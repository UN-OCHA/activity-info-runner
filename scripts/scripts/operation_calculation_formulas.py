from enum import StrEnum, auto
from typing import List, Optional

from pydantic import Field
from temporalio import workflow

from api import ActivityInfoClient
from api.models import FormFields
from scripts.models import ScriptBoundary, SchemaSnapshot
from scripts.script import AIRScript, AIRScriptExecutionResult


# ------ Models ------

class OperationCalculationFormulasField(FormFields):
    ref_order: int = Field(alias='REFORDER')
    description: str = Field(alias='DESC')
    apply: str = Field(alias='APPLY')
    sys_prefix: str = Field(alias='SYSPREFIX')
    sys_field: str = Field(alias='SYSFIELD')
    filter: Optional[str] = Field(alias='FILTER')
    formula: Optional[str] = Field(alias='FORMULA')
    errors: Optional[str] = Field(alias='ERRS')


class OperationCalculationApplyType(StrEnum):
    INTERNAL = "Internal"
    EXTERNAL = "External"
    UNKNOWN = auto()


# ------ Logic ------

@workflow.defn
class OperationCalculationFormulas(AIRScript):
    async def get_script_boundary(self, database_ids: List[str]) -> ScriptBoundary:
        return (
            ScriptBoundary.builder()
            .select_databases(database_ids)
            .form(label_regex="^2\.1")
            .with_all_records()
            .with_fields(code_regex="^AMOUNT_.*")
            .form(label_regex="^0\.1\.6")
            .with_all_records()
            .with_fields(code_regex="ERRS")
            .build()
        )

    async def get_desired_schema(self, materialized_boundary: SchemaSnapshot,
                                 client: ActivityInfoClient) -> SchemaSnapshot:
        for database in materialized_boundary.databases:
            config_form = database.find_form(label_pattern="^0\.1\.6", is_regex=True)
            if not config_form: continue

            config_records = [OperationCalculationFormulasField.model_validate(record) for record in
                              config_form.records]
            config_records_per_form_prefix = set([config.sys_prefix for config in config_records])

            for form_prefix in config_records_per_form_prefix:
                form_configs = [config for config in config_records if config.sys_prefix == form_prefix]
                target_form = database.find_form(label_pattern=f"^{form_prefix}(_|$)", is_regex=True)

                if not target_form: continue

                for form_field in target_form.select_fields(code_pattern=".*(ICALC|ECALC)$", is_regex=True):
                    if form_field.code.endswith("ICALC"):
                        field_configs = [config for config in form_configs if
                                         form_field.code.startswith(config.sys_field) and
                                         config.apply == OperationCalculationApplyType.INTERNAL]

                        form_field.type_parameters.formula = "VALUE(\"#\")"
                        for config in field_configs:
                            form_field.type_parameters.formula = f"IF(${config.filter}, ${config.formula}, {form_field.type_parameters.formula})"

                    elif form_field.code.endswith("ECALC"):
                        field_config = next((config for config in form_configs if
                                             form_field.code.startswith(config.sys_field) and
                                             config.apply == OperationCalculationApplyType.EXTERNAL), None)

                        if field_config is None:
                            for record in target_form.records:
                                record[form_field.label] = None
                        else:
                            for record in target_form.records:
                                val = await self.evaluate_expression(field_config.formula, record, client)
                                record[form_field.label] = val
                                
        return materialized_boundary

    @workflow.run
    async def execute(self, database_ids: List[str]) -> AIRScriptExecutionResult:
        return await super().execute(database_ids)
