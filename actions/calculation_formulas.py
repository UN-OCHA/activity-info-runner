import inspect
import logging
from enum import StrEnum, auto
from typing import List, Tuple, Dict, Optional

from actions.common import resolve_form_from_prefix, convert_errors_to_record_actions, collect_field_mappings
from actions.models import Changeset, RecordError, FieldUpdateAction, RecordAction, RecordUpdateAction
from api import ActivityInfoClient
from api.models import OperationCalculationFormulasField
from parser import RecordResolver, ActivityInfoExpression
from utils import build_nested_dict

CALCULATION_FORMULAS_FORM_PREFIX = "0.1.6_"


class OperationCalculationApplyType(StrEnum):
    INTERNAL = "Internal"
    EXTERNAL = "External"
    UNKNOWN = auto()


async def get_operation_calculation_changesets(client: ActivityInfoClient, database_id: str) -> Changeset:
    """Generates changesets for operation calculation formulas in the specified database.
    Args:
        client: An instance of ActivityInfoClient to interact with the API.
        database_id: The ID of the database to process.
    Returns:
        A changeset of record and field actions (including errors as record actions)
    """
    # 1: Locate the operation calculation formulas form
    database_tree = await client.api.get_database_tree(database_id)
    form_id = next(
        (res.id for res in database_tree.resources if
         res.type == "FORM" and res.label.startswith(CALCULATION_FORMULAS_FORM_PREFIX)),
        None
    )
    form_name = next(
        (res.label for res in database_tree.resources if
         res.type == "FORM" and res.label.startswith(CALCULATION_FORMULAS_FORM_PREFIX)),
        None
    )
    if not form_id:
        raise ValueError("Operation Calculation Formulas form not found in the database tree")

    # 2: Fetch the rows specifying operation calculation formulas
    fields = await client.api.get_operation_calculation_formulas_fields(form_id)
    logging.info(f"Retrieved {len(fields)} operation calculation formula fields")
    internal_fields = [field for field in fields if field.apply == OperationCalculationApplyType.INTERNAL]
    external_fields = [field for field in fields if field.apply == OperationCalculationApplyType.EXTERNAL]

    # 3: Generate internal changeset entries (to replace form schema formulas)
    internal_changeset, internal_errors = await get_internal_operation_calculation_changeset_entries(client,
                                                                                                     database_id,
                                                                                                     internal_fields)
    logging.info(f"Computed {len(internal_changeset)} internal changeset entries")
    for i, entry in enumerate(internal_changeset.field_actions, start=1): entry.order = i

    # 4: Generate external changeset entries (to update existing records)
    external_changeset, external_errors = await get_external_operation_calculation_changeset_entries(client,
                                                                                                     database_id,
                                                                                                     external_fields)
    logging.info(f"Computed {len(external_changeset)} external changeset entries")
    for i, entry in enumerate(external_changeset.record_actions, start=len(internal_changeset) + 1): entry.order = i

    errors = internal_errors + external_errors
    for i in range(len(errors)):
        errors[i].form_id = form_id
        errors[i].form_name = form_name
    error_actions = await convert_errors_to_record_actions(errors)
    error_actions = revert_extra_errors(form_id, error_actions, fields)
    for i, entry in enumerate(error_actions,
                              start=len(internal_changeset) + len(external_changeset) + 1): entry.order = i

    return internal_changeset + external_changeset + Changeset.from_record_actions(error_actions)


