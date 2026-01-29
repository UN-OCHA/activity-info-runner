import logging
from typing import List, Tuple, Iterable, TypeVar, Callable, Dict, Any, Union

from pydantic import BaseModel, Field
from temporalio import activity

from blob_store import BlobRef, load_blob
from scripts.dtos import SchemaFieldDTO
from scripts.models import Changeset, RecordAction, FieldAction, FormAction, DatabaseAction, SchemaSnapshot, \
    DatabaseDeleteAction, DatabaseCreateAction, DatabaseUpdateAction, FormSchema, FormDeleteAction, FormCreateAction, \
    FormUpdateAction, FieldDeleteAction, FieldCreateAction, FieldUpdateAction, RecordDeleteAction, RecordCreateAction, \
    RecordUpdateAction

ORIGIN = "generate_changeset"


class RecordDTO(BaseModel):
    id: str
    # Dictionary mapping Field Codes -> Values
    fields: Dict[str, Any] = Field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)


@activity.defn
async def generate_changeset(materialized_boundary: Union[SchemaSnapshot, BlobRef],
                             desired_schema: Union[SchemaSnapshot, BlobRef]) -> Tuple[
    Changeset, List[str]]:
    """
    aka Gen2 Generic Script
    Temporal Activity: Compares the materialized state against the desired state to produce a changeset.

    This function calculates the difference (diff) between what currently exists in ActivityInfo
    (materialized_boundary) and what the user wants to exist (desired_schema). It returns
    a Changeset object containing the necessary Create, Update, and Delete actions to
    reconcile the two states.

    Args:
        materialized_boundary: The current state of resources in ActivityInfo.
        desired_schema: The target state defined by the user script.

    Returns:
        A tuple containing:
        1. Changeset: The collection of actions required to synchronize the states.
        2. List[str]: A list of warning messages generated during the diff process.
    """
    logging.info(f"Generating changeset")
    materialized_boundary = await load_blob(materialized_boundary)
    desired_schema = await load_blob(desired_schema)
    all_db_actions: List[DatabaseAction] = []
    all_form_actions: List[FormAction] = []
    all_field_actions: List[FieldAction] = []
    all_record_actions: List[RecordAction] = []
    warnings: List[str] = []

    db_matches, db_deletes, db_creates, db_warnings = match_resources(
        current=materialized_boundary.databases,
        desired=desired_schema.databases,
        id_getter=lambda d: d.databaseId,
        fallback_key=lambda d: d.label,
    )
    warnings.extend(db_warnings)
    for db in db_deletes:
        all_db_actions.append(DatabaseDeleteAction(origin=ORIGIN, database_id=db.databaseId))
    for db in db_creates:
        all_db_actions.append(DatabaseCreateAction(
            origin=ORIGIN,
            database_id="",
            label=db.label,
            description=db.description
        ))
        # Important: We cannot recurse into "Creates" yet because the Parent DB
        # doesn't exist. Typically, we create the DB first, then run a second pass.
        # For now, we assume we skip children of new DBs until the next run.
    for current_db, desired_db in db_matches:
        if (current_db.label != desired_db.label or
                current_db.description != desired_db.description):
            all_db_actions.append(DatabaseUpdateAction(
                origin=ORIGIN,
                database_id=current_db.databaseId,
                old_database=current_db,
                new_database=desired_db,
            ))
        f_actions, f_field_actions, f_record_actions, f_warnings = await generate_form_changes(
            current_db.databaseId,
            current_db.forms,
            desired_db.forms
        )
        all_form_actions.extend(f_actions)
        all_field_actions.extend(f_field_actions)
        all_record_actions.extend(f_record_actions)
        warnings.extend(f_warnings)
    return Changeset(
        record_actions=all_record_actions,
        field_actions=all_field_actions,
        form_actions=all_form_actions,
        database_actions=all_db_actions
    ), warnings


