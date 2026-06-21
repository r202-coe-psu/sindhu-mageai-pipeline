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
    print("### เริ่มต้นระบบส่งออกข้อมูล (Beanie Initializing)")
    await models.init_default_beanie_client()

    print("\n=======================================================")
    print("   รายงานสรุปปริมาณน้ำฝน ลุ่มน้ำทะเลสาบสงขลา (DWR Telemetry)  ")
    print("=======================================================")
    
    metrics_to_save = []
    exist_counter = 0

    ignore_keys = {
        "code",
        "source",
        "name_th",
        "waterlevel_datetime",
        "status",
        "alert_max",
        "alert_min",
    }

    for code, metrics_station in metrics_stations.items():
        station = (
            await models.Station.find(
                models.Station.status == "active", models.Station.code == code
            )
            .sort(-models.Station.updated_date)
            .first_or_none()
        )
        if not station:
            print(f"[!] ไม่พบสถานี {code} ในฐานข้อมูล")
            continue

        # 1. ดึงข้อมูลตัวชี้วัด (Metrics) ที่มีอยู่แล้วในฐานข้อมูลแบบเป็นกลุ่ม (Bulk fetch)
        valid_timestamps = []
        for d in metrics_station:
            dt_str = d.get("waterlevel_datetime")
            if not dt_str:
                continue
            try:
                valid_timestamps.append(datetime.datetime.fromisoformat(dt_str))
            except ValueError:
                continue
        existing_metrics_set = set()
        if valid_timestamps:
            min_ts = min(valid_timestamps)
            max_ts = max(valid_timestamps)

            existing_docs = await models.Metric.find(
                models.Metric.metadata["station"]["$id"] == station.id,
                models.Metric.timestamp >= min_ts,
                models.Metric.timestamp <= max_ts,
            ).to_list()

            existing_metrics_set = {
                (doc.timestamp, doc.metadata["parameter"]) for doc in existing_docs
            }

        # 2. ประมวลผลข้อมูลตัวชี้วัด (Metrics) ที่รับเข้ามาใหม่
        for data in metrics_station:
            current_code = data.get("code")
            current_source = data.get("source", source)
            name_th = station.name_th or data.get("name_th", current_code)
            waterlevel_datetime = data.get("waterlevel_datetime")

            if not waterlevel_datetime:
                continue

            timestamp = datetime.datetime.fromisoformat(waterlevel_datetime)
            # จัดรูปแบบเวลาให้อ่านง่าย (เช่น 18/06/2026 เวลา 11:00 น.)
            time_formatted = timestamp.strftime("%d/%m/%Y เวลา %H:%M น.")

            for parameter, value in data.items():
                if parameter in ignore_keys or value is None:
                    continue

                val_formatted = f"{value:.1f} มม."
                status_rain = "🌧️ ฝนตก" if value > 0 else "☀️ ไม่มีฝน"

                # ข้ามขั้นตอนหากข้อมูลนี้มีอยู่แล้วในฐานข้อมูล
                if (timestamp, parameter) in existing_metrics_set:
                    exist_counter += 1
                    print(
                        f" -> [มีข้อมูลแล้ว] สถานี: {name_th:<35} | ค่าฝน: {val_formatted:<8} ({status_rain}) | วันเวลาตรวจวัด: {time_formatted}"
                    )
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
                print(
                    f" -> [บันทึกใหม่] สถานี: {name_th:<35} | ค่าฝน: {val_formatted:<8} ({status_rain}) | วันเวลาตรวจวัด: {time_formatted}"
                )

    if metrics_to_save:
        print(f"\n[>] กำลังบันทึกข้อมูลฝนสะสมใหม่ {len(metrics_to_save)} รายการลง MongoDB...")
        await models.Metric.insert_many(metrics_to_save)

    total = exist_counter + len(metrics_to_save)
    print("\n=======================================================")
    print("                  สรุปการทำงานของระบบ                  ")
    print("=======================================================")
    print(f"จำนวนข้อมูลทั้งหมด: {total} รายการ")
    print(f"ข้ามรายการที่มีอยู่แล้ว: {exist_counter} รายการ")
    print(f"บันทึกข้อมูลสำเร็จ: {len(metrics_to_save)} รายการ")
    print("=======================================================\n")


@data_exporter
def export_data_to_mongodb(metrics_stations, **kwargs) -> None:
    asyncio.run(insert_data(metrics_stations))
    return