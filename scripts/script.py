from abc import ABC, abstractmethod
import copy
import os
from datetime import timedelta
from typing import List, Union

from pydantic import BaseModel
from temporalio import workflow, activity
from temporalio.common import RetryPolicy

from api import ActivityInfoClient
from api.client import BASE_URL
from blob_store import BlobRef, load_blob, save_blob
from scripts.boundaries import materialize_boundary
from scripts.changeset import generate_changeset
from scripts.models import Changeset, ScriptBoundary, SchemaSnapshot
from utils import CaptureLogs


class AIRScriptExecutionResult(BaseModel):
    changeset: Changeset
    materialized_boundary: Union[SchemaSnapshot, BlobRef]
    warnings: List[str]
    logs: List[str]


class AIRScript(ABC):
    @abstractmethod
    async def get_script_boundary(self, database_ids: List[str]) -> ScriptBoundary:
        pass

    @abstractmethod
    async def get_desired_schema(self, schema: SchemaSnapshot, client: ActivityInfoClient) -> SchemaSnapshot:
        pass

    async def evaluate_expression(self, expression: str, record: dict, client: ActivityInfoClient):
        """Helper to evaluate an ActivityInfo expression against a record."""
        from parser import ActivityInfoExpression, RecordResolver
        from utils import build_nested_dict

        if not expression:
            return None
        
        # Clean record and build nested structure
        curr_fields = {k: v for k, v in record.items() if k not in ('_id', '_lastEditTime') and v is not None}
        nested_fields = build_nested_dict(curr_fields)
        
        resolver = RecordResolver(client, nested_fields)
        parsed_expr = ActivityInfoExpression.parse(expression)
        return await parsed_expr.evaluate(resolver)

    @activity.defn
    async def generate_script_boundary(self, database_ids: List[str]) -> ScriptBoundary:
        return await self.get_script_boundary(database_ids)

    @activity.defn
    async def generate_desired_schema(self, materialized_boundary: Union[SchemaSnapshot, BlobRef]) -> Union[
        SchemaSnapshot, BlobRef]:
        boundary = await load_blob(materialized_boundary)
        schema_copy = copy.deepcopy(boundary)
        async with ActivityInfoClient(BASE_URL, os.getenv("API_TOKEN")) as client:
            desired = await self.get_desired_schema(schema_copy, client)
        return await save_blob(desired)

    @workflow.run
    async def execute(self, database_ids: List[str]) -> AIRScriptExecutionResult:
        with CaptureLogs() as log_handler:
            retry_policy = RetryPolicy(maximum_attempts=2)
            timeout = timedelta(minutes=5)
            boundary = await workflow.execute_activity(self.generate_script_boundary, arg=database_ids,
                                                       retry_policy=retry_policy, start_to_close_timeout=timeout)
            materialized_boundary, warnings = await workflow.execute_activity(materialize_boundary, arg=boundary,
                                                                              retry_policy=retry_policy,
                                                                              start_to_close_timeout=timeout)
            desired_schema = await workflow.execute_activity(self.generate_desired_schema, arg=materialized_boundary,
                                                             retry_policy=retry_policy, start_to_close_timeout=timeout)
            changeset, w = await workflow.execute_activity(generate_changeset,
                                                           args=[materialized_boundary, desired_schema],
                                                           retry_policy=retry_policy, start_to_close_timeout=timeout)
            warnings.extend(w)
            return AIRScriptExecutionResult(changeset=changeset, materialized_boundary=materialized_boundary,
                                            warnings=warnings, logs=log_handler.records)
