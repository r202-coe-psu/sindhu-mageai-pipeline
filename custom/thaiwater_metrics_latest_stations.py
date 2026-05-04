from datetime import datetime, timedelta
import datetime
from beanie.odm.operators.find.comparison import NotIn

import asyncio
import nest_asyncio
from dhara import models

if "data_loader" not in globals():
    from mage_ai.data_preparation.decorators import data_loader

nest_asyncio.apply()


async def get_acquisition_stations():
    await models.init_default_beanie_client()

    PROCESS_LIMIT = 300

    minutes_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        minutes=50
    )
    pipeline = [
        {"$match": {"source": "air4thai", "status": "active"}},
        {"$group": {"_id": None, "station_ids": {"$addToSet": {"$toString": "$_id"}}}},
    ]

    responses = await models.Station.aggregate(pipeline).to_list()

    return responses[0]["station_ids"] if len(responses) > 0 else []


@custom
def load_data_from_api(*args, **kwargs):
    stations = asyncio.run(get_acquisition_stations())
    print("Total station(s):", len(stations))
    return {"stations": stations}
