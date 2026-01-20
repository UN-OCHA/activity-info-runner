import subprocess
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from functools import cache

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from temporalio.api.enums.v1.event_type_pb2 import EVENT_TYPE_WORKFLOW_TASK_SCHEDULED, \
    EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED, EVENT_TYPE_ACTIVITY_TASK_SCHEDULED, EVENT_TYPE_ACTIVITY_TASK_STARTED, \
    EVENT_TYPE_ACTIVITY_TASK_COMPLETED, EVENT_TYPE_ACTIVITY_TASK_FAILED, EVENT_TYPE_ACTIVITY_TASK_TIMED_OUT, \
    EVENT_TYPE_WORKFLOW_EXECUTION_STARTED
from temporalio.client import Client
from temporalio.converter import DataConverter

from workflows.workflows import SCRIPTS, TASK_QUEUE, RunScriptWorkflowParameters


@asynccontextmanager
async def lifespan(instance: FastAPI):
    """ Run at startup
        Initialize the Client and add it to app.state
    """
    client = await Client.connect("localhost:7233")
    instance.state.client = client
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_git_revision_short_hash() -> str:
    return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()


def safe_timestamp_to_datetime(ts) -> datetime:
    """Converts a Protobuf Timestamp or similar object to a naive datetime."""
    if hasattr(ts, "ToDatetime"):
        return ts.ToDatetime().replace(tzinfo=None)
    if hasattr(ts, "replace"):  # Already datetime-like
        return ts.replace(tzinfo=None)
    # Fallback/Error if unknown type
    return ts


@app.get("/")
@cache
def read_root():
    return {"app": "Activity Info Runner", "version": get_git_revision_short_hash()}


@app.get("/scripts")
@cache
def read_scripts():
    return list(SCRIPTS.keys())


@app.get("/workflows")
async def get_workflows(request: Request):
    client: Client = request.app.state.client
    workflows = []
    async for wf in client.list_workflows():
        handle = client.get_workflow_handle(wf.id, run_id=wf.run_id)
        init_event = await anext(handle.fetch_history_events(page_size=1))
        params = \
            (await DataConverter.default.decode(init_event.workflow_execution_started_event_attributes.input.payloads))[
                0]
        async for event in handle.fetch_history_events(page_size=100):
            last_event = event
        pending = last_event.event_type == EVENT_TYPE_WORKFLOW_TASK_SCHEDULED
        workflows.append({
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "type": wf.workflow_type,
            "status": "PENDING" if pending else wf.status.name if wf.status else "UNKNOWN",
            "start_time": wf.start_time.isoformat() if wf.start_time else None,
            "close_time": wf.close_time.isoformat() if wf.close_time else None,
            "params": params,
        })
    return workflows


@app.get("/workflows/{workflow_id}/{run_id}")
async def get_workflow(request: Request):
    client: Client = request.app.state.client
    handle = client.get_workflow_handle(request.path_params["workflow_id"], run_id=request.path_params["run_id"])
    wf = await handle.describe()

    # Timing collection
    timings = []
    pending_activities = {}  # Map scheduled_event_id -> {name, start_time, ...}
    workflow_start_time = None

    # Process history events
    last_event = None
    async for event in handle.fetch_history_events(page_size=100):
        last_event = event

        # Helper to get naive datetime
        event_dt = safe_timestamp_to_datetime(event.event_time)

        if event.event_type == EVENT_TYPE_WORKFLOW_EXECUTION_STARTED:
            workflow_start_time = event_dt

        elif event.event_type == EVENT_TYPE_ACTIVITY_TASK_SCHEDULED:
            attr = event.activity_task_scheduled_event_attributes
            pending_activities[event.event_id] = {
                "name": attr.activity_type.name,
                "type": "activity",
                "scheduled_time": event_dt
            }

        elif event.event_type == EVENT_TYPE_ACTIVITY_TASK_STARTED:
            attr = event.activity_task_started_event_attributes
            if attr.scheduled_event_id in pending_activities:
                pending_activities[attr.scheduled_event_id]["start_time"] = event_dt

        elif event.event_type in [EVENT_TYPE_ACTIVITY_TASK_COMPLETED, EVENT_TYPE_ACTIVITY_TASK_FAILED,
                                  EVENT_TYPE_ACTIVITY_TASK_TIMED_OUT]:
            # These events have scheduled_event_id reference
            if event.event_type == EVENT_TYPE_ACTIVITY_TASK_COMPLETED:
                scheduled_id = event.activity_task_completed_event_attributes.scheduled_event_id
            elif event.event_type == EVENT_TYPE_ACTIVITY_TASK_FAILED:
                scheduled_id = event.activity_task_failed_event_attributes.scheduled_event_id
            else:
                scheduled_id = event.activity_task_timed_out_event_attributes.scheduled_event_id

            if scheduled_id in pending_activities:
                activity_data = pending_activities.pop(scheduled_id)
                start_time = activity_data.get("start_time")
                end_time = event_dt

                # If start_time wasn't captured (rare), use scheduled_time or None
                if start_time:
                    duration = (end_time - start_time).total_seconds()
                    activity_data["start_time"] = start_time.isoformat()
                    activity_data["end_time"] = end_time.isoformat()
                    activity_data["duration_seconds"] = duration
                    del activity_data["scheduled_time"]  # Clean up
                    timings.append(activity_data)

    # Workflow Timing
    if wf.start_time and wf.close_time:
        st = wf.start_time.replace(tzinfo=None)
        et = wf.close_time.replace(tzinfo=None)
        timings.insert(0, {
            "name": wf.workflow_type,
            "type": "workflow",
            "start_time": st.isoformat(),
            "end_time": et.isoformat(),
            "duration_seconds": (et - st).total_seconds()
        })
    elif wf.start_time:
        timings.insert(0, {
            "name": wf.workflow_type,
            "type": "workflow",
            "start_time": wf.start_time.replace(tzinfo=None).isoformat(),
            "end_time": None,
            "duration_seconds": None
        })

    init_event = await anext(handle.fetch_history_events(page_size=1))
    params = \
    (await DataConverter.default.decode(init_event.workflow_execution_started_event_attributes.input.payloads))[0]

    pending = last_event.event_type == EVENT_TYPE_WORKFLOW_TASK_SCHEDULED
    res = None
    if last_event.event_type == EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED:
        res = (await DataConverter.default.decode(
            last_event.workflow_execution_completed_event_attributes.result.payloads))[
            0]

    return {
        "workflow_id": handle.id,
        "run_id": handle.run_id,
        "type": wf.workflow_type,
        "status": "PENDING" if pending else wf.status.name if wf.status else "UNKNOWN",
        "start_time": wf.start_time.isoformat() if wf.start_time else None,
        "close_time": wf.close_time.isoformat() if wf.close_time else None,
        "params": params,
        "results": res,
        "timings": timings
    }


@app.post("/workflows/{script_id}")
async def start_workflow(request: Request):
    client: Client = request.app.state.client
    params = RunScriptWorkflowParameters(
        database_id=request.query_params["database_id"],
        name=request.path_params["script_id"],
    ).model_dump()

    handle = await client.start_workflow(
        "RunScriptWorkflow",
        id=str(uuid.uuid4()),
        arg=params,
        task_queue=TASK_QUEUE,
    )

    return {
        "workflow_id": handle.id,
        "run_id": handle.run_id,
        "task_queue": TASK_QUEUE,
    }
