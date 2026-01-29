import asyncio
import logging
import os

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

from scripts.scripts.all import get_scripts, get_activities

TASK_QUEUE = "air-queue"


async def main():
    load_dotenv()
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    if not os.getenv("API_TOKEN"):
        print("WARNING: API_TOKEN is not set. Worker may fail to authenticate with ActivityInfo.")

    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=await get_scripts(),
        activities=await get_activities(),
    )
    print("Worker started.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
