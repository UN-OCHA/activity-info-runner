from enum import StrEnum, auto
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, field_validator


class DatabaseTreeResourceType(StrEnum):
    FORM = "FORM"
    # We do not care about other resource types for our purposes
    OTHER = auto()


class FieldType(StrEnum):
    serial = "serial"
    month = "month"
    attachment = "attachment"
    geopoint = "geopoint"
    FREE_TEXT = "FREE_TEXT"
    quantity = "quantity"
    enumerated = "enumerated"
    multiselectreference = "multiselectreference"
    epiweek = "epiweek"
    subform = "subform"
    date = "date"
    calculated = "calculated"
    reversereference = "reversereference"
    reference = "reference"
    fortnight = "fortnight"
    section = "section"
    NARRATIVE = "NARRATIVE"


class FieldTypeParametersCardinality(StrEnum):
    SINGLE = "SINGLE"
    MULTIPLE = "MULTIPLE"


class FieldTypeParametersItemsUpdateDTO(BaseModel):
    id: str = Field(alias="id")
    label: str = Field(alias="label")


class FieldTypeParametersUpdateDTO(BaseModel):
    model_config = {"populate_by_name": True}
    units: Optional[str] = Field(default=None, alias="units")
    input_mask: Optional[str] = Field(default=None, alias="inputMask")
    cardinality: Optional[FieldTypeParametersCardinality] = Field(default=None, alias="cardinality")
    range: Optional[List[Dict[str, str]]] = Field(default=None, alias="range")
    form_id: Optional[str] = Field(default=None, alias="formId")
    items: Optional[List[FieldTypeParametersItemsUpdateDTO]] = Field(default=None, alias="items")
    formula: Optional[str] = Field(default=None, alias="formula")
    prefix_formula: Optional[str] = Field(default=None, alias="prefixFormula")

    @field_validator("cardinality", mode="before")
    @classmethod
    def normalize_cardinality(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("units", mode="before")
    @classmethod
    def normalize_empty_strings(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v


class SchemaFieldDTO(BaseModel):
    model_config = {"populate_by_name": True}
    id: Optional[str] = Field(default=None, alias="id")
    code: Optional[str] = Field(default=None, alias="code")
    label: str = Field(alias="label")
    relevance_condition: Optional[str] = Field(default=None, alias="relevanceCondition")
    validation_condition: Optional[str] = Field(default=None, alias="validationCondition")
    data_entry_visible: bool = Field(default=False, alias="dataEntryVisible")
    table_visible: bool = Field(default=False, alias="tableVisible")
    required: bool = Field(alias="required")
    key: Optional[bool] = Field(default=False, alias="key")
    type: str = Field(alias="type")
    type_parameters: Optional[FieldTypeParametersUpdateDTO] = Field(default=None, alias="typeParameters")

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type_case(cls, v):
        if isinstance(v, str):
            for member in FieldType:
                if member.value.upper() == v.upper():
                    return member.value
        return v

    @field_validator("type_parameters", mode="after")
    @classmethod
    def normalize_empty(cls, v: Optional[FieldTypeParametersUpdateDTO]):
        if v is None:
            return None
        if all(value is None for value in v.model_dump().values()):
            return None
        return v

    @field_validator("validation_condition", "relevance_condition", mode="before")
    @classmethod
    def normalize_empty_strings(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v

    def __hash__(self):
        return hash((self.id, self.code, self.label))


class SchemaUpdateDTO(BaseModel):
    form_id: str = Field(alias="id")
    form_label: str = Field(alias="label")
    schema_version: str = Field(alias="schemaVersion")
    database_id: str = Field(alias="databaseId")
    parent_form_id: Optional[str] = Field(default=None, alias="parentFormId")
    elements: List[SchemaFieldDTO] = Field(alias="elements")


class RecordUpdateDTO(BaseModel):
    form_id: str = Field(alias="formId")
    record_id: str = Field(alias="recordId")
    parent_record_id: Optional[str] = Field(default=None, alias="parentRecordId")
    deleted: bool = Field(default=False, alias="deleted")
    fields: Dict[str, Any] = Field(alias="fields")

    model_config = {
        "populate_by_name": True,
    }
