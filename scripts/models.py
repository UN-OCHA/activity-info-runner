from enum import Enum
from typing import Dict, Any, Union, Optional, List, Literal

from pydantic import BaseModel, Field

from scripts.dtos import SchemaFieldDTO


# ------ BOUNDARIES ------

# TODO: Add record boundary by key field formula

class RecordExactBoundary(BaseModel):
    record_ids: List[str]


class AllRecordsBoundary(BaseModel):
    pass


RecordBoundary = Union[RecordExactBoundary, AllRecordsBoundary]


class FieldIdentifierType(str, Enum):
    id = 'id'
    code = 'code'
    label = 'label'


class FieldBoundary(BaseModel):
    identifier: str
    identifier_type: FieldIdentifierType
    identifier_is_regex: bool = False

    @classmethod
    def code(cls, pattern: str, is_regex: bool = False) -> "FieldBoundary":
        return cls(identifier=pattern, identifier_type=FieldIdentifierType.code, identifier_is_regex=is_regex)

    @classmethod
    def label(cls, pattern: str, is_regex: bool = False) -> "FieldBoundary":
        return cls(identifier=pattern, identifier_type=FieldIdentifierType.label, identifier_is_regex=is_regex)


class FormIdentifierType(str, Enum):
    id = 'id'
    label = 'label'


class FormBoundary(BaseModel):
    identifier: str
    identifier_type: FormIdentifierType
    identifier_is_regex: bool = False
    field_boundaries: List[FieldBoundary] = Field(default_factory=list)
    record_boundaries: List[RecordBoundary] = Field(default_factory=list)

    @classmethod
    def label(cls, pattern: str, is_regex: bool = False) -> "FormBoundary":
        return cls(identifier=pattern, identifier_type=FormIdentifierType.label, identifier_is_regex=is_regex)

    @classmethod
    def id(cls, pattern: str) -> "FormBoundary":
        return cls(identifier=pattern, identifier_type=FormIdentifierType.id, identifier_is_regex=False)

    # Fluent Builders
    def with_all_records(self) -> "FormBoundary":
        self.record_boundaries.append(AllRecordsBoundary())
        return self

    def with_fields(self, *fields: FieldBoundary) -> "FormBoundary":
        self.field_boundaries.extend(fields)
        return self


class DatabaseIdentifierType(str, Enum):
    id = 'id'
    label = 'label'


class DatabaseBoundary(BaseModel):
    identifier: str
    identifier_type: DatabaseIdentifierType
    identifier_is_regex: bool = False
    form_boundaries: List[FormBoundary]

    @classmethod
    def id(cls, identifier: str, forms: List[FormBoundary] = None) -> "DatabaseBoundary":
        return cls(
            identifier=identifier,
            identifier_type=DatabaseIdentifierType.id,
            form_boundaries=forms or []
        )


class ScriptBoundary(BaseModel):
    database_boundaries: List[DatabaseBoundary]

    @classmethod
    def for_databases(cls, ids: List[str], forms: List[FormBoundary]) -> "ScriptBoundary":
        """Helper to apply the same form boundaries to multiple databases (common pattern)"""
        return cls(database_boundaries=[
            DatabaseBoundary.id(ident, forms=forms) for ident in ids
        ])

    @staticmethod
    def builder() -> "ScriptBoundaryBuilder":
        return ScriptBoundaryBuilder()


class ScriptBoundaryBuilder:
    def __init__(self):
        self._db_ids: List[str] = []
        self._forms: List[FormBoundary] = []

    def select_databases(self, ids: List[str]) -> "ScriptBoundaryBuilder":
        self._db_ids.extend(ids)
        return self

    def form(self, label_regex: str = None, id_regex: str = None) -> "FormBoundaryBuilder":
        return FormBoundaryBuilder(self, label_regex, id_regex)

    def _add_form(self, form: FormBoundary):
        self._forms.append(form)

    def build(self) -> ScriptBoundary:
        return ScriptBoundary.for_databases(self._db_ids, self._forms)


