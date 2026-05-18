import datetime
import asyncio
import nest_asyncio

from sindhu import models
from sindhu.schemas import bases

nest_asyncio.apply()
if "data_exporter" not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


async def insert_data(stations):
    print("### Initialize Beanie")
    await models.init_default_beanie_client()

    stations_to_save = []
    print("### Start insert data")

    for code, station in stations.items():
        for data in station:
            name         = data.pop("name")
            name_th      = data.pop("name_th")
            station_code = data.pop("code")
            source       = data.pop("source")
            url          = data.pop("url")
            station_type = data.pop("station_type")
            longitude    = data.pop("longitude")
            latitude     = data.pop("latitude")

            dept        = data.pop("dept")
            rtu_grp     = data.pop("rtu_grp")
            gd_id       = data.pop("gd_id")
            main_basin  = data.pop("main_basin")
            sub_basin   = data.pop("sub_basin")
            sub_station = data.pop("sub_station")

            tambon_name_th   = data.pop("tambon_name_th")
            amphoe_name_th   = data.pop("amphoe_name_th")
            province_name_th = data.pop("province_name_th")

            created_date = datetime.datetime.now(datetime.timezone.utc)
            updated_date = datetime.datetime.now(datetime.timezone.utc)

            metadata = dict(
                station_type=station_type,
                tambon_name_th=tambon_name_th,
                amphoe_name_th=amphoe_name_th,
                province_name_th=province_name_th,
                dept=dept,
                rtu_grp=rtu_grp,
                gd_id=gd_id,
                main_basin=main_basin,
                sub_basin=sub_basin,
                sub_station=sub_station,
            )

        exists_station = (
            await models.Station.find(
                models.Station.name_th == name_th,
            )
            .sort(-models.Station.updated_date)
            .first_or_none()
        )

        if exists_station:
            print(f"[>] Updating station ({station_code}) {name_th}")
            exists_station.name        = name
            exists_station.name_th     = name_th
            exists_station.code        = station_code
            exists_station.source      = source
            exists_station.url         = url
            exists_station.metadata    = metadata
            exists_station.coordinates = bases.GeoObject(
                coordinates=[longitude, latitude]
            )
            exists_station.status       = "active"
            exists_station.updated_date = datetime.datetime.now(
                datetime.timezone.utc
            )
            await exists_station.save()
            continue

        print(f"[+] New Station ({station_code}) {name_th}")
        station = models.Station(
            name=name,
            name_th=name_th,
            code=station_code,
            source=source,
            url=url,
            metadata=metadata,
            coordinates=bases.GeoObject(coordinates=[longitude, latitude]),
            created_date=created_date,
            updated_date=updated_date,
            status="active",
        )
        stations_to_save.append(station)

    if stations_to_save:
        await models.Station.insert_many(stations_to_save)

    print("### Success insert data:", len(stations_to_save))


@data_exporter
def export_data_to_mongodb(stations, **kwargs) -> None:
    asyncio.run(insert_data(stations))
    print("### Done Process")