from typing import Dict, Any, Union, Optional, List, ClassVar

from pydantic import BaseModel

from actions.dtos import FieldType


class ActionBase(BaseModel):
    origin: Optional[str]


# ------ RECORD ACTIONS ------


class RecordBase(ActionBase):
    form_id: str
    form_name: str
    record_id: str
    parent_record_id: Optional[str] = None


class RecordDeleteAction(RecordBase):
    TYPE: ClassVar[str] = "DELETE"
    pass


class RecordUpdateAction(RecordBase):
    TYPE: ClassVar[str] = "UPDATE"
    order: int
    field_code: str
    field_value: str | float | int | None
    old_field_value: Optional[str | float | int] = None


class RecordCreateAction(RecordBase):
    TYPE: ClassVar[str] = "CREATE"
    order: int
    fields: Dict[str, Any]


RecordAction = Union[RecordCreateAction, RecordUpdateAction, RecordDeleteAction]


# ------ SCHEMA ACTIONS ------

class FieldBase(ActionBase):
    database_id: str
    form_id: str
    form_name: str
    field_code: str


class FieldDeleteAction(FieldBase):
    TYPE: ClassVar[str] = "DELETE"
    order: int
    old_formula: Optional[str] = None
    pass


class FieldUpdateAction(FieldBase):
    TYPE: ClassVar[str] = "UPDATE"
    order: int
    relevance_condition: Optional[str] = None
    validation_condition: Optional[str] = None
    formula: Optional[str]
    old_formula: Optional[str] = None


class FieldCreateAction(FieldBase):
    TYPE: ClassVar[str] = "CREATE"
    order: int
    label: str
    relevance_condition: Optional[str] = None
    validation_condition: Optional[str] = None
    data_entry_visible: bool
    table_visible: bool
    required: bool
    key: bool
    type: FieldType
    formula: Optional[str]
    prefix_formula: Optional[str] = None


FieldAction = Union[FieldCreateAction, FieldUpdateAction, FieldDeleteAction]


# ------ Changeset ------

class Changeset(BaseModel):
    record_actions: List[RecordAction] = []
    field_actions: List[FieldAction] = []

    def __add__(self, other: "Changeset") -> "Changeset":
        if not isinstance(other, Changeset):
            return NotImplemented
        return Changeset(
            record_actions=self.record_actions + other.record_actions,
            field_actions=self.field_actions + other.field_actions,
        )

    def as_tuple(self):
        return self.record_actions, self.field_actions

    @classmethod
    def from_tuple(cls, t):
        return cls(record_actions=t[0], field_actions=t[1])

    @classmethod
    def from_record_actions(cls, a: List[RecordAction]):
        return cls(record_actions=a, field_actions=[])

    @classmethod
    def from_field_actions(cls, a: List[FieldAction]):
        return cls(record_actions=[], field_actions=a)

    def __len__(self) -> int:
        return len(self.record_actions) + len(self.field_actions)


# ------ Errors ------

class RecordError(RecordBase):
    form_name: str
    field_code: str
    error_message: str
