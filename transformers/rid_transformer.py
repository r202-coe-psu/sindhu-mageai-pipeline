import json
from datetime import datetime, timezone, timedelta

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


BANGKOK_TZ = timezone(timedelta(hours=7))

# mapping: API field → (metric_type, unit)
METRIC_FIELDS = {
    "RF15":         ("rainfall_15min",   "mm"),
    "WL_UP_MSL":    ("water_level_up",   "m"),
    "WL_DOWN_MSL":  ("water_level_down", "m"),
    "FLOW":         ("flow",             "m3/s"),
    "DO":           ("do",               "mg/L"),
    "EC":           ("ec",               "uS/cm"),
    "PH":           ("ph",               ""),
    "TP":           ("temperature",      "C"),
    "SA":           ("salinity",         "ppt"),
}


def safe_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_rid_datetime(dt_str):
    if not dt_str:
        return None
    try:
        dt_naive = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
        return dt_naive.replace(tzinfo=BANGKOK_TZ).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def explode_to_metrics(raw_record):
    """
    แปลง 1 raw record (มีหลายค่าวัด) → list ของ metric records (1 ค่าต่อ 1 record)
    """
    timestamp = parse_rid_datetime(raw_record.get("DateValue"))
    station_code = raw_record.get("STATION_ID")
    
    if not timestamp or not station_code:
        return []
    
    metrics = []
    for api_field, (metric_type, unit) in METRIC_FIELDS.items():
        value = safe_float(raw_record.get(api_field))
        if value is None:
            continue   # ข้ามค่าที่ null/empty
        
        metadata = {
            "station_code": station_code,
            "metric_type": metric_type,
            "source": "rid",
        }
        if unit:
            metadata["unit"] = unit
        
        metrics.append({
            "timestamp": timestamp,
            "metadata": metadata,
            "value": value,
        })
    
    return metrics


@transformer
def transform_rid_data(api_responses, *args, **kwargs):
    print("### เริ่ม transform ข้อมูลเป็น EAV format")
    
    all_metrics = []
    failed_stations = []
    
    for response in api_responses:
        station_code = response.get("station_code")
        
        if response.get("status_code") != 200 or not response.get("raw_text"):
            failed_stations.append(station_code)
            continue
        
        try:
            raw_records = json.loads(response["raw_text"])
        except json.JSONDecodeError:
            failed_stations.append(station_code)
            continue
        
        if not isinstance(raw_records, list):
            failed_stations.append(station_code)
            continue
        
        # explode แต่ละ raw record → หลาย metric records
        for raw_record in raw_records:
            all_metrics.extend(explode_to_metrics(raw_record))
    
    success_count = len(api_responses) - len(failed_stations)
    print(f"\nรวม metric records: {len(all_metrics):,}")
    print(f"สถานีสำเร็จ: {success_count} / {len(api_responses)}")
    
    if failed_stations:
        print(f"สถานีล้มเหลว: {failed_stations}")
    
    if all_metrics:
        print(f"\nตัวอย่าง 2 records แรก:")
        import pprint
        pprint.pprint(all_metrics[:2])
    
    return all_metrics