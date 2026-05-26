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

    ignore_keys = {"code", "source", "name_th", "waterlevel_datetime"}

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

        # 1. Bulk fetch existing metrics to avoid N+1 queries
        valid_timestamps = []
        for d in metrics_station:
            dt_str = d.get("waterlevel_datetime")
            if dt_str:
                valid_timestamps.append(datetime.datetime.fromisoformat(dt_str))
        
        existing_metrics_set = set()
        if valid_timestamps:
            min_ts = min(valid_timestamps)
            max_ts = max(valid_timestamps)
            
            existing_docs = await models.Metric.find(
                models.Metric.metadata["station"]["$id"] == station.id,
                models.Metric.timestamp >= min_ts,
                models.Metric.timestamp <= max_ts
            ).to_list()
            
            existing_metrics_set = {
                (doc.timestamp, doc.metadata["parameter"]) for doc in existing_docs
            }

        # 2. Process incoming metrics
        for data in metrics_station:
            current_code = data.get("code")
            current_source = data.get("source", source)
            name_th = data.get("name_th", station.name_th) 
            waterlevel_datetime = data.get("waterlevel_datetime")

            if not waterlevel_datetime:
                continue

            timestamp = datetime.datetime.fromisoformat(waterlevel_datetime)

            for parameter, value in data.items():
                if parameter in ignore_keys or value is None:
                    continue

                # Skip if already exists in database
                if (timestamp, parameter) in existing_metrics_set:
                    exist_counter += 1
                    # [RESTORED]
                    print(f"[/] Skip parameter {parameter} exists for station ({current_code})-{name_th} at {timestamp}")
                    continue

                metadata = dict(
                    source=current_source,
                    station=DBRef("stations", station.id),
                    station_code=current_code,
                    created_date=datetime.datetime.now(datetime.timezone.utc),
                    parameter=parameter,
                )

                metric = models.Metric(
                    timestamp=timestamp, value=value, metadata=metadata
                )

                metrics_to_save.append(metric)
                print(f"[+] Queue parameter {parameter} for station ({current_code})-{name_th} at {timestamp}")

    if metrics_to_save:
        print(f"\n[>] Inserting {len(metrics_to_save)} new documents to database...")
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