async def generate_form_changes(
        database_id: str,
        current_forms: List[FormSchema],
        desired_forms: List[FormSchema]
) -> Tuple[List[FormAction], List[FieldAction], List[RecordAction], List[str]]:
    """
    Calculates the diff for Forms within a specific Database.

    Args:
        database_id: The ID of the database being processed.
        current_forms: List of existing forms in the database.
        desired_forms: List of desired forms for the database.

    Returns:
        Tuple[List[FormAction], List[FieldAction], List[RecordAction], List[str]]:
        A tuple containing lists of form actions, field actions, record actions, and warnings.
    """
    f_actions: List[FormAction] = []
    field_actions: List[FieldAction] = []
    record_actions: List[RecordAction] = []
    warnings: List[str] = []

    matches, deletes, creates, w = match_resources(
        current=current_forms,
        desired=desired_forms,
        id_getter=lambda f: f.id,
        fallback_key=lambda f: f.label,
    )
    warnings.extend(w)
    for form in deletes:
        f_actions.append(FormDeleteAction(origin=ORIGIN, form_id=form.id, database_id=form.databaseId))
    for form in creates:
        f_actions.append(FormCreateAction(origin=ORIGIN, form_id="", label=form.label, database_id=form.databaseId))
    for current_f, desired_f in matches:
        if current_f.label != desired_f.label:
            f_actions.append(FormUpdateAction(
                origin=ORIGIN,
                form_id=current_f.id,
                database_id=current_f.databaseId,
                old_label=current_f.label,
                new_label=desired_f.label,
            ))
        fd_actions, fd_warnings = generate_field_changes(database_id, current_f.id, current_f.fields, desired_f.fields)
        field_actions.extend(fd_actions)
        warnings.extend(fd_warnings)
        rc_actions, rc_warnings = generate_record_changes(
            form_id=current_f.id,
            current_records=current_f.records,
            desired_records=desired_f.records
        )
        record_actions.extend(rc_actions)
        warnings.extend(rc_warnings)
    return f_actions, field_actions, record_actions, warnings


def generate_field_changes(
        database_id: str,
        form_id: str,
        current_fields: List[SchemaFieldDTO],
        desired_fields: List[SchemaFieldDTO]
) -> Tuple[List[FieldAction], List[str]]:
    """
    Calculates the diff for Fields within a specific Form.

    Args:
        database_id: The ID of the database containing the form.
        form_id: The ID of the form containing the fields.
        current_fields: List of existing fields in the form.
        desired_fields: List of desired fields for the form.

    Returns:
        Tuple[List[FieldAction], List[str]]: A tuple containing field actions and warnings.
    """
    actions: List[FieldAction] = []
    warnings: List[str] = []

    matches, deletes, creates, w = match_resources(
        current=current_fields,
        desired=desired_fields,
        id_getter=lambda f: f.id,
        fallback_key=lambda f: f.code or f.label,  # Use Code, fall back to Label
    )
    warnings.extend(w)
    for field in deletes:
        actions.append(FieldDeleteAction(origin=ORIGIN, database_id=database_id, form_id=form_id, field_id=field.id))
    for field in creates:
        actions.append(FieldCreateAction(
            origin="reconciler",
            database_id=database_id,
            form_id=form_id,
            **field.model_dump(exclude={'id'})
        ))
    for current_f, desired_f in matches:
        if current_f.model_dump(exclude={'id'}) != desired_f.model_dump(exclude={'id'}):
            actions.append(FieldUpdateAction(
                origin="reconciler",
                database_id=database_id,
                form_id=form_id,
                field_id=current_f.id,
                old_field=current_f,
                new_field=desired_f
            ))
    return actions, warnings


def generate_record_changes(
        form_id: str,
        current_records: List[Dict[str, Any]],
        desired_records: List[Dict[str, Any]]
) -> Tuple[List[RecordAction], List[str]]:
    """
    Calculates the diff for Records within a specific Form, handling field-level updates.

    Args:
        form_id: The ID of the form containing the records.
        current_records: List of existing records in the form.
        desired_records: List of desired records for the form.

    Returns:
        Tuple[List[RecordAction], List[str]]: A tuple containing record actions and warnings.
    """
    actions: List[RecordAction] = []
    warnings: List[str] = []

    matches, deletes, creates, w = match_resources(
        current=current_records,
        desired=desired_records,
        id_getter=lambda r: r.get("@id"),
        # Records usually don't have a reliable fallback key like "label" unless
        # specifically defined. We disable fallback matching to avoid dangerous
        # data overwrites based on vague similarities.
        fallback_key=lambda r: "",
    )
    warnings.extend(w)

    for rec in deletes:
        actions.append(RecordDeleteAction(
            origin=ORIGIN,
            form_id=form_id,
            record_id=rec.get("@id"),
            parent_record_id=None
        ))
    for rec in creates:
        actions.append(RecordCreateAction(
            origin=ORIGIN,
            form_id=form_id,
            record_id="",
            parent_record_id=None,
            fields=rec
        ))
    for current_r, desired_r in matches:
        for field_code, desired_value in desired_r.items():
            current_value = current_r.get(field_code)
            if not _are_values_equal(current_value, desired_value):
                actions.append(RecordUpdateAction(
                    origin=ORIGIN,
                    form_id=form_id,
                    record_id=current_r.get("@id"),
                    parent_record_id=None,
                    field_code=field_code,
                    field_value=desired_value,
                    old_field_value=current_value
                ))
    return actions, warnings


