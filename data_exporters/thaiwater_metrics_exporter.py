import asyncio
import nest_asyncio
import datetime
from bson import ObjectId, DBRef
from sindhu import models

nest_asyncio.apply()

if "data_exporter" not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

source = "thaiwater"


async def insert_data(metrics_stations):
    print("### Initialize Beanie")
    await models.init_default_beanie_client()

    print("### Start insert data (Strict Songkhla Metrics Only)")
    metrics_to_save = []
    exist_counter = 0

    for code, metrics_station in metrics_stations.items():
        # ค้นหา station ด้วย code + source (การกรองจังหวัดทำที่ transformer แล้ว)
        station = (
            await models.Station.find(
                models.Station.status == "active",
                models.Station.code == code,
                models.Station.source == source,
            )
            .sort(-models.Station.updated_date)
            .first_or_none()
        )
        
        # ยังไม่มี station ของ source นี้ใน DB ให้ข้าม (ต้องรัน thaiwater_stations ก่อน)
        if not station:
            continue

        print(f"[>] Processing metrics for station: {code} - {metrics_station[0]['name_th']}")

        for data in metrics_station:
            station_code = data.pop("code")
            name_th = data.pop("name_th")
            data_source = data.pop("source")
            waterlevel_datetime = data.pop("waterlevel_datetime")

            # แปลงค่ากลับเป็น datetime object สำหรับบันทึกพิกัดเวลา (Timestamp)
            timestamp = datetime.datetime.fromisoformat(waterlevel_datetime)

            # Fallback Imputation for diff_wl_bank
            waterlevel = data.get("waterlevel")
            diff_wl_bank = data.get("diff_wl_bank")
            if diff_wl_bank is None and waterlevel is not None:
                water_level_critical = station.metadata.get("water_level_critical")
                if water_level_critical is not None:
                    data["diff_wl_bank"] = waterlevel - water_level_critical

            for parameter, value in data.items():
                if value is None:
                    continue
    
                # เช็คข้อมูลซ้ำซ้อนในระดับ Metric
                exists_metric = await models.Metric.find_one(
                    models.Metric.timestamp == timestamp,
                    models.Metric.metadata["station"]["$id"] == station.id,
                    models.Metric.metadata["parameter"] == parameter,
                ).exists()

                if exists_metric:
                    exist_counter += 1
                    continue

                # จัดเตรียม Metadata และแก้ไข source ให้เป็น thaiwater ให้ถูกต้อง
                metadata = dict(
                    source="thaiwater", 
                    station=DBRef("stations", station.id),
                    station_code=station_code,
                    created_date=datetime.datetime.now(datetime.timezone.utc),
                    parameter=parameter,
                )

                metric = models.Metric(
                    timestamp=timestamp, value=value, metadata=metadata
                )

                metrics_to_save.append(metric)

    # ทำการบันทึกข้อมูลแบบ Bulk Insert
    if metrics_to_save:
        await models.Metric.insert_many(metrics_to_save)

    total_docs = exist_counter + len(metrics_to_save)
    print(f"\nTotal processed documents for Songkhla: {total_docs}")
    print(f"Found exists: {exist_counter} documents")
    print(f"Inserted new: {len(metrics_to_save)} documents")
    if total_docs > 0:
        print(f"Inserted rate: {len(metrics_to_save)/total_docs*100:.2f}%")
    print("\n### Success insert data")


@data_exporter
def export_data_to_mongodb(metrics_stations, **kwargs) -> None:
    asyncio.run(insert_data(metrics_stations))
    print("### Done Process")