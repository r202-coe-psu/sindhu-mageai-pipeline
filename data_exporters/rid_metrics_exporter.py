import asyncio
import nest_asyncio
import datetime
from bson import ObjectId, DBRef
from sindhu import models

nest_asyncio.apply()

if "data_exporter" not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

source = "rid"


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
            waterlevel_datetime = data.pop("waterlevel_datetime")

            # Extract parameter name and value
            parameter = data.pop("parameter_name")
            value = data.pop("parameter_value")

            # Pop metadata fields
            cross_section = data.pop("cross_section", None)
            zerogate = data.pop("zerogate", None)
            water_level_warning = data.pop("water_level_warning", None)
            water_level_critical = data.pop("water_level_critical", None)
            
            # Pop raw WebSocket fields
            raw_water_level = data.pop("raw_water_level", None)
            raw_water_level_value_list = data.pop("raw_water_level_value_list", None)
            raw_rain_sum_now = data.pop("raw_rain_sum_now", None)
            raw_rain_sum = data.pop("raw_rain_sum", None)

            # Process — waterlevel_datetime
            if isinstance(waterlevel_datetime, str):
                timestamp = datetime.datetime.fromisoformat(waterlevel_datetime)
            else:
                timestamp = waterlevel_datetime

            # Now check if this metric already exists in MongoDB
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

            # Construct enriched metadata dictionary
            metadata = dict(
                source=source,
                station=DBRef("stations", station.id),
                station_code=code,
                created_date=datetime.datetime.now(datetime.timezone.utc),
                parameter=parameter,
                cross_section=cross_section,
                zerogate=zerogate,
                water_level_warning=water_level_warning,
                water_level_critical=water_level_critical,
                # Store raw fields in metadata
                water_level=raw_water_level,
                water_level_value_list=raw_water_level_value_list,
                rain_sum_now=raw_rain_sum_now,
                rain_sum=raw_rain_sum,
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
