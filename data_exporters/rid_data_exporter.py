import datetime
from typing import List
import asyncio
import bson

from sindhu import models
from sindhu.schemas import bases

if "data_exporter" not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


async def insert_data(stations):
    print("### Initialize Beanie")
    await models.init_default_beanie_client()

    stations_to_save = []
    print("### Start insert data")
    for code, station in stations.items():
        for data in station:
            name = data.pop("name_en")
            name_th = data.pop("name_th")
            station_code = data.pop("code")
            source = data.pop("source")
            url = data.pop("url")
            station_type = data.pop("station_type")
            location = data.pop("location")
            basin = data.pop("basin")
            longitude = data.pop("longitude")
            latitude = data.pop("latitude")
            created_date = datetime.datetime.now(datetime.timezone.utc)
            updated_date = datetime.datetime.now(datetime.timezone.utc)

            exists_name_th_station = (
                await models.Station.find(
                    models.Station.name_th == name_th,
                )
                .sort(-models.Station.updated_date)
                .first_or_none()
            )
            if exists_name_th_station:
                print(f"[>] Updating station ({station_code}) {name_th}")
                exists_name_th_station.name = name
                exists_name_th_station.name_th = name_th
                exists_name_th_station.code = station_code
                exists_name_th_station.source = source
                exists_name_th_station.url = url
                exists_name_th_station.station_type = station_type
                exists_name_th_station.location = location
                exists_name_th_station.basin = basin
                exists_name_th_station.coordinates = bases.GeoObject(
                    coordinates=[longitude, latitude]
                )
                exists_name_th_station.status = "active"  # always active after use
                exists_name_th_station.updated_date = datetime.datetime.now(
                    datetime.timezone.utc
                )
                await exists_name_th_station.save()
                continue

            # Otherwise It's new station
            print(f"[+] New Station ({station_code}) {name_th}")
            new_station = models.Station(
                name=name,
                name_th=name_th,
                code=station_code,
                source=source,
                url=url,
                station_type=station_type,
                location=location,
                basin=basin,
                coordinates=bases.GeoObject(coordinates=[longitude, latitude]),
                created_date=created_date,
                updated_date=updated_date,
                status="active",
            )

            stations_to_save.append(new_station)

    if stations_to_save:
        await models.Station.insert_many(stations_to_save)

    print("### Success insert data:", len(stations_to_save))


@data_exporter
def export_data_to_mongodb(stations, **kwargs) -> None:
    asyncio.run(insert_data(stations))
    print("### Done Process")
