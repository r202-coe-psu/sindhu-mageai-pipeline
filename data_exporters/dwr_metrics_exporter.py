import asyncio
import nest_asyncio
import datetime
from bson import ObjectId, DBRef
from sindhu import models

nest_asyncio.apply()

if "data_exporter" not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

source = "dwr"


async def insert_data(metrics_stations):
    print("### Initialize Beanie")
    await models.init_default_beanie_client()

    print("### Start insert data")
    metrics_to_save = []
    exist_counter = 0

    for code, metrics_station in metrics_stations.items():
        station = (
            await models.Station.find(
                models.Station.status == "active", models.Station.code == code
            )
            .sort(-models.Station.updated_date)
            .first_or_none()
        )
        if not station:
            print(f"[!] Station {code} not found")
            continue

        for data in metrics_station:
            code = data.pop("code")
            source = data.pop("source")
            name_th = data.pop("name_th")
            waterlevel_datetime = data.pop("waterlevel_datetime")

            # Process
            timestamp = datetime.datetime.fromisoformat(waterlevel_datetime)

            for parameter, value in data.items():
                if not value:
                    continue

                exists_metric = await models.Metric.find_one(
                    models.Metric.timestamp == timestamp,
                    models.Metric.metadata["station"]["$id"] == station.id,
                    models.Metric.metadata["parameter"] == parameter,
                ).exists()

                if exists_metric:
                    exist_counter += 1
                    print(
                        f"[/] Skip parameter {parameter} exists for station ({code})-{station.name_th} at {timestamp}"
                    )
                    continue

                metadata = dict(
                    source=source,
                    station=DBRef("stations", station.id),
                    station_code=code,
                    created_date=datetime.datetime.now(datetime.timezone.utc),
                    parameter=parameter,
                )

                metric = models.Metric(
                    timestamp=timestamp, value=value, metadata=metadata
                )

                metrics_to_save.append(metric)

    if metrics_to_save:
        await models.Metric.insert_many(metrics_to_save)

    total = exist_counter + len(metrics_to_save)
    print(f"\nTotal {total} documents")
    print(f"Found exists {exist_counter} documents")
    print(f"Inserted {len(metrics_to_save)} documents")
    if total > 0:
        print(f"Inserted rate {len(metrics_to_save)/total*100:.2f}%")
    print("\n### Success insert data")


@data_exporter
def export_data_to_mongodb(metrics_stations, **kwargs) -> None:
    asyncio.run(insert_data(metrics_stations))
    return