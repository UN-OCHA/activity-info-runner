from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


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


class OperationCalculationFormulasField(FormFields):
    ref_order: int = Field(alias='REFORDER')
    description: str = Field(alias='DESC')
    apply: str = Field(alias='APPLY')

    sys_prefix: str = Field(alias='SYSPREFIX')
    sys_field: str = Field(alias='SYSFIELD')

    filter: Optional[str] = Field(alias='FILTER')
    formula: Optional[str] = Field(alias='FORMULA')
    errors: Optional[str] = Field(alias='ERRS')


# class OperationDataFormsField(FormFields):
#     sys_prefix: str = Field(alias='SYSPREFIX')
#     entity_form: str = Field(alias='EFORM.@id')
#     user_level: str = Field(alias='USERLEVEL.@id')
#     process: str = Field(alias='PROCESS.@id')
#     data_level: str = Field(alias='DATALEVEL.@id')
#     composite_code: str = Field(alias='CCODE')


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


class FormElement(BaseModel):
    id: str
    code: Optional[str] = None
    label: str
    description: Optional[str] = None
    relevanceCondition: Optional[str] = ""
    validationCondition: Optional[str] = ""
    required: Optional[bool] = False
    type: str
    key: Optional[bool] = False
    dataEntryVisible: Optional[bool] = True
    tableVisible: Optional[bool] = True
    typeParameters: Optional[TypeParameters] = None


class FormSchema(BaseModel):
    id: str
    schemaVersion: int
    databaseId: str
    label: str
    elements: List[FormElement]