class FormBoundaryBuilder:
    def __init__(self, parent: ScriptBoundaryBuilder, label_regex: str = None, id_regex: str = None):
        self.parent = parent
        if label_regex:
            self.boundary = FormBoundary.label(label_regex, is_regex=True)
        elif id_regex:
            self.boundary = FormBoundary.id(id_regex) # ID usually exact, but let's stick to existing factory
        else:
             raise ValueError("Must provide label_regex or id_regex")

    def with_all_records(self) -> "FormBoundaryBuilder":
        self.boundary.with_all_records()
        return self

    def with_fields(self, code_regex: str = None) -> "FormBoundaryBuilder":
        if code_regex:
            self.boundary.with_fields(FieldBoundary.code(code_regex, is_regex=True))
        return self

    def form(self, label_regex: str = None, id_regex: str = None) -> "FormBoundaryBuilder":
        """Chains to a new form, effectively 'closing' the current one."""
        self.parent._add_form(self.boundary)
        return self.parent.form(label_regex, id_regex)

    def build(self) -> ScriptBoundary:
        """Finishes the builder."""
        self.parent._add_form(self.boundary)
        return self.parent.build()


# ------ SCHEMAS ------

class FormSchema(BaseModel):
    id: str
    databaseId: str
    label: str
    fields: List[SchemaFieldDTO]
    records: List[Dict[str, Any]]

    def __hash__(self):
        return hash(self.id)

    def find_field(self, code_pattern: str = None, label_pattern: str = None, is_regex: bool = False) -> Optional[SchemaFieldDTO]:
        """Finds a single field matching the criteria."""
        return next(self._filter_fields(code_pattern, label_pattern, is_regex), None)

    def select_fields(self, code_pattern: str = None, label_pattern: str = None, is_regex: bool = False) -> List[SchemaFieldDTO]:
        """Returns all fields matching the criteria."""
        return list(self._filter_fields(code_pattern, label_pattern, is_regex))

    def _filter_fields(self, code_pattern: str, label_pattern: str, is_regex: bool):
        import re
        for field in self.fields:
            if code_pattern:
                if is_regex:
                    if not re.search(code_pattern, field.code): continue
                elif field.code != code_pattern and not field.code.startswith(code_pattern):
                    # Defaulting to strict match for non-regex unless context implies otherwise, but given the user's previous code used startswith,
                    # let's be flexible or strict. Strict is safer for libraries.
                    if field.code != code_pattern: continue
            
            if label_pattern:
                if is_regex:
                    if not re.search(label_pattern, field.label): continue
                elif field.label != label_pattern: continue
            
            yield field


class DatabaseSchema(BaseModel):
    databaseId: str
    label: str
    description: str
    forms: List[FormSchema]

    def __hash__(self):
        return hash(self.label) + hash(self.description)

    def find_form(self, id_pattern: str = None, label_pattern: str = None, is_regex: bool = False) -> Optional[FormSchema]:
         return next(self._filter_forms(id_pattern, label_pattern, is_regex), None)

    def select_forms(self, id_pattern: str = None, label_pattern: str = None, is_regex: bool = False) -> List[FormSchema]:
        return list(self._filter_forms(id_pattern, label_pattern, is_regex))

    def _filter_forms(self, id_pattern: str, label_pattern: str, is_regex: bool):
        import re
        for form in self.forms:
            if id_pattern:
                if is_regex:
                    if not re.search(id_pattern, form.id): continue
                elif form.id != id_pattern: continue
            
            if label_pattern:
                if is_regex:
                    if not re.search(label_pattern, form.label): continue
                elif form.label != label_pattern: continue
            
            yield form


class SchemaSnapshot(BaseModel):
    databases: List[DatabaseSchema]


# ------ ACTIONS ------


class ActionBase(BaseModel):
    origin: Optional[str]


# ------ RECORD ACTIONS ------


class RecordBase(ActionBase):
    form_id: str
    record_id: str
    parent_record_id: Optional[str] = None


class RecordDeleteAction(RecordBase):
    TYPE: Literal["DELETE"] = "DELETE"
    pass


class RecordUpdateAction(RecordBase):
    TYPE: Literal["UPDATE"] = "UPDATE"
    field_code: str
    field_value: str | float | int | None
    old_field_value: Optional[str | float | int] = None


