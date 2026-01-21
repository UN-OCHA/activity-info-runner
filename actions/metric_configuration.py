import inspect
import logging
import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Dict, Optional, Callable

from temporalio import activity
from temporalio.exceptions import ApplicationError

from actions.common import DatabaseTreeResourceType, resolve_form_from_prefix, collect_field_mappings
from actions.dtos import FieldType, FieldTypeParametersUpdateDTO, SchemaFieldUpdateDTO
from actions.models import Changeset, FieldAction, FieldCreateAction, FieldDeleteAction, RecordAction, \
    RecordUpdateAction, FieldUpdateAction
from api import ActivityInfoClient
from api.client import BASE_URL, APIError
from utils import CaptureLogs

OPERATION_METRIC_CONFIGURATION_FORM_PREFIX = "0.1.5_"


class MetricFieldKind(Enum):
    MANUAL = auto()
    INTERNAL_CALC = auto()
    EXTERNAL_CALC = auto()
    FINAL = auto()


@dataclass(frozen=True)
class MetricFieldConfig:
    suffix: str
    label_suffix: str
    type: FieldType
    calculated: bool
    formula: Optional[str]
    relevanceCondition: Callable[[str], str]


FIELD_KIND_CONFIG: Dict[MetricFieldKind, MetricFieldConfig] = {
    MetricFieldKind.MANUAL: MetricFieldConfig(
        suffix="MAN",
        label_suffix="(Manual)",
        type=FieldType.quantity,
        calculated=False,
        formula=None,
        relevanceCondition=lambda
            field_name: f"!ISBLANK(SEARCH(\"|{field_name}|\", CONCAT(\"|\", TEXTJOIN(\"|\", TRUE, IND.MM.[Complete Metrics].CCODE), \"|\")))"
    ),
    MetricFieldKind.INTERNAL_CALC: MetricFieldConfig(
        suffix="ICALC",
        label_suffix="(Internal Calc)",
        type=FieldType.calculated,
        calculated=True,
        formula="VALUE(\"#\")",
        relevanceCondition=lambda
            field_name: f"!ISBLANK(SEARCH(\"|{field_name}|\", CONCAT(\"|\", TEXTJOIN(\"|\", TRUE, IND.MM.[Complete Metrics].CCODE), \"|\"))) || !ISBLANK(SEARCH(\"|{field_name}|\", CONCAT(\"|\", TEXTJOIN(\"|\", TRUE, IND.MM.[Calc-only Metrics].CCODE), \"|\")))"
    ),
    MetricFieldKind.EXTERNAL_CALC: MetricFieldConfig(
        suffix="ECALC",
        label_suffix="(External Calc)",
        type=FieldType.quantity,
        calculated=False,
        formula=None,
        relevanceCondition=lambda
            field_name: f"!ISBLANK(SEARCH(\"|{field_name}|\", CONCAT(\"|\", TEXTJOIN(\"|\", TRUE, IND.MM.[Complete Metrics].CCODE), \"|\"))) || !ISBLANK(SEARCH(\"|{field_name}|\", CONCAT(\"|\", TEXTJOIN(\"|\", TRUE, IND.MM.[Calc-only Metrics].CCODE), \"|\")))"
    ),
    MetricFieldKind.FINAL: MetricFieldConfig(
        suffix="",
        label_suffix="",
        type=FieldType.calculated,
        calculated=True,
        formula=None,
        relevanceCondition=lambda
            field_name: f"!ISBLANK(SEARCH(\"|{field_name}|\", CONCAT(\"|\", TEXTJOIN(\"|\", TRUE, IND.MM.[Complete Metrics].CCODE), \"|\"))) || !ISBLANK(SEARCH(\"|{field_name}|\", CONCAT(\"|\", TEXTJOIN(\"|\", TRUE, IND.MM.[Calc-only Metrics].CCODE), \"|\")))"
    ),
}


def final_formula(prefix: str, kinds: List[MetricFieldKind]) -> str:
    sources: List[str] = []
    if MetricFieldKind.MANUAL in kinds:
        sources.append(f"{prefix}_MAN")
    if MetricFieldKind.INTERNAL_CALC in kinds:
        sources.append(f"{prefix}_ICALC")
    if MetricFieldKind.EXTERNAL_CALC in kinds:
        sources.append(f"{prefix}_ECALC")
    if not sources:
        raise ValueError(f"No sources available for FINAL field {prefix}")
    return f"COALESCE({','.join(sources)})"


@activity.defn
async def get_operation_metric_configuration_changesets(database_id: str) -> Changeset:
    try:
        with CaptureLogs() as log_handler:
            origin = inspect.currentframe().f_code.co_name
            field_actions: List[FieldAction] = []
            record_actions: List[RecordAction] = []

            client = ActivityInfoClient(BASE_URL, api_token=os.getenv("API_TOKEN"))
            tree = await client.api.get_database_tree(database_id)
            metric_configurations_form = next(
                (res for res in tree.resources if
                 res.label.startswith(
                     OPERATION_METRIC_CONFIGURATION_FORM_PREFIX) and res.type == DatabaseTreeResourceType.FORM),
                None
            )
            if not metric_configurations_form:
                raise ValueError("Operation Metric Configurations form not found in the database.")

            metric_configurations = await client.api.get_operation_metric_configuration_fields(
                metric_configurations_form.id)

            for prefix in set([m.data_form_prefix for m in metric_configurations]):
                logging.debug(f"Processing metric configurations for prefix {prefix}")
                configurations = sorted([c for c in metric_configurations if c.data_form_prefix == prefix],
                                        key=lambda c: c.order)

                form = await resolve_form_from_prefix(client, database_id, prefix)
                if form is None:
                    for config in configurations:
                        record_actions.append(RecordUpdateAction(
                            origin=origin,
                            order=0,
                            form_id=metric_configurations_form.id,
                            form_name=metric_configurations_form.label,
                            record_id=config.id,
                            field_code="ERRS",
                            field_value=f"Form with prefix {prefix} could not be found in the database",
                            old_field_value=None,
                        ))
                    continue
                else:
                    for config in configurations:
                        if config.errors is not None:
                            record_actions.append(RecordUpdateAction(
                                origin=origin,
                                order=1,
                                form_id=metric_configurations_form.id,
                                form_name=metric_configurations_form.label,
                                record_id=config.id,
                                field_code="ERRS",
                                field_value=None,
                                old_field_value=config.errors,
                            ))

                expected_field_codes: set[str] = set()
                current_schema = await client.api.get_form_schema(form.id)
                existing_fields_by_code = {
                    e.code: e
                    for e in current_schema.elements
                    if e.code.startswith("AMOUNT_")
                }

                for config in configurations:
                    field_code_prefix = f"AMOUNT_{config.reference_code}"

                    field_kinds = [
                        MetricFieldKind.EXTERNAL_CALC,
                        MetricFieldKind.INTERNAL_CALC,
                        MetricFieldKind.FINAL,
                    ]
                    if config.shown_as.startswith("MAN"):
                        field_kinds.insert(0, MetricFieldKind.MANUAL)

                    for kind in field_kinds:
                        cfg = FIELD_KIND_CONFIG[kind]
                        field_code = (
                            f"{field_code_prefix}_{cfg.suffix}"
                            if cfg.suffix else field_code_prefix
                        )

                        expected_field_codes.add(field_code)

                        label = f"{config.name} {cfg.label_suffix}".strip()
                        formula = (
                            final_formula(field_code_prefix, field_kinds)
                            if kind is MetricFieldKind.FINAL
                            else cfg.formula
                        )

                        existing = existing_fields_by_code.get(field_code)
                        relevance_condition = cfg.relevanceCondition(config.field_name)
                        update = SchemaFieldUpdateDTO(
                            id=existing.id if existing else None,
                            code=field_code,
                            label=label,
                            relevanceCondition=relevance_condition,
                            validationCondition=None,
                            dataEntryVisible=not cfg.calculated,
                            tableVisible=not cfg.calculated,
                            required=False,
                            key=False,
                            type=cfg.type,
                            typeParameters=FieldTypeParametersUpdateDTO(
                                formula=formula,
                            ) if formula is not None
                            else None
                        )
                        if existing is None:
                            field_actions.append(FieldCreateAction(
                                origin=origin,
                                database_id=database_id,
                                form_id=form.id,
                                form_name=form.label,
                                field_code=field_code,
                                order=config.order,
                                **update.model_dump(),
                            ))
                        else:
                            normalized_existing = existing.model_copy(deep=True)

                            normalized_type_parameters = None
                            if normalized_existing.type_parameters is not None:
                                old_formula = normalized_existing.type_parameters.formula or ""
                                field_lookup = await collect_field_mappings(client, form.id)
                                sorted_keys = sorted(field_lookup.keys(), key=len, reverse=True)
                                for k in sorted_keys:
                                    old_formula = old_formula.replace(k, field_lookup[k])
                                normalized_type_parameters = normalized_existing.type_parameters.model_copy(
                                    update={"formula": old_formula}
                                )

                            old_relevance_condition = normalized_existing.relevance_condition or ""
                            field_lookup = await collect_field_mappings(client, form.id)
                            sorted_keys = sorted(field_lookup.keys(), key=len, reverse=True)
                            for k in sorted_keys:
                                old_relevance_condition = old_relevance_condition.replace(k, field_lookup[k])

                            normalized_existing = normalized_existing.model_copy(
                                update={
                                    "type_parameters": normalized_type_parameters,
                                    "relevance_condition": old_relevance_condition
                                }
                            )

                            needs_update = (
                                    normalized_existing.type_parameters.formula != formula
                                    or normalized_existing.relevance_condition != relevance_condition
                            )
                            if needs_update:
                                field_actions.append(FieldUpdateAction(
                                    origin=origin,
                                    database_id=database_id,
                                    form_id=form.id,
                                    form_name=form.label,
                                    field_code=field_code,
                                    order=0,
                                    old=normalized_existing,
                                    new=update,
                                ))

                for existing_code in existing_fields_by_code:
                    if existing_code not in expected_field_codes:
                        old_params = existing_fields_by_code[existing_code].type_parameters
                        field_actions.append(FieldDeleteAction(
                            origin=origin,
                            database_id=database_id,
                            form_id=form.id,
                            form_name=form.label,
                            field_code=existing_code,
                            order=0,
                            old_formula=old_params.formula if old_params else None,
                        ))

            res = Changeset.from_tuple((record_actions, field_actions))
            res.logs = log_handler.records
            return res
    except APIError as e:
        if e.status_code == 404:
            raise ApplicationError(str(e), non_retryable=True) from e
        raise e
