from enum import StrEnum
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


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
    units: Optional[str] = Field(alias="units")
    input_mask: Optional[str] = Field(alias="inputMask")
    cardinality: Optional[FieldTypeParametersCardinality] = Field(alias="cardinality")
    range: Optional[str] = Field(alias="range")
    form_id: Optional[str] = Field(alias="formId")
    items: Optional[List[FieldTypeParametersItemsUpdateDTO]] = Field(alias="items")
    formula: Optional[str] = Field(alias="formula")
    prefix_formula: Optional[str] = Field(alias="prefixFormula")


class SchemaFieldUpdateDTO(BaseModel):
    id: str = Field(alias="id")
    code: str = Field(alias="code")
    label: str = Field(alias="label")
    relevance_condition: Optional[str] = Field(alias="relevanceCondition")
    validation_condition: Optional[str] = Field(alias="validationCondition")
    data_entry_visible: bool = Field(alias="dataEntryVisible")
    table_visible: bool = Field(alias="tableVisible")
    required: bool = Field(alias="required")
    key: bool = Field(alias="key")
    type: FieldType = Field(alias="type")
    type_parameters: Optional[FieldTypeParametersUpdateDTO] = Field(alias="typeParameters")


class SchemaUpdateDTO(BaseModel):
    form_id: str = Field(alias="id")
    form_label: str = Field(alias="label")
    schema_version: str = Field(alias="schemaVersion")
    database_id: str = Field(alias="databaseId")
    parent_form_id: Optional[str] = Field(default=None, alias="parentFormId")
    elements: List[SchemaFieldUpdateDTO] = Field(alias="elements")


class RecordUpdateDTO(BaseModel):
    form_id: str = Field(alias="formId")
    record_id: str = Field(alias="recordId")
    parent_record_id: Optional[str] = Field(default=None, alias="parentRecordId")
    deleted: bool = Field(default=False, alias="deleted")
    fields: Dict[str, Any] = Field(alias="fields")

    model_config = {
        "populate_by_name": True,
    }
