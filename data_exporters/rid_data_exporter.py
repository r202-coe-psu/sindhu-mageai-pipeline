import asyncio
import nest_asyncio
from typing import List, Dict

from sindhu import models

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

nest_asyncio.apply()


async def insert_metrics(metrics: List[Dict]) -> Dict:
    """
    Insert metrics เข้า time series collection
    Strategy: query existing → filter ออก → bulk insert ใหม่
    """
    print("### Initialize Beanie")
    await models.init_default_beanie_client()
    
    if not metrics:
        return {"inserted": 0, "skipped": 0}
    
    # หาช่วงเวลาของ batch นี้ เพื่อ query existing แค่ window ที่เกี่ยวข้อง
    timestamps = [m["timestamp"] for m in metrics]
    min_ts = min(timestamps)
    max_ts = max(timestamps)
    
    print(f"ช่วงเวลาของ batch: {min_ts} → {max_ts}")
    print("Query existing records ในช่วงนี้...")
    
    # 👇 ใช้ Beanie find() แทน motor collection
    existing_docs = await models.Metric.find(
        {
            "timestamp": {"$gte": min_ts, "$lte": max_ts},
            "metadata.source": "rid",
        }
    ).to_list()
    
    # สร้าง set ของ key (timestamp, station_code, metric_type) ที่มีอยู่แล้ว
    existing_keys = set()
    for doc in existing_docs:
        meta = doc.metadata or {}
        key = (
            doc.timestamp,
            meta.get("station_code"),
            meta.get("metric_type"),
        )
        existing_keys.add(key)
    
    print(f"   เจอ {len(existing_keys):,} records ที่มีอยู่แล้ว")
    
    # filter เฉพาะ records ใหม่
    new_metrics_data = []
    for m in metrics:
        key = (
            m["timestamp"],
            m["metadata"]["station_code"],
            m["metadata"]["metric_type"],
        )
        if key not in existing_keys:
            new_metrics_data.append(m)
    
    skipped = len(metrics) - len(new_metrics_data)
    print(f"จะ insert ใหม่: {len(new_metrics_data):,}")
    print(f"ข้าม (มีอยู่แล้ว): {skipped:,}")
    
    if not new_metrics_data:
        return {"inserted": 0, "skipped": skipped}
    
    # แปลง dict เป็น Metric document ก่อน insert
    print(f"### Building Metric documents...")
    metric_docs = [models.Metric(**m) for m in new_metrics_data]
    
    # Bulk insert ผ่าน Beanie API
    print(f"### Inserting {len(metric_docs):,} records...")
    await models.Metric.insert_many(metric_docs)
    
    summary = {"inserted": len(metric_docs), "skipped": skipped}
    print(f"Insert สำเร็จ: {summary['inserted']:,}")
    
    return summary


@data_exporter
def export_metrics_to_mongodb(metrics: List[Dict], **kwargs) -> None:
    if not metrics:
        print("️ไม่มี metrics เข้ามา — ข้ามการ export")
        return
    
    asyncio.run(insert_metrics(metrics))
    print("### Done Process")