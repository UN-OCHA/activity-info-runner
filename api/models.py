from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict

from scripts.dtos import SchemaFieldDTO


class OwnerRef(BaseModel):
    id: str
    name: str
    email: str


class Operation(BaseModel):
    operation: str
    filter: Optional[str] = None
    securityCategories: List[str] = []


class Grant(BaseModel):
    resourceId: str
    optional: bool
    operations: List[Operation]
    conditions: List[Any] = []


class Role(BaseModel):
    id: str
    label: str
    permissions: List[Operation] = []
    parameters: List[Dict[str, Any]] = []
    filters: List[Any] = []
    grants: List[Grant] = []
    version: int
    grantBased: bool


class Resource(BaseModel):
    id: str
    parentId: Optional[str]
    label: str
    type: str
    visibility: str


class DatabaseRole(BaseModel):
    id: str
    parameters: Dict[str, Any] = {}
    resources: List[Any] = []


class DatabaseTree(BaseModel):
    databaseId: str
    userId: str
    version: str
    label: str
    description: str
    ownerRef: OwnerRef
    billingAccountId: int
    language: str
    originalLanguage: str
    languages: List[str] = []
    role: DatabaseRole
    suspended: bool
    billingPlan: str
    storage: str
    publishedTemplate: bool
    resources: List[Resource]
    grants: List[Grant]
    locks: List[Any] = []
    roles: List[Role]
    securityCategories: List[Dict[str, str]]


class FormFields(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias='@id')
    last_edit_time: float = Field(alias='@lastEditTime')


class OperationMetricConfigurationField(FormFields):
    sort_order: str = Field(alias='SORTORDER')
    data_form_prefix: str = Field(alias='DFORM.SYSPREFIX')
    data_form_id: str = Field(alias='DFORM.@id')
    order: int = Field(alias='REFORDER')
    shown_as: str = Field(alias='DISPLAY.@id')
    global_attachment_metrix: str = Field(alias='GLOBMETRIC.@id')
    reference_code_manual: Optional[str] = Field(alias='REFCODE_MAN')
    name: str = Field(alias='NAME')
    reference_code: str = Field(alias='REFCODE')
    field_name: str = Field(alias='CCODE')
    reference_label: str = Field(alias='REFLABEL')
    errors: Optional[str] = Field(alias='ERRS')


class OperationDataFormsField(FormFields):
    system_prefix: str = Field(alias='SYSPREFIX')
    entity_form_prefix: str = Field(alias='EFORM.SYSPREFIX')
    entity_form_id: str = Field(alias='EFORM.@id')
    # user_level: str = Field(alias='USERLEVEL')
    # process: str = Field(alias='PROCESS')
    # data_level: str = Field(alias='DATALEVEL')
    composite_code: str = Field(alias='CCODE')


class Database(BaseModel):
    databaseId: str
    label: str
    description: str


class TypeParameterLookupConfig(BaseModel):
    id: str
    formula: Optional[str] = None
    lookupLabel: Optional[str] = None


class TypeParameters(BaseModel):
    range: Optional[List[Dict[str, str]]] = None
    lookupConfigs: Optional[List[TypeParameterLookupConfig]] = None
    formula: Optional[str] = None
    units: Optional[str] = None
    aggregation: Optional[str] = None


class FormSchema(BaseModel):
    id: str
    schemaVersion: int
    databaseId: str
    label: str
    elements: List[SchemaFieldDTO]