async def get_internal_operation_calculation_changeset_entries(client: ActivityInfoClient, database_id: str,
                                                               internal_fields: List[
                                                                   OperationCalculationFormulasField]) -> Tuple[
    Changeset, List[RecordError]]:
    """Generates changeset entries for internal operation calculation formulas.
    Args:
        client: An instance of ActivityInfoClient to interact with the API.
        database_id: The ID of the database to process.
        internal_fields: A list of OperationCalculationFormulasField objects representing internal fields.
    Returns:
        A tuple containing:
            - A changeset of record actions
            - A list of record errors
    """
    origin = inspect.currentframe().f_code.co_name
    errors: List[RecordError] = []
    internal_fields.sort(key=lambda x: x.ref_order)
    grouped_fields: Dict[Tuple[str, str], List[OperationCalculationFormulasField]] = {}
    form_names: Dict[Tuple[str, str], str] = {}

    for field in internal_fields:
        # 1: Resolve the actual form ID from the sys_prefix (i.e: 2.1A -> c41sw8jmkcry89xi)
        form = await resolve_form_from_prefix(client, database_id, field.sys_prefix)
        if not form:
            errors.append(RecordError(
                form_id="",
                form_name="",
                origin=origin,
                record_id=field.id,
                field_code="SYSPREFIX",
                error_message=f"Could not resolve form ID for prefix {field.sys_prefix}"
            ))
            continue
        field_code = f"{field.sys_field}_ICALC"

        # 2: Validate the filter and formula expressions by parsing them
        _, _, parse_errors = parse_expressions_with_errors(form.id, field, field_code)
        if parse_errors:
            for e in parse_errors:
                e.origin = origin
            errors.extend(parse_errors)
            continue

        # 3: Group fields by (form_id, field_code) to combine multiple conditions later
        key = (form.id, field_code)
        if key not in grouped_fields:
            grouped_fields[key] = []
        grouped_fields[key].append(field)
        form_names[key] = form.label

    # 4: For each group, combine the formulas using nested IF statements based on the filters
    field_actions: List[FieldUpdateAction] = []
    skip_unchanged_count = 0
    for (form_id, field_code), fields in grouped_fields.items():
        fields.sort(key=lambda x: x.ref_order)
        reversed_fields = list(reversed(fields))
        last = reversed_fields[0]
        expr = f"IF({last.filter}, {last.formula})"
        for f in reversed_fields[1:]:
            expr = f"IF({f.filter}, {f.formula}, {expr})"
        old_form = await client.api.get_form_schema(form_id)
        old_formula = next(
            (e.typeParameters.formula for e in old_form.elements if e.code == field_code)
        )
        field_lookup = await collect_field_mappings(client, form_id)
        sorted_keys = sorted(field_lookup.keys(), key=len, reverse=True)
        for k in sorted_keys:
            old_formula = old_formula.replace(k, field_lookup[k])
        if old_formula == expr:
            skip_unchanged_count += 1
            continue
        field_actions.append(FieldUpdateAction(
            origin=origin,
            database_id=database_id,
            form_id=form_id,
            form_name=form_names[(form_id, field_code)],
            field_code=field_code,
            order=fields[-1].ref_order,
            formula=expr,
            old_formula=old_formula
        ))

    logging.info(f"Skipped {skip_unchanged_count} fields due to unchanged formulae")

    return Changeset.from_field_actions(field_actions), errors


