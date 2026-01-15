import logging
from typing import List, Optional, Tuple, Any, Dict

from api import ActivityInfoClient
from api.models import OperationCalculationFormulasField
from models import FormChangeset, FormChangesetEntry, FormChangesetPlan, RecordChangesetEntry, RecordChangeset
from enum import StrEnum, auto

from parser import ActivityInfoExpression, DictResolver


class OperationCalculationApplyType(StrEnum):
    INTERNAL = "Internal"
    EXTERNAL = "External"
    UNKNOWN = auto()

class DatabaseTreeResourceType(StrEnum):
    FORM = "FORM"
    OTHER = auto()

async def get_operation_calculation_changesets(client: ActivityInfoClient, database_id: str) -> Tuple[FormChangeset, RecordChangeset]:
    database_tree = await client.api.get_database_tree(database_id)
    form_id = next(
        (res.id for res in database_tree.resources if res.type == "FORM" and res.label.startswith("0.1.5_")),
        None
    )
    res = await client.api.get_operation_calculation_formulas_fields(form_id)
    logging.info(f"Retrieved {len(res)} operation calculation formula fields")
    internal_fields = [field for field in res if field.apply == OperationCalculationApplyType.INTERNAL]
    internal_changeset = await get_internal_operation_calculation_changeset_entries(client, database_id,internal_fields)
    logging.info(f"Computed {len(internal_changeset)} internal changeset entries")
    external_fields = [field for field in res if field.apply == OperationCalculationApplyType.EXTERNAL]
    external_changeset = await get_external_operation_calculation_changeset_entries(client, database_id, external_fields)
    logging.info(f"Computed {len(external_changeset)} external changeset entries")
    form_changeset = FormChangeset(entries=internal_changeset, action="operation_calculation_formulas", title="Internal Changeset")
    record_changeset = RecordChangeset(entries=external_changeset, action="operation_calculation_formulas", title="External Changeset")
    return form_changeset, record_changeset

async def get_internal_operation_calculation_changeset_entries(client:ActivityInfoClient, database_id: str, internal_fields: List[OperationCalculationFormulasField]) -> List[FormChangesetEntry]:
    internal_fields.sort(key=lambda x: x.ref_order)
    changeset_plans: List[FormChangesetPlan] = []
    for field in internal_fields:
        form_id = await resolve_form_id_from_prefix(client, database_id, field.sys_prefix)
        logging.info(f"Resolved form ID {form_id} for sys_prefix {field.sys_prefix}")
        changeset_plans.append(FormChangesetPlan(
            calcOrder=field.ref_order,
            formId=form_id,
            fieldCode=f"{field.sys_field}_ICALC",
            newExpression=f"IF({field.filter}, {field.formula})",
        ))
    return await resolve_internal_changeset_plans(client, database_id, changeset_plans)

async def get_external_operation_calculation_changeset_entries(client:ActivityInfoClient, database_id: str, external_fields: List[OperationCalculationFormulasField]) -> List[RecordChangesetEntry]:
    external_fields.sort(key=lambda x: x.ref_order)
    skip_filter_count = 0
    skip_unchanged_count = 0
    changeset_entries: List[RecordChangesetEntry] = []
    for field in external_fields:
        form_id = await resolve_form_id_from_prefix(client, database_id, field.sys_prefix)
        logging.info(f"Resolved form ID {form_id} for sys_prefix {field.sys_prefix}")
        entries = await client.api.get_form(form_id)
        filter_expr = ActivityInfoExpression.parse(field.filter)
        formula_expr = ActivityInfoExpression.parse(field.formula)
        for entry in entries:
            old_fields = {k: entry[k] for k in entry if k not in ('_id', '_lastEditTime') and entry[k] is not None}
            nested_fields = build_nested_dict(old_fields)
            resolver = DictResolver(nested_fields)
            if not filter_expr.evaluate(resolver):
                skip_filter_count += 1
                continue
            record_id = entry.get("@id")
            if not record_id:
                continue
            res = formula_expr.evaluate(resolver)
            if old_fields.get(field.sys_field) == res:
                skip_unchanged_count += 1
                continue
            new_fields = old_fields.copy()
            new_fields[field.sys_field] = res
            changeset_entries.append(RecordChangesetEntry(
                calcOrder=field.ref_order,
                formId=form_id,
                recordId=record_id,
                parentRecordId=None,
                fields=new_fields,
                oldFields=old_fields,
            ))
    logging.info(f"Skipped {skip_filter_count} records due to filter not matching")
    logging.info(f"Skipped {skip_unchanged_count} records due to unchanged values")
    return changeset_entries

def build_nested_dict(flat: Dict[str, Any]) -> Dict:
    nested: Dict = {}
    for key, value in flat.items():
        parts = key.split(".")
        d = nested
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value
    return nested

async def resolve_form_id_from_prefix(client: ActivityInfoClient, database_id: str, sys_prefix: str) -> Optional[str]:
    database_tree = await client.api.get_database_tree(database_id)
    for res in database_tree.resources:
        if res.label.split("_")[0] == sys_prefix and res.type == DatabaseTreeResourceType.FORM:
            return res.id
    return None

async def resolve_internal_changeset_plans(client: ActivityInfoClient, database_id: str, internal_changeset: List[FormChangesetPlan]) -> List[FormChangesetEntry]:
    changeset_entries: List[FormChangesetEntry] = []
    for plan in internal_changeset:
        field_lookup = await collect_field_mappings(client, plan.form_id)
        schema = await client.api.get_form_schema(plan.form_id)
        code_lookup = {el.code: el.id for el in schema.elements}
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
            fieldCode=plan.field_code,
            fieldId=code_lookup[plan.field_code],
            newExpression=plan.new_expression,
            oldExpression=old_expression,
        ))
    return changeset_entries

async def collect_field_mappings(client: ActivityInfoClient, start_form_id: str) -> Dict[str, str]:
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
                            logging.debug(f"Found reference to form {ref_form_id} in field {el.code or 'UNKNOWN'} ({el.id})")
                            pending_forms.append(ref_form_id)
    
    logging.info(f"Collected {len(mappings)} field mappings across {len(visited_forms)} forms")
    return mappings