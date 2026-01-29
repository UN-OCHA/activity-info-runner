from typing import Any, List

from pydantic import ValidationError

from api.cache import auto_cache
from api.client import ActivityInfoHTTPClient, APIError
from api.models import DatabaseTree, FormSchema, OperationMetricConfigurationField, \
    OperationDataFormsField, Database
from scripts.dtos import RecordUpdateDTO

RawFormPayload = dict[str, Any]


class ActivityInfoEndpoints:
    def __init__(self, http: ActivityInfoHTTPClient):
        self._http = http

    @auto_cache(ttl=36000, model=DatabaseTree)
    async def get_database_tree(self, database_id: str) -> DatabaseTree:
        raw = await self._http.request("GET", f"databases/{database_id}")
        try:
            return DatabaseTree.model_validate(raw)
        except ValidationError as e:
            raise APIError(
                "Response does not match DatabaseTree schema"
            ) from e

    @auto_cache(ttl=36000)
    async def get_form(self, form_id: str) -> List[RawFormPayload]:
        return await self._http.request("GET", f"form/{form_id}/query")

    # @cached(ttl=20, serializer=PickleSerializer())
    @auto_cache(ttl=36000, model=FormSchema)
    async def get_form_schema(self, form_id: str) -> FormSchema:
        raw = await self._http.request("GET", f"form/{form_id}/schema")
        try:
            return FormSchema.model_validate(raw)  # parse dict into Pydantic model
        except ValidationError as e:
            raise APIError("Response does not match FormSchema") from e

    async def get_operation_metric_configuration_fields(
            self,
            form_id: str,
    ) -> List[OperationMetricConfigurationField]:
        raw = await self.get_form(form_id, _bypass_cache=True)
        try:
            return [
                OperationMetricConfigurationField.model_validate(item)
                if isinstance(item, dict) else item
                for item in raw
            ]
        except ValidationError as e:
            raise APIError(
                "Form does not match OperationMetricConfigurationField schema"
            ) from e

    @auto_cache(ttl=36000, model=OperationDataFormsField)
    async def get_operation_data_forms_fields(
            self,
            form_id: str,
    ) -> List[OperationDataFormsField]:
        raw = await self.get_form(form_id, _bypass_cache=True)
        try:
            return [
                OperationDataFormsField.model_validate(item)
                if isinstance(item, dict) else item
                for item in raw
            ]
        except ValidationError as e:
            raise APIError(
                "Form does not match OperationDataFormsField schema"
            ) from e

    @auto_cache(ttl=36000, model=Database)
    async def get_user_databases(self) -> List[Database]:
        raw = await self._http.request("GET", "databases")
        try:
            return [
                Database.model_validate(item)
                if isinstance(item, dict) else item
                for item in raw
            ]
        except ValidationError as e:
            raise APIError(
                "Item does not match Database schema"
            ) from e

    async def update_form_records(self, records: List[RecordUpdateDTO]) -> None:
        payload = {
            "changes": [
                r.model_dump(
                    mode="json",
                    exclude_none=True,
                    exclude_unset=True,
                    by_alias=True,
                )
                for r in records
            ]
        }
        await self._http.request(
            "POST",
            "update",
            json=payload,
        )

    async def update_form_schema(self, schema: FormSchema):
        await self._http.request(
            "POST",
            f"form/{schema.id}/schema",
            json=schema.model_dump(
                mode="json",
                exclude_none=True,
                exclude_unset=True,
                by_alias=True,
            )
        )
