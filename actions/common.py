import logging
from enum import StrEnum, auto
from typing import Optional, Dict, List

from actions.models import RecordError, RecordAction, RecordUpdateAction
from api import ActivityInfoClient
from api.models import Resource


class DatabaseTreeResourceType(StrEnum):
    FORM = "FORM"
    # We do not care about other resource types for our purposes
    OTHER = auto()


async def resolve_form_from_prefix(client: ActivityInfoClient, database_id: str, sys_prefix: str) -> Optional[Resource]:
    """Resolves the form corresponding to a given system prefix in the database tree."""
    database_tree = await client.api.get_database_tree(database_id)
    for res in database_tree.resources:
        if res.label.split("_")[0] == sys_prefix and res.type == DatabaseTreeResourceType.FORM:
            return res
    return None


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
            if el.type.upper() in ["REFERENCE",
                                   "MULTISELECTREFERENCE"] and el.type_parameters and el.type_parameters.range:
                for r in el.type_parameters.range:
                    ref_form_id = r.get("formId") or r.get("formClassId")
                    if ref_form_id:
                        if ref_form_id not in visited_forms and ref_form_id not in pending_forms:
                            pending_forms.append(ref_form_id)

            if el.type.upper() == "SUBFORM" and el.type_parameters and el.type_parameters.form_id:
                ref_form_id = el.type_parameters.form_id
                if ref_form_id not in visited_forms and ref_form_id not in pending_forms:
                    pending_forms.append(ref_form_id)

    logging.info(f"Collected {len(mappings)} field mappings across {len(visited_forms)} forms")

    return mappings


async def convert_errors_to_record_actions(errors: List[RecordError]) -> List[RecordAction]:
    res: List[RecordAction] = []
    for e in errors:
        res.append(RecordUpdateAction(
            origin=e.origin,
            order=0,
            record_id=e.record_id,
            form_name=e.form_name,
            form_id=e.form_id,
            field_code="ERRS",
            field_value=e.error_message
        ))
    return res
