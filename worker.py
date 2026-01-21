import asyncio
import os

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

from workflows.workflows import RunScriptWorkflow, SCRIPTS, TASK_QUEUE


async def main():
    load_dotenv()
    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[RunScriptWorkflow],
        activities=list(SCRIPTS.values()),
    )
    print("Worker started.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
