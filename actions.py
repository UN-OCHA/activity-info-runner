import logging
from enum import StrEnum, auto
from typing import List, Optional, Tuple, Dict

from api import ActivityInfoClient
from api.models import OperationCalculationFormulasField
from models import FormChangeset, FormChangesetEntry, FormChangesetPlan, RecordChangesetEntry, RecordChangeset, \
    FieldErrorReport, FieldErrorEntry, FormRecordUpdateDTO
from parser import ActivityInfoExpression, RecordResolver
from utils import build_nested_dict


class OperationCalculationApplyType(StrEnum):
    INTERNAL = "Internal"
    EXTERNAL = "External"
    UNKNOWN = auto()


class DatabaseTreeResourceType(StrEnum):
    FORM = "FORM"
    # We do not care about other resource types for our purposes
    OTHER = auto()


async def get_operation_calculation_changesets(client: ActivityInfoClient, database_id: str) -> tuple[
    FormChangeset, RecordChangeset, list[FormRecordUpdateDTO]]:
    """Generates changesets for operation calculation formulas in the specified database.
    Args:
        client: An instance of ActivityInfoClient to interact with the API.
        database_id: The ID of the database to process.
    Returns:
        A tuple containing:
            - FormChangeset for internal operation calculation formulas.
            - RecordChangeset for external operation calculation formulas.
            - A list of FormRecordUpdateDTO representing any errors encountered.
    """
    # 1: Locate the operation calculation formulas form
    database_tree = await client.api.get_database_tree(database_id)
    form_id = next(
        (res.id for res in database_tree.resources if res.type == "FORM" and res.label.startswith("0.1.5_")),
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
    for i, entry in enumerate(internal_changeset, start=1): entry.calc_order = i

    # 4: Generate external changeset entries (to update existing records)
    external_changeset, external_errors = await get_external_operation_calculation_changeset_entries(client, database_id,
                                                                                    external_fields)
    logging.info(f"Computed {len(external_changeset)} external changeset entries")
    for i, entry in enumerate(external_changeset, start=len(internal_changeset) + 1): entry.calc_order = i

    # 5: Construct the structured changesets and error report to return
    form_changeset = FormChangeset(entries=internal_changeset, action="operation_calculation_formulas",
                                   title="Internal Changeset")
    record_changeset = RecordChangeset(entries=external_changeset, action="operation_calculation_formulas",
                                       title="External Changeset")

    form_changeset.pretty_print_table()
    record_changeset.pretty_print_table()

    errors = internal_errors + external_errors
    for i in range(len(errors)):
        errors[i].form_id = form_id
        errors[i].form_name = "0.1.5_Operation_Calculation_Formulas"
    report = FieldErrorReport(entries=errors, title="Operation Calculation Formula Errors")
    report.pretty_print_table()
    error_dtos = [e.as_form_update_dto() for e in errors]
    error_dtos.extend(revert_extra_errors(form_id, errors, fields))

    return form_changeset, record_changeset, error_dtos


def parse_expressions_with_errors(
        form_id: str,
        field: OperationCalculationFormulasField,
        field_code: str,
) -> Tuple[Optional[ActivityInfoExpression], Optional[ActivityInfoExpression], List[FieldErrorEntry]]:
    """Tries to parse filter and formula expressions and returns any errors found.
    Args:
        form_id: The ID of the form.
        field: The OperationCalculationFormulasField object.
        field_code: The field code to report in errors.
    Returns:
        A tuple containing:
            - The parsed filter ActivityInfoExpression (or None if failed).
            - The parsed formula ActivityInfoExpression (or None if failed).
            - A list of FieldErrorEntry objects representing any errors encountered.
    """
    errors: List[FieldErrorEntry] = []
    filter_expr = None
    formula_expr = None

    try:
        filter_expr = ActivityInfoExpression.parse(field.filter)
    except Exception as e:
        errors.append(FieldErrorEntry(
            formId=form_id,
            recordId=field.id,
            parentRecordId=None,
            fieldCode=field_code,
            expression=field.filter,
            errorMessage=f"Failed to parse filter expression: {e}",
        ))
        logging.warning(f"Failed to parse filter expression for field {field.id} in form {form_id}: {e}")

    try:
        formula_expr = ActivityInfoExpression.parse(field.formula)
    except Exception as e:
        errors.append(FieldErrorEntry(
            formId=form_id,
            recordId=field.id,
            parentRecordId=None,
            fieldCode=field_code,
            expression=field.formula,
            errorMessage=f"Failed to parse formula expression: {e}",
        ))
        logging.warning(f"Failed to parse formula expression for field {field.id} in form {form_id}: {e}")

    return filter_expr, formula_expr, errors


async def get_internal_operation_calculation_changeset_entries(client: ActivityInfoClient, database_id: str,
                                                               internal_fields: List[
                                                                   OperationCalculationFormulasField]) -> Tuple[List[
    FormChangesetEntry], List[FieldErrorEntry]]:
    """Generates changeset entries for internal operation calculation formulas.
    Args:
        client: An instance of ActivityInfoClient to interact with the API.
        database_id: The ID of the database to process.
        internal_fields: A list of OperationCalculationFormulasField objects representing internal fields.
    Returns:
        A tuple containing:
            - A list of FormChangesetEntry objects representing the changeset entries.
            - A list of FieldErrorEntry objects representing any errors encountered.
    """
    errors: List[FieldErrorEntry] = []
    internal_fields.sort(key=lambda x: x.ref_order)
    grouped_fields: Dict[Tuple[str, str], List[OperationCalculationFormulasField]] = {}

    for field in internal_fields:
        # 1: Resolve the actual form ID from the sys_prefix (i.e: 2.1A -> c41sw8jmkcry89xi)
        form_id = await resolve_form_id_from_prefix(client, database_id, field.sys_prefix)
        if not form_id:
            errors.append(FieldErrorEntry(
                formId="",
                recordId=field.id,
                parentRecordId=None,
                fieldCode="SYSPREFIX",
                expression=field.sys_prefix,
                errorMessage=f"Could not resolve form ID for prefix {field.sys_prefix}",
            ))
            logging.warning(f"Could not resolve form ID for prefix {field.sys_prefix}")
            continue
        field_code = f"{field.sys_field}_ICALC"

        # 2: Validate the filter and formula expressions by parsing them
        _, _, parse_errors = parse_expressions_with_errors(form_id, field, field_code)
        if parse_errors:
            errors.extend(parse_errors)
            continue

        # 3: Group fields by (form_id, field_code) to combine multiple conditions later
        key = (form_id, field_code)
        if key not in grouped_fields:
            grouped_fields[key] = []
        grouped_fields[key].append(field)

    # 4: For each group, combine the formulas using nested IF statements based on the filters
    changeset_plans: List[FormChangesetPlan] = []
    for (form_id, field_code), fields in grouped_fields.items():
        fields.sort(key=lambda x: x.ref_order)
        reversed_fields = list(reversed(fields))
        last = reversed_fields[0]
        expr = f"IF({last.filter}, {last.formula})"
        for f in reversed_fields[1:]:
            expr = f"IF({f.filter}, {f.formula}, {expr})"
        changeset_plans.append(FormChangesetPlan(
            calcOrder=fields[-1].ref_order,
            formId=form_id,
            fieldCode=field_code,
            newExpression=expr,
        ))

    return await resolve_internal_changeset_plans(client, changeset_plans), errors


async def get_external_operation_calculation_changeset_entries(client: ActivityInfoClient, database_id: str,
                                                               external_fields: List[
                                                                   OperationCalculationFormulasField]) -> Tuple[
    List[RecordChangesetEntry], List[FieldErrorEntry]]:
    """Generates changeset entries for external operation calculation formulas.
    Args:
        client: An instance of ActivityInfoClient to interact with the API.
        database_id: The ID of the database to process.
        external_fields: A list of OperationCalculationFormulasField objects representing external fields.
    Returns:
        A tuple containing:
            - A list of RecordChangesetEntry objects representing the changeset entries.
            - A list of FieldErrorEntry objects representing any errors encountered.
    """
    errors: List[FieldErrorEntry] = []
    external_fields.sort(key=lambda x: x.ref_order)
    skip_filter_count = 0
    skip_unchanged_count = 0
    changeset_entries: List[RecordChangesetEntry] = []

    for field in external_fields:
        # 1: Resolve the actual form ID from the sys_prefix (i.e: 2.1A -> c41sw8jmkcry89xi)
        form_id = await resolve_form_id_from_prefix(client, database_id, field.sys_prefix)
        if not form_id:
            errors.append(FieldErrorEntry(
                formId="",
                recordId=field.id,
                parentRecordId=None,
                fieldCode="SYSPREFIX",
                expression=field.sys_prefix,
                errorMessage=f"Could not resolve form ID for prefix {field.sys_prefix}",
            ))
            logging.warning(f"Could not resolve form ID for prefix {field.sys_prefix}")
            continue

        # 2: Fetch all records from the target form
        database_tree = await client.api.get_database_tree(database_id)
        form_name = next(
            (res.label for res in database_tree.resources if res.id == form_id),
            None
        )
        entries = await client.api.get_form(form_id)

        filter_expr, formula_expr, parse_errors = parse_expressions_with_errors(form_id, field, field.sys_field)
        if parse_errors:
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
            new_fields[field.sys_field] = res
            changeset_entries.append(RecordChangesetEntry(
                calcOrder=field.ref_order,
                formId=form_id,
                formName=form_name,
                recordId=record_id,
                parentRecordId=None,
                fields=new_fields,
                oldFields=old_fields,
            ))

    logging.info(f"Skipped {skip_filter_count} records due to filter not matching")
    logging.info(f"Skipped {skip_unchanged_count} records due to unchanged values")

    return changeset_entries, errors


async def resolve_form_id_from_prefix(client: ActivityInfoClient, database_id: str, sys_prefix: str) -> Optional[str]:
    """Resolves the form ID corresponding to a given system prefix in the database tree."""
    database_tree = await client.api.get_database_tree(database_id)
    for res in database_tree.resources:
        if res.label.split("_")[0] == sys_prefix and res.type == DatabaseTreeResourceType.FORM:
            return res.id
    return None


async def resolve_internal_changeset_plans(client: ActivityInfoClient,
                                           internal_changeset: List[FormChangesetPlan]) -> List[FormChangesetEntry]:
    """Resolves the internal changeset plans into actual changeset entries by fetching current formulas.
    Args:
        client: An instance of ActivityInfoClient to interact with the API.
        internal_changeset: A list of FormChangesetPlan objects representing the planned changes.
    Returns:
        A list of FormChangesetEntry objects representing the resolved changeset entries.
    """
    changeset_entries: List[FormChangesetEntry] = []
    for plan in internal_changeset:
        # 1: Collect field ID to code mappings for the target form and its references
        field_lookup = await collect_field_mappings(client, plan.form_id)
        # 2: Fetch the current form schema to get existing formulas
        schema = await client.api.get_form_schema(plan.form_id)
        code_lookup = {el.code: el.id for el in schema.elements}

        # 3: Replace field IDs in the old expression with field codes for comparison
        target_element = next((el for el in schema.elements if el.code == plan.field_code), None)
        if not target_element:
            logging.warning(f"Field code {plan.field_code} not found in form {plan.form_id}")
            continue
        old_expression = target_element.typeParameters.formula
        sorted_keys = sorted(field_lookup.keys(), key=len, reverse=True)
        for k in sorted_keys:
            old_expression = old_expression.replace(k, field_lookup[k])
        if old_expression == plan.new_expression:
            logging.info(f"Skipping unchanged formula for {plan.field_code} in form {plan.form_id}")
            continue

        changeset_entries.append(FormChangesetEntry(
            calcOrder=plan.calc_order,
            formId=plan.form_id,
            formName=schema.label,
            fieldCode=plan.field_code,
            fieldId=code_lookup[plan.field_code],
            newExpression=plan.new_expression,
            oldExpression=old_expression,
        ))

    return changeset_entries


async def collect_field_mappings(client: ActivityInfoClient, start_form_id: str) -> Dict[str, str]:
    """Collects field ID to code mappings across forms starting from a given form ID.
    Args:
        client: An instance of ActivityInfoClient to interact with the API.
        start_form_id: The ID of the form to start collecting mappings from.
    Returns:
        A dictionary mapping field IDs to their corresponding codes.
    """
    mappings = {}
    visited_forms = set()
    pending_forms = [start_form_id]

    logging.info(f"Starting field mapping collection from form {start_form_id}")
    while pending_forms:
        form_id = pending_forms.pop(0)
        if form_id in visited_forms:
            continue
        visited_forms.add(form_id)

        try:
            schema = await client.api.get_form_schema(form_id)
        except Exception as e:
            logging.warning(f"Failed to fetch schema for form {form_id}: {e}")
            continue

        for el in schema.elements:
            if el.code:
                mappings[el.id] = el.code
            if el.type.upper() == "REFERENCE" and el.typeParameters and el.typeParameters.range:
                for r in el.typeParameters.range:
                    ref_form_id = r.get("formId") or r.get("formClassId")
                    if ref_form_id:
                        if ref_form_id not in visited_forms and ref_form_id not in pending_forms:
                            logging.debug(
                                f"Found reference to form {ref_form_id} in field {el.code or 'UNKNOWN'} ({el.id})")
                            pending_forms.append(ref_form_id)

    logging.info(f"Collected {len(mappings)} field mappings across {len(visited_forms)} forms")

    return mappings

def revert_extra_errors(form_id: str, existing_errors: List[FieldErrorEntry], fields: List[OperationCalculationFormulasField]) -> List[FormRecordUpdateDTO]:
    """Identifies fields that previously had errors but are now resolved, creating revert error entries.
    Args:
        existing_errors: A list of existing FieldErrorEntry objects.
        fields: A list of OperationCalculationFormulasField objects.
    Returns:
        A list of FormRecordUpdateDTO objects representing revert error entries.
    """
    # A field's current error is found in field.errors (non-null)
    error_field_ids = {error.record_id for error in existing_errors}
    revert_errors: List[FormRecordUpdateDTO] = []

    for field in fields:
        if field.id in error_field_ids:
            continue
        if field.errors is not None:
            revert_errors.append(FormRecordUpdateDTO(
                formId=form_id,
                recordId=field.id,
                parentRecordId=None,
                deleted=False,
                fields={
                    "ERRS": ""
                },
            ))
            logging.info(f"Creating revert error entry for field {field.id} as errors are now resolved")
    return revert_errors