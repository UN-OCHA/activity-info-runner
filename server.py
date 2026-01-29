import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from functools import cache

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from google.protobuf.json_format import MessageToDict
from starlette.middleware.cors import CORSMiddleware
from temporalio.api.enums.v1.event_type_pb2 import EVENT_TYPE_WORKFLOW_TASK_SCHEDULED, \
    EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED, EVENT_TYPE_ACTIVITY_TASK_SCHEDULED, EVENT_TYPE_ACTIVITY_TASK_STARTED, \
    EVENT_TYPE_ACTIVITY_TASK_COMPLETED, EVENT_TYPE_ACTIVITY_TASK_FAILED, EVENT_TYPE_ACTIVITY_TASK_TIMED_OUT
from temporalio.api.enums.v1.task_queue_pb2 import TaskQueueKind, TaskQueueType
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.workflowservice.v1.request_response_pb2 import DescribeTaskQueueRequest
from temporalio.client import Client

from api import ActivityInfoClient
from api.client import BASE_URL
from blob_store import load_blob
from scripts.scripts.all import get_scripts
from worker import TASK_QUEUE


@asynccontextmanager
async def lifespan(instance: FastAPI):
    """ Run at startup
        Initialize the Client and add it to app.state
    """
    load_dotenv()
    temporal_client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))
    ai_client = ActivityInfoClient(BASE_URL, api_token=os.getenv("API_TOKEN"))
    instance.state.temporal_client = temporal_client
    instance.state.ai_client = ai_client
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return {"app": "Activity Info Runner", "version": os.getenv("APP_VERSION", "dev")}


@app.get("/system")
async def get_system_info(request: Request):
    client: Client = request.app.state.temporal_client
    result = await client.workflow_service.describe_task_queue(
        DescribeTaskQueueRequest(
            namespace="default",
            include_task_queue_status=True,
            task_queue_type=TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW,
            task_queue=TaskQueue(name=TASK_QUEUE, kind=TaskQueueKind.TASK_QUEUE_KIND_NORMAL),
        )
    )
    res = MessageToDict(result)
    return res


@app.get("/entities")
async def read_entities(request: Request):
    client: ActivityInfoClient = request.app.state.ai_client
    scripts = await get_scripts()
    return {
        "scripts": [c.__name__ for c in scripts],
        "databases": await client.api.get_user_databases()
    }


@app.get("/workflows")
async def get_workflows(request: Request):
    client: Client = request.app.state.temporal_client
    workflows = []
    async for wf in client.list_workflows():
        handle = client.get_workflow_handle(wf.id, run_id=wf.run_id)
        init_event = await anext(handle.fetch_history_events(page_size=1))
        params = \
            (await client.data_converter.decode(init_event.workflow_execution_started_event_attributes.input.payloads))[
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
    client: Client = request.app.state.temporal_client
    handle = client.get_workflow_handle(request.path_params["workflow_id"], run_id=request.path_params["run_id"])
    wf = await handle.describe()

    # Timing collection
    timings = []
    pending_activities = {}  # Map scheduled_event_id -> {name, start_time, ...}

    # Process history events
    last_event = None
    async for event in handle.fetch_history_events(page_size=100):
        last_event = event

        # Helper to get naive datetime
        event_dt = safe_timestamp_to_datetime(event.event_time)

        if event.event_type == EVENT_TYPE_ACTIVITY_TASK_SCHEDULED:
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

    init_event = await anext(handle.fetch_history_events(page_size=1))
    params = \
        (await client.data_converter.decode(init_event.workflow_execution_started_event_attributes.input.payloads))[0]

    pending = last_event.event_type == EVENT_TYPE_WORKFLOW_TASK_SCHEDULED
    res = None
    if last_event.event_type == EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED:
        res = (await client.data_converter.decode(
            last_event.workflow_execution_completed_event_attributes.result.payloads))[
            0]

    response_data = {
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

    if res and "materialized_boundary" in res:
         snapshot = await load_blob(res["materialized_boundary"])
         # Convert to dict
         snapshot_data = snapshot.model_dump()
         for db in snapshot_data.get("databases", []):
             for form in db.get("forms", []):
                 form["records"] = len(form.get("records", []))
         response_data["results"]["materialized_boundary"] = snapshot_data

    return response_data


@app.post("/workflows/{script_id}")
async def start_workflow(request: Request):
    client: Client = request.app.state.temporal_client
    scripts = await get_scripts()
    scripts_by_id = {script.__name__: script for script in scripts}
    script = scripts_by_id[request.path_params["script_id"]]

    handle = await client.start_workflow(
        script.__name__,
        id=str(uuid.uuid4()),
        arg=[request.query_params["database_id"]],
        task_queue=TASK_QUEUE,
    )

    return {
        "workflow_id": handle.id,
        "run_id": handle.run_id,
        "task_queue": TASK_QUEUE,
    }
