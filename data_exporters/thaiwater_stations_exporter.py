import datetime
from typing import List
import asyncio
import bson

from sindhu import models
from sindhu.schemas import bases

if "data_exporter" not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


async def insert_data(air4thai_stations):
    print("### Initialize Beanie")
    await models.init_default_beanie_client()

    stations_to_save = []
    print("### Start insert data")
    


    print("### Success insert data:", len(stations_to_save))


@data_exporter
def export_data_to_mongodb(stations, **kwargs) -> None:
    asyncio.run(insert_data(stations))
    print("### Done Process")
