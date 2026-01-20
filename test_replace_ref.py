import asyncio
import os

from dotenv import load_dotenv

from api import ActivityInfoClient
from api.client import BASE_URL
from api.models import FormSchema


async def test():
    load_dotenv()
    client = ActivityInfoClient(BASE_URL, api_token=os.getenv("API_TOKEN"))
    schema: FormSchema = await client.api.get_form_schema("c93gljgmkcry89xd")
    field = next(
        (el for el in schema.elements if
         el.code == "DISAG_AGE_SEX"),
        None
    )
    field.type_parameters.range = [{'formId': 'chl0hbomkminwf02'}]
    for element in schema.elements:
        if element.type == "calculated":
            print(element.type_parameters)
    await client.api.update_form_schema(schema)


asyncio.run(test())