async def get_external_operation_calculation_changeset_entries(client: ActivityInfoClient, database_id: str,
                                                               external_fields: List[
                                                                   OperationCalculationFormulasField]) -> Tuple[
    Changeset, List[RecordError]]:
    """Generates changeset entries for external operation calculation formulas.
    Args:
        client: An instance of ActivityInfoClient to interact with the API.
        database_id: The ID of the database to process.
        external_fields: A list of OperationCalculationFormulasField objects representing external fields.
    Returns:
        A tuple containing:
            - A changeset of field actions
            - A list of record errors
    """
    origin = inspect.currentframe().f_code.co_name
    errors: List[RecordError] = []
    external_fields.sort(key=lambda x: x.ref_order)
    skip_filter_count = 0
    skip_unchanged_count = 0
    record_actions: List[RecordAction] = []

    for field in external_fields:
        # 1: Resolve the actual form ID from the sys_prefix (i.e: 2.1A -> c41sw8jmkcry89xi)
        form = await resolve_form_from_prefix(client, database_id, field.sys_prefix)
        if not form:
            errors.append(RecordError(
                form_id="",
                form_name="",
                record_id=field.id,
                field_code="SYSPREFIX",
                origin=origin,
                error_message=f"Could not resolve form ID for prefix {field.sys_prefix}",
            ))
            continue

        # 2: Fetch all records from the target form
        database_tree = await client.api.get_database_tree(database_id)
        form_name = next(
            (res.label for res in database_tree.resources if res.id == form.id),
            None
        )
        entries = await client.api.get_form(form.id)

        filter_expr, formula_expr, parse_errors = parse_expressions_with_errors(form.id, field, field.sys_field)
        if parse_errors:
            for e in parse_errors:
                e.origin = origin
            errors.extend(parse_errors)
            continue

        # 3: Evaluate the filter and formula for each record, creating changeset entries as needed
        for entry in entries:
            old_fields = {k: entry[k] for k in entry if k not in ('_id', '_lastEditTime') and entry[k] is not None}
            nested_fields = build_nested_dict(old_fields)

            resolver = RecordResolver(client, nested_fields)
            if not await filter_expr.evaluate(resolver):
                skip_filter_count += 1
                continue

            record_id = entry.get("@id")
            if not record_id:
                continue

            res = await formula_expr.evaluate(resolver)
            if old_fields.get(field.sys_field) == res:
                skip_unchanged_count += 1
                continue

            new_fields = old_fields.copy()
            new_fields[f"{field.sys_field}_ECALC"] = res
            record_actions.append(RecordUpdateAction(
                origin=origin,
                order=field.ref_order,
                form_id=form.id,
                form_name=form_name,
                record_id=record_id,
                field_code=f"{field.sys_field}_ECALC",
                field_value=res,
                old_field_value=old_fields[field.sys_field],
            ))

    logging.info(f"Skipped {skip_filter_count} records due to filter not matching")
    logging.info(f"Skipped {skip_unchanged_count} records due to unchanged values")

    return Changeset.from_record_actions(record_actions), errors


def parse_expressions_with_errors(
        form_id: str,
        field: OperationCalculationFormulasField,
        field_code: str,
) -> Tuple[Optional[ActivityInfoExpression], Optional[ActivityInfoExpression], List[RecordError]]:
    """Tries to parse filter and formula expressions and returns any errors found.
    Args:
        form_id: The ID of the form.
        field: The OperationCalculationFormulasField object.
        field_code: The field code to report in errors.
    Returns:
        A tuple containing:
            - The parsed filter ActivityInfoExpression (or None if failed).
            - The parsed formula ActivityInfoExpression (or None if failed).
            - A list of RecordError objects representing any errors encountered.
    """
    errors: List[RecordError] = []
    filter_expr = None
    formula_expr = None

    try:
        filter_expr = ActivityInfoExpression.parse(field.filter)
    except Exception as e:
        errors.append(RecordError(
            origin="",
            form_id="",
            form_name="",
            record_id=field.id,
            field_code=field_code,
            error_message=f"Failed to parse filter expression: {e}"
        ))
    try:
        formula_expr = ActivityInfoExpression.parse(field.formula)
    except Exception as e:
        errors.append(RecordError(
            origin="",
            form_id="",
            form_name="",
            record_id=field.id,
            field_code=field_code,
            error_message=f"Failed to parse formula expression: {e}",
        ))

    return filter_expr, formula_expr, errors


def revert_extra_errors(form_id: str, existing_errors: List[RecordAction],
                        fields: List[OperationCalculationFormulasField]) -> List[RecordAction]:
    """Identifies fields that previously had errors but are now resolved, creating revert error entries.
    Args:
        form_id: The ID of the form.
        existing_errors: A list of existing RecordAction objects with errors.
        fields: A list of OperationCalculationFormulasField objects.
    Returns:
        A corrected list of RecordAction objects
    """
    # A field's current error is found in field.errors (non-null)
    error_field_ids = {error.record_id for error in existing_errors}
    final_actions: List[RecordAction] = existing_errors

    for field in fields:
        if field.id in error_field_ids:
            continue
        if field.errors is not None:
            final_actions.append(RecordUpdateAction(
                form_id=form_id,
                field_code="ERRS",
                field_value="",
                record_id=field.id,
                order=0,
                origin=inspect.currentframe().f_code.co_name,
                old_field_value=field.errors,
                form_name="?",
            ))
            logging.info(f"Reverting errors for field {field.id}")
    return final_actions