class RecordCreateAction(RecordBase):
    TYPE: Literal["CREATE"] = "CREATE"
    fields: Dict[str, Any]


RecordAction = Union[RecordCreateAction, RecordUpdateAction, RecordDeleteAction]


# ------ FIELD ACTIONS ------

class FieldBase(ActionBase):
    database_id: str
    form_id: str
    field_id: str


class FieldDeleteAction(FieldBase):
    TYPE: Literal["DELETE"] = "DELETE"


class FieldUpdateAction(FieldBase):
    TYPE: Literal["UPDATE"] = "UPDATE"
    old_field: SchemaFieldDTO
    new_field: SchemaFieldDTO


class FieldCreateAction(FieldBase, SchemaFieldDTO):
    TYPE: Literal["CREATE"] = "CREATE"


FieldAction = Union[FieldCreateAction, FieldUpdateAction, FieldDeleteAction]


# ------ FORM ACTIONS ------

class FormBase(ActionBase):
    form_id: str
    database_id: str


class FormDeleteAction(FormBase):
    TYPE: Literal["DELETE"] = "DELETE"


class FormUpdateAction(FormBase):
    TYPE: Literal["DELETE"] = "UPDATE"
    old_label: str
    new_label: str


class FormCreateAction(FormBase):
    TYPE: Literal["CREATE"] = "CREATE"
    label: str


FormAction = Union[FormCreateAction, FormUpdateAction, FormDeleteAction]


# ------ DATABASE ACTIONS ------

class DatabaseBase(ActionBase):
    database_id: str


class DatabaseDeleteAction(DatabaseBase):
    TYPE: Literal["DELETE"] = "DELETE"


class DatabaseUpdateAction(DatabaseBase):
    TYPE: Literal["UPDATE"] = "UPDATE"
    old_database: DatabaseSchema
    new_database: DatabaseSchema


class DatabaseCreateAction(DatabaseBase):
    TYPE: Literal["CREATE"] = "CREATE"
    label: str
    description: str


DatabaseAction = Union[DatabaseCreateAction, DatabaseUpdateAction, DatabaseDeleteAction]


# ------ Changeset ------

class Changeset(BaseModel):
    record_actions: List[RecordAction] = Field(default_factory=list)
    field_actions: List[FieldAction] = Field(default_factory=list)
    form_actions: List[FormAction] = Field(default_factory=list)
    database_actions: List[DatabaseAction] = Field(default_factory=list)

    def __add__(self, other: "Changeset") -> "Changeset":
        if not isinstance(other, Changeset):
            return NotImplemented
        return Changeset(
            record_actions=self.record_actions + other.record_actions,
            field_actions=self.field_actions + other.field_actions,
            form_actions=self.form_actions + other.form_actions,
            database_actions=self.database_actions + other.database_actions,
        )

    def as_tuple(self):
        return self.record_actions, self.field_actions, self.form_actions, self.database_actions

    @classmethod
    def from_tuple(cls, t):
        return cls(record_actions=t[0], field_actions=t[1], form_actions=t[2], database_actions=t[3])

    @classmethod
    def from_record_actions(cls, a: List[RecordAction]):
        return cls(record_actions=a, field_actions=[], form_actions=[], database_actions=[])

    @classmethod
    def from_field_actions(cls, a: List[FieldAction]):
        return cls(record_actions=[], field_actions=a, form_actions=[], database_actions=[])

    @classmethod
    def from_form_actions(cls, a: List[FormAction]):
        return cls(record_actions=[], field_actions=[], form_actions=a, database_actions=[])

    @classmethod
    def from_database_actions(cls, a: List[DatabaseAction]):
        return cls(record_actions=[], field_actions=[], form_actions=[], database_actions=a)

    def __len__(self) -> int:
        return len(self.record_actions) + len(self.field_actions) + len(self.form_actions) + len(self.database_actions)

    def to_dict(self) -> Dict[str, Any]:
        """Convert changeset to dict using aliases for compatibility with ActivityInfo API and correct serialization."""
        return self.model_dump(by_alias=True)
