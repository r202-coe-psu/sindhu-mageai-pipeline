import asyncio
import nest_asyncio
import datetime
from bson import DBRef
from sindhu import models

nest_asyncio.apply()

if "data_exporter" not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

SOURCE = "dwr"

THRESHOLD_KEYS = {
    "lbMsl", "rbMsl", "bbMsl", "zflowMsl",
    "wlFw", "wlFc", "wlDw", "wlDc",
    "rfFw", "rfFc",
    "qfw", "qfc", "qdw", "qdc",
}


async def insert_data(metrics_stations):
    print("### Initialize Beanie")
    await models.init_default_beanie_client()

    print("### Start insert data")
    metrics_to_save = []
    exist_counter = 0

    for code, metrics_station in metrics_stations.items():
        station = (
            await models.Station.find(
                models.Station.status == "active",
                models.Station.code == code,
                models.Station.source == SOURCE,
            )
            .sort(-models.Station.updated_date)
            .first_or_none()
        )

        if not station:
            print(f"[!] Station {code} not found")
            continue

        print(f"[>] Processing metrics for station: {code} - {metrics_station[0]['name_th']}")

        for data in metrics_station:
            station_code        = data.pop("code")
            name_th             = data.pop("name_th")
            data_source         = data.pop("source")
            waterlevel_datetime = data.pop("waterlevel_datetime")

            # pop threshold fields — ไม่เก็บเป็น metric
            for key in list(THRESHOLD_KEYS):
                data.pop(key, None)

            timestamp = datetime.datetime.fromisoformat(waterlevel_datetime)

            for parameter, value in data.items():
                if value is None:
                    continue

                exists_metric = await models.Metric.find_one(
                    models.Metric.timestamp == timestamp,
                    models.Metric.metadata["station"]["$id"] == station.id,
                    models.Metric.metadata["parameter"] == parameter,
                ).exists()

                if exists_metric:
                    exist_counter += 1
                    continue

                metadata = dict(
                    source=SOURCE,
                    station=DBRef("stations", station.id),
                    station_code=station_code,
                    created_date=datetime.datetime.now(datetime.timezone.utc),
                    parameter=parameter,
                )

                metrics_to_save.append(
                    models.Metric(timestamp=timestamp, value=value, metadata=metadata)
                )

    if metrics_to_save:
        await models.Metric.insert_many(metrics_to_save)

    total_docs = exist_counter + len(metrics_to_save)
    print(f"\nTotal processed documents: {total_docs}")
    print(f"Found exists: {exist_counter} documents")
    print(f"Inserted new: {len(metrics_to_save)} documents")
    if total_docs > 0:
        print(f"Inserted rate: {len(metrics_to_save)/total_docs*100:.2f}%")
    print("\n### Success insert data")


@data_exporter
def export_data_to_mongodb(metrics_stations, **kwargs) -> None:
    asyncio.run(insert_data(metrics_stations))
    print("### Done Process")