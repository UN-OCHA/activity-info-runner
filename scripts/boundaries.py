import asyncio
import logging
import os
import re
from typing import Dict, Tuple, List, Any, Union

from temporalio import activity

from api import ActivityInfoClient
from api.client import BASE_URL
from blob_store import save_blob, BlobRef
from scripts.dtos import DatabaseTreeResourceType, SchemaFieldDTO
from scripts.models import ScriptBoundary, DatabaseIdentifierType, FormBoundary, FormIdentifierType, FieldBoundary, \
    RecordBoundary, FieldIdentifierType, SchemaSnapshot, DatabaseSchema, FormSchema, RecordExactBoundary

# Global semaphore to throttle concurrent API requests across this worker.
CONCURRENCY_LIMIT = asyncio.Semaphore(10)


async def with_semaphore(coro):
    """
    Wraps a coroutine to enforce the global CONCURRENCY_LIMIT.

    This ensures that we do not overwhelm the ActivityInfo API or the local
    worker resources when processing many boundaries in parallel.
    """
    async with CONCURRENCY_LIMIT:
        return await coro


@activity.defn
async def materialize_boundary(boundaries: ScriptBoundary) -> Tuple[Union[SchemaSnapshot, BlobRef], List[str]]:
    """
    aka Gen1 Generic Script
    Temporal Activity: Resolves abstract ScriptBoundaries into a concrete SchemaSnapshot.

    This function takes user-defined rules (e.g., "All databases matching 'HPC._*'") and
    resolves them into actual resources (Ids, Fields, etc...). It performs
    lookups against the ActivityInfo API in parallel, respecting rate limits.

    Args:
        boundaries: The abstract definition of what resources this script should manage.

    Returns:
        A tuple containing:
        1. SchemaSnapshot (or BlobRef): The concrete tree of resources to be diffed later.
        2. List[str]: A list of warning messages (e.g., if a label wasn't found).

    Raises:
        RuntimeError: If any sub-task fails (e.g., network error fetching a database tree).
    """
    warnings: List[str] = []
    client = ActivityInfoClient(BASE_URL, os.getenv("API_TOKEN"))
    materialized_databases: List[DatabaseSchema] = []
    existing_databases = await client.api.get_user_databases()
    database_dict = {db.label: db for db in existing_databases}
    for database_boundary in boundaries.database_boundaries:
        if database_boundary.identifier_type == DatabaseIdentifierType.id:
            matching_databases = [db for db in existing_databases if db.databaseId == database_boundary.identifier]
        else:  # database_boundary.identifier_type == DatabaseIdentifierType.label
            matching_databases = match_identifier(database_boundary.identifier, database_boundary.identifier_is_regex,
                                                  database_dict)
        if len(matching_databases) == 0:
            warnings.append(
                f"Database identifier {database_boundary.identifier} of type {database_boundary.identifier_type} could not be materialized.")
        tasks = [with_semaphore(
            materialize_form_boundaries(client, database.databaseId, database_boundary.form_boundaries))
            for
            database in matching_databases]
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        for i in range(len(task_results)):
            if isinstance(task_results[i], Exception):
                raise RuntimeError(
                    f"Failed to materialize database boundary {database_boundary.identifier}: {task_results[i]}")
            else:
                forms, w = task_results[i]
                materialized_databases.append(DatabaseSchema(
                    databaseId=matching_databases[i].databaseId,
                    label=matching_databases[i].label,
                    description=matching_databases[i].description,
                    forms=forms,
                ))
                warnings.extend(w)
    if len(materialized_databases) == 0:
        warnings.append(f"No materialized database boundaries were found.")

    snapshot = SchemaSnapshot(databases=materialized_databases)
    # Always offload to blob store to avoid message size limits
    blob_ref = await save_blob(snapshot)
    return blob_ref, warnings


