import asyncio
import nest_asyncio 
from datetime import datetime, timezone
from typing import List, Dict
from pymongo import UpdateOne

from sindhu import models

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
nest_asyncio.apply()

async def upsert_measurements(measurements: List[Dict]) -> Dict:
    """
    Bulk upsert measurements โดยใช้ (station_code, datetime) เป็น unique key
    - ถ้ามี record เดิมอยู่แล้ว → update ค่าใหม่ (เผื่อ RID มีการแก้ไขย้อนหลัง)
    - ถ้ายังไม่มี → insert พร้อม created_date
    """
    print("### Initialize Beanie")
    await models.init_default_beanie_client()

    now = datetime.now(timezone.utc)
    collection = models.Measurement.get_motor_collection()

    # สร้าง bulk operations
    operations = []
    for m in measurements:
        # unique key — กำหนดว่า record ไหนคือ "ตัวเดียวกัน"
        filter_query = {
            "station_code": m["station_code"],
            "datetime": m["datetime"],
        }

        # update ค่าทุกครั้ง แต่ created_date ตั้งครั้งเดียวตอน insert
        update_doc = {
            "$set": {**m, "updated_date": now},
            "$setOnInsert": {"created_date": now},
        }

        operations.append(UpdateOne(filter_query, update_doc, upsert=True))

    print(f"### Bulk upsert {len(operations):,} records...")
    
    # ordered=False → ถ้ามี record ไหนพัง ตัวที่เหลือยังทำต่อได้
    result = await collection.bulk_write(operations, ordered=False)

    summary = {
        "matched": result.matched_count,
        "modified": result.modified_count,
        "upserted": result.upserted_count,
    }

    print(f"🔍 Matched (เจอเดิม): {summary['matched']:,}")
    print(f"✏️  Modified (อัปเดต): {summary['modified']:,}")
    print(f"➕ Upserted (เพิ่มใหม่): {summary['upserted']:,}")

    return summary


@data_exporter
def export_measurements_to_mongodb(measurements: List[Dict], **kwargs) -> None:
    if not measurements:
        print("⚠️ ไม่มี measurements เข้ามา — ข้ามการ export")
        return

    asyncio.run(upsert_measurements(measurements))
    print("### Done Process")