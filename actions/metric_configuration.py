import inspect
import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Dict, Optional

from actions.common import DatabaseTreeResourceType, resolve_form_from_prefix, collect_field_mappings
from actions.dtos import FieldType
from actions.models import Changeset, FieldAction, FieldCreateAction, FieldDeleteAction, RecordAction, \
    RecordUpdateAction, FieldUpdateAction
from api import ActivityInfoClient

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


FIELD_KIND_CONFIG: Dict[MetricFieldKind, MetricFieldConfig] = {
    MetricFieldKind.MANUAL: MetricFieldConfig(
        suffix="MAN",
        label_suffix="(Manual)",
        type=FieldType.quantity,
        calculated=False,
        formula=None,
    ),
    MetricFieldKind.INTERNAL_CALC: MetricFieldConfig(
        suffix="ICALC",
        label_suffix="(Internal Calc)",
        type=FieldType.calculated,
        calculated=True,
        formula="VALUE(\"#\")",
    ),
    MetricFieldKind.EXTERNAL_CALC: MetricFieldConfig(
        suffix="ECALC",
        label_suffix="(External Calc)",
        type=FieldType.quantity,
        calculated=False,
        formula=None,
    ),
    MetricFieldKind.FINAL: MetricFieldConfig(
        suffix="",
        label_suffix="",
        type=FieldType.calculated,
        calculated=True,
        formula=None,
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


async def get_operation_metric_configuration_changesets(client: ActivityInfoClient, database_id: str,
                                                        order_start_idx: int) -> Changeset:
    origin = inspect.currentframe().f_code.co_name
    field_actions: List[FieldAction] = []
    record_actions: List[RecordAction] = []

    tree = await client.api.get_database_tree(database_id)
    metric_configurations_form = next(
        (res for res in tree.resources if
         res.label.startswith(
             OPERATION_METRIC_CONFIGURATION_FORM_PREFIX) and res.type == DatabaseTreeResourceType.FORM),
        None
    )
    if not metric_configurations_form:
        raise ValueError("Operation Metric Configurations form not found in the database.")

    metric_configurations = await client.api.get_operation_metric_configuration_fields(metric_configurations_form.id)

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
                if existing is None:
                    field_actions.append(FieldCreateAction(
                        origin=origin,
                        order=config.order,
                        database_id=database_id,
                        form_id=form.id,
                        form_name=form.label,
                        field_code=field_code,
                        label=label,
                        relevance_condition="TODO!!",
                        validation_condition="",
                        data_entry_visible=not cfg.calculated,
                        table_visible=not cfg.calculated,
                        required=False,
                        key=False,
                        type=cfg.type,
                        formula=formula,
                    ))
                else:
                    needs_update = (
                            existing.typeParameters.formula != formula
                        # TODO: also check for relevance condition or validation condition
                    )
                    old_formula = existing.typeParameters.formula
                    if old_formula:
                        field_lookup = await collect_field_mappings(client, form.id)
                        sorted_keys = sorted(field_lookup.keys(), key=len, reverse=True)
                        for k in sorted_keys:
                            old_formula = old_formula.replace(k, field_lookup[k])
                        if old_formula == formula:
                            continue
                    if needs_update:
                        field_actions.append(FieldUpdateAction(
                            origin=origin,
                            database_id=database_id,
                            form_id=form.id,
                            form_name=form.label,
                            field_code=field_code,
                            order=0,
                            formula=formula,
                            old_formula=old_formula,
                        ))

        for existing_code in existing_fields_by_code:
            if existing_code not in expected_field_codes:
                field_actions.append(FieldDeleteAction(
                    origin=origin,
                    database_id=database_id,
                    form_id=form.id,
                    form_name=form.label,
                    field_code=existing_code,
                    order=0,
                    old_formula=existing_fields_by_code[existing_code].typeParameters.formula,
                ))

    for idx in range(len(record_actions)):
        record_actions[idx].order = order_start_idx + idx
    for idx in range(len(field_actions)):
        field_actions[idx].order = order_start_idx + len(record_actions) + idx

    return Changeset.from_tuple((record_actions, field_actions))