T = TypeVar("T")

# A unique identifier (empty string means "unset")
Identifier = str

# A fallback key used when ID is missing
FallbackKey = str


def match_resources(
        current: Iterable[T],
        desired: Iterable[T],
        *,
        id_getter: Callable[[T], Identifier],
        fallback_key: Callable[[T], FallbackKey],
) -> Tuple[
    List[Tuple[T, T]],
    List[T],
    List[T],
    List[str]
]:
    """
    Match two collections of resources using a two-phase strategy.

    Matching rules (in order):
      1. Match by ID if the ID is set (non-empty string)
      2. Fallback match by a secondary identifying key (label, code, etc.)

    Guarantees:
      - Each resource is matched at most once
      - ID-based matches always take precedence
      - Fallback matches are skipped if ambiguous
      - Ambiguities are reported via warnings

    Args:
        current: Iterable of existing (materialized) resources.
        desired: Iterable of desired (target) resources.
        id_getter: Function returning the resource ID. Empty string ("") is treated as "ID not set".
        fallback_key: Function returning a secondary identifying key used only when ID-based matching fails.

    Returns:
        matched: List of tuples (current, desired) for resources that were matched.
        deletes: Resources present in `current` but not matched.
        creates: Resources present in `desired` but not matched.
        warnings: List of warnings encountered.
    """
    current_list: List[T] = list(current)
    desired_list: List[T] = list(desired)
    matched: List[Tuple[T, T]] = []
    matched_current_indices = set()
    matched_desired_indices = set()
    warnings: List[str] = []

    # ---- Phase 1: Match by ID ----
    current_by_id: Dict[Identifier, int] = {}
    for i, c in enumerate(current_list):
        ident = id_getter(c)
        if ident:
            current_by_id[ident] = i

    desired_by_id: Dict[Identifier, int] = {}
    for i, d in enumerate(desired_list):
        ident = id_getter(d)
        if ident:
            desired_by_id[ident] = i

    for resource_id, current_idx in current_by_id.items():
        desired_idx = desired_by_id.get(resource_id)
        if desired_idx is not None:
            matched.append((current_list[current_idx], desired_list[desired_idx]))
            matched_current_indices.add(current_idx)
            matched_desired_indices.add(desired_idx)

    unmatched_current_indices = [i for i in range(len(current_list)) if i not in matched_current_indices]
    unmatched_desired_indices = [i for i in range(len(desired_list)) if i not in matched_desired_indices]

    # ---- Phase 2: Match by fallback key ----
    desired_by_fallback: Dict[FallbackKey, List[int]] = {}
    for idx in unmatched_desired_indices:
        d = desired_list[idx]
        key = fallback_key(d)
        desired_by_fallback.setdefault(key, []).append(idx)

    for current_idx in unmatched_current_indices:
        c = current_list[current_idx]
        key = fallback_key(c)
        candidate_indices = desired_by_fallback.get(key, [])
        if len(candidate_indices) == 1:
            desired_idx = candidate_indices[0]
            matched.append((c, desired_list[desired_idx]))
            matched_current_indices.add(current_idx)
            matched_desired_indices.add(desired_idx)
            desired_by_fallback[key].remove(desired_idx)

        elif len(candidate_indices) > 1:
            warnings.append(f"Ambiguous fallback match for key '{key}'.")

    # Re-calculate unmatched based on indices
    final_deletes = [current_list[i] for i in range(len(current_list)) if i not in matched_current_indices]
    final_creates = [desired_list[i] for i in range(len(desired_list)) if i not in matched_desired_indices]

    return matched, final_deletes, final_creates, warnings


def _are_values_equal(val1: Any, val2: Any) -> bool:
    """
    Custom equality check to handle ActivityInfo specific quirks
    (e.g., None vs empty string, float vs int).
    """
    if val1 == val2:
        return True

    # normalize None and empty strings
    v1_norm = "" if val1 is None else val1
    v2_norm = "" if val2 is None else val2
    if v1_norm == v2_norm:
        return True

    return False