async def materialize_form_boundaries(client: ActivityInfoClient, database_id: str,
                                      form_boundaries: List[FormBoundary]) -> Tuple[List[FormSchema], List[str]]:
    """
    Resolves Form boundaries within a specific Database.

    Args:
        client: The API client instance.
        database_id: The specific ActivityInfo Database ID to inspect.
        form_boundaries: List of abstract form rules to resolve.

    Returns:
        Tuple[List[FormSchema], List[str]]: Concrete form boundaries and warnings.
    """
    logging.info(f"Materializing Form boundaries for database id {database_id}")
    warnings: List[str] = []
    materialized_forms: List[FormSchema] = []
    tree = await client.api.get_database_tree(database_id)
    forms_dict = {res.label: res for res in tree.resources if res.type == DatabaseTreeResourceType.FORM}
    for form_boundary in form_boundaries:
        if form_boundary.identifier_type == FormIdentifierType.id:
            matching_forms = [form for form in forms_dict.values() if form.id == form_boundary.identifier]
        else:  # form_boundary.identifier_type == FormIdentifierType.label
            matching_forms = match_identifier(form_boundary.identifier, form_boundary.identifier_is_regex, forms_dict)
        if len(matching_forms) == 0:
            warnings.append(
                f"Form identifier {form_boundary.identifier} of type {form_boundary.identifier_type} could not be materialized for database id {database_id}.")
        tasks = [with_semaphore(
            materialize_field_and_record_boundaries(client, form.id, form_boundary.field_boundaries,
                                                    form_boundary.record_boundaries))
            for
            form in matching_forms]
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        for i in range(len(task_results)):
            if isinstance(task_results[i], Exception):
                raise RuntimeError(f"Failed to materialize form boundary {form_boundary.identifier}: {task_results[i]}")
            else:
                fields, records, w = task_results[i]
                materialized_forms.append(FormSchema(
                    id=matching_forms[i].id,
                    databaseId=database_id,
                    label=matching_forms[i].label,
                    fields=fields,
                    records=records,
                ))
                warnings.extend(w)
    if len(materialized_forms) == 0:
        warnings.append(f"No materialized form boundaries were found for database id {database_id}.")
    return materialized_forms, warnings


async def materialize_field_and_record_boundaries(client: ActivityInfoClient, form_id: str,
                                                  field_boundaries: List[FieldBoundary],
                                                  record_boundaries: List[RecordBoundary]) -> Tuple[
    List[SchemaFieldDTO], List[Dict[str, Any]], List[str]]:
    """
    Resolves Field and Record boundaries for a specific Form.

    This function fetches the schema only once and performs CPU-bound matching
    for all field boundaries.

    Args:
        client: The API client instance.
        form_id: The specific Form ID to inspect.
        field_boundaries: Rules for which columns/fields to manage.
        record_boundaries: Rules for which rows/records to manage.

    Returns:
        Tuple[List[SchemaFieldDTO], List[Dict[str, Any]], List[str]]: Concrete field/record boundaries and warnings.
    """
    logging.info(f"Materializing Field boundaries for form id {form_id}")
    warnings: List[str] = []
    materialized_field_boundaries: List[SchemaFieldDTO] = []
    materialized_record_boundaries: List[Dict[str, Any]] = []
    schema = await client.api.get_form_schema(form_id)
    records = await client.api.get_form(form_id)
    fields_by_code = {elem.code: elem for elem in schema.elements}
    fields_by_label = {elem.label: elem for elem in schema.elements}
    for field_boundary in field_boundaries:
        if field_boundary.identifier_type == FieldIdentifierType.id:
            matching_fields = [field for field in schema.elements if field.id == field_boundary.identifier]
        elif field_boundary.identifier_type == FieldIdentifierType.code:
            matching_fields = match_identifier(field_boundary.identifier, field_boundary.identifier_is_regex,
                                               fields_by_code)
        else:  # field_boundary.identifier_type == FieldIdentifierType.label
            matching_fields = match_identifier(field_boundary.identifier, field_boundary.identifier_is_regex,
                                               fields_by_label)
        if len(matching_fields) == 0:
            warnings.append(
                f"Field identifier {field_boundary.identifier} of type {field_boundary.identifier_type} could not be materialized for form id {form_id}.")
        materialized_field_boundaries.extend(matching_fields)
    if len(materialized_field_boundaries) == 0:
        warnings.append(f"No materialized field boundaries were found for form id {form_id}.")
    for record_boundary in record_boundaries:
        if isinstance(record_boundary, RecordExactBoundary):
            materialized_record_boundaries = [r for r in records if (r.get('@id') in record_boundary.record_ids)]
        else:
            materialized_record_boundaries = records
    if len(materialized_record_boundaries) == 0:
        warnings.append(f"No materialized record boundaries were found for form id {form_id}.")
    return materialized_field_boundaries, materialized_record_boundaries, warnings


def match_identifier(identifier: str, is_regex: bool, items: Dict[str, Any]) -> List[Any]:
    """
    Return values from `items` whose keys match the given identifier.

    If `is_regex` is True, `identifier` is treated as a regular expression
    and matched against each key using `re.search`. If False, keys must
    exactly equal `identifier`.

    Args:
        identifier: A string identifier or regular expression pattern.
        is_regex: Whether to interpret `identifier` as a regex.
        items: A mapping of keys to values to match against.

    Returns:
        A list of values whose corresponding keys match the identifier.
    """
    if is_regex:
        expr = re.compile(identifier)
        return [v for k, v in items.items() if expr.search(k)]
    else:
        return [v for k, v in items.items() if k == identifier]
