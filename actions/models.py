from typing import Dict, Any, Union, Optional, List, ClassVar, Literal

from pydantic import BaseModel

from actions.dtos import SchemaFieldUpdateDTO


class ActionBase(BaseModel):
    origin: Optional[str]


# ------ RECORD ACTIONS ------


class RecordBase(ActionBase):
    form_id: str
    form_name: str
    record_id: str
    parent_record_id: Optional[str] = None


class RecordDeleteAction(RecordBase):
    TYPE: Literal["DELETE"] = "DELETE"
    pass


class RecordUpdateAction(RecordBase):
    TYPE: Literal["UPDATE"] = "UPDATE"
    order: int
    field_code: str
    field_value: str | float | int | None
    old_field_value: Optional[str | float | int] = None


class RecordCreateAction(RecordBase):
    TYPE: Literal["CREATE"] = "CREATE"
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
    TYPE: Literal["DELETE"] = "DELETE"
    order: int
    old_formula: Optional[str] = None
    pass


class FieldUpdateAction(FieldBase):
    TYPE: Literal["UPDATE"] = "UPDATE"
    order: int
    old: SchemaFieldUpdateDTO
    new: SchemaFieldUpdateDTO


class FieldCreateAction(FieldBase, SchemaFieldUpdateDTO):
    TYPE: Literal["CREATE"] = "CREATE"
    order: int


FieldAction = Union[FieldCreateAction, FieldUpdateAction, FieldDeleteAction]


# ------ Changeset ------

class Changeset(BaseModel):
    record_actions: List[RecordAction] = []
    field_actions: List[FieldAction] = []
    logs: List[str] = []

    def __add__(self, other: "Changeset") -> "Changeset":
        if not isinstance(other, Changeset):
            return NotImplemented
        return Changeset(
            record_actions=self.record_actions + other.record_actions,
            field_actions=self.field_actions + other.field_actions,
            logs=self.logs + other.logs
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert changeset to dict using aliases for compatibility with ActivityInfo API and correct serialization."""
        return self.model_dump(by_alias=True)


# ------ Errors ------

class RecordError(RecordBase):
    form_name: str
    field_code: str
    error_message: str