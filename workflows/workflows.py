from datetime import timedelta
from typing import Dict, Callable, Coroutine, Any

from pydantic import BaseModel, Field
from temporalio import workflow

from actions.calculation_formulas import get_operation_calculation_changesets
from actions.metric_configuration import get_operation_metric_configuration_changesets
from actions.models import Changeset

SCRIPTS: Dict[str, Callable[[str], Coroutine[Any, Any, Changeset]]] = {
    "operation_calculation_formulas": get_operation_calculation_changesets,
    "operation_metric_configuration": get_operation_metric_configuration_changesets
}

TASK_QUEUE = "air-queue"


# {"name": "calculation_formulas", "database_id": "cay0dkxmkcry89w2"}
class RunScriptWorkflowParameters(BaseModel):
    name: str = Field()
    database_id: str = Field()


@workflow.defn
class RunScriptWorkflow:
    @workflow.run
    async def run(self, params: RunScriptWorkflowParameters) -> dict:
        changeset = await workflow.execute_activity(SCRIPTS[params.name], params.database_id,
                                               start_to_close_timeout=timedelta(seconds=20))
        return changeset.to_dict()
