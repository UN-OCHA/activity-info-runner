import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv

from actions import get_operation_calculation_changesets
from api import ActivityInfoClient
from api.client import BASE_URL


async def main(dry_run: bool):
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("aiocache").setLevel(logging.WARNING)
    load_dotenv()
    api_token = os.getenv("API_TOKEN")
    if not api_token:
        raise ValueError("API_TOKEN environment variable is not set")
    async with ActivityInfoClient(BASE_URL, api_token=os.getenv("API_TOKEN")) as client:
        form_changeset, record_changeset = await get_operation_calculation_changesets(client=client, database_id="cay0dkxmkcry89w2",form_id="c9hx7ckmkcry89xr")
        form_changeset.pretty_print_table()
        record_changeset.pretty_print_table()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Activity Info Runner")
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making changes"
    )
    args = parser.parse_args()
    log_level = logging.DEBUG if args.debug else logging.ERROR
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logging.getLogger("aiocache").setLevel(logging.WARNING)
    asyncio.run(main(dry_run=args.dry_run))