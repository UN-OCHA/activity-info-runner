import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv

from actions import get_operation_calculation_changesets
from api import ActivityInfoClient
from api.client import BASE_URL


async def main(dry_run: bool, database_id: str):
    load_dotenv()
    api_token = os.getenv("API_TOKEN")
    if not api_token:
        raise ValueError("API_TOKEN environment variable is not set")

    async with ActivityInfoClient(BASE_URL, api_token=os.getenv("API_TOKEN")) as client:
        form_changeset, record_changeset, errors_report = await get_operation_calculation_changesets(client, database_id)
        form_changeset.pretty_print_table()
        record_changeset.pretty_print_table()
        errors_report.pretty_print_table()

        if not dry_run:
            error_dtos = [e.as_form_update_dto() for e in errors_report.entries]
            await client.api.update_form_records(error_dtos)
            logging.info("Updated operation calculation error records in Activity Info.")


if __name__ == '__main__':
    # Usage: python main.py [--debug] [--dry-run] <database_id>
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
    parser.add_argument(
        "database_id",
        type=str,
        help="The Activity Info database ID",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.ERROR
    logging.getLogger("aiocache").setLevel(logging.WARNING)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logging.getLogger("aiocache").setLevel(logging.WARNING)

    # Run the main async function with loaded arguments
    asyncio.run(main(dry_run=args.dry_run, database_id=args.database_id))