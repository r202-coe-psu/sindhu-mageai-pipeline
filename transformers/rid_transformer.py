import json
from datetime import datetime, timezone, timedelta

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


# RID server เก็บข้อมูลใน Bangkok time (UTC+7)
BANGKOK_TZ = timezone(timedelta(hours=7))


def safe_float(value):
    """แปลง string เป็น float โดย handle null/empty"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_rid_datetime(dt_str):
    """
    Parse "2026-05-06 00:00:00.000" → datetime object (UTC)
    RID ส่งเวลามาเป็น Bangkok time → แปลงเป็น UTC ก่อนเก็บ
    """
    if not dt_str:
        return None
    try:
        dt_naive = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
        dt_bangkok = dt_naive.replace(tzinfo=BANGKOK_TZ)
        return dt_bangkok.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def transform_measurement(raw_record, fetched_at):
    """แปลง raw record หนึ่งตัวให้เป็น schema ใหม่"""
    return {
        "station_code": raw_record.get("STATION_ID"),
        "datetime": parse_rid_datetime(raw_record.get("DateValue")),
        "site_time": parse_rid_datetime(raw_record.get("SITE_TIME")),
        # ค่าวัด (แปลงเป็น float, null ก็เก็บเป็น None)
        "rainfall_15min": safe_float(raw_record.get("RF15")),       # mm
        "water_level_up": safe_float(raw_record.get("WL_UP_MSL")),  # m, MSL
        "water_level_down": safe_float(raw_record.get("WL_DOWN_MSL")),
        "flow": safe_float(raw_record.get("FLOW")),                  # m³/s
        "do": safe_float(raw_record.get("DO")),                      # mg/L
        "ec": safe_float(raw_record.get("EC")),                      # μS/cm
        "ph": safe_float(raw_record.get("PH")),
        "temperature": safe_float(raw_record.get("TP")),             # °C
        "salinity": safe_float(raw_record.get("SA")),                # ppt
        # metadata
        "source": "rid",
        "fetched_at": fetched_at,
    }


@transformer
def transform_rid_data(api_responses, *args, **kwargs):
    print("### เริ่ม transform ข้อมูล")
    
    fetched_at = datetime.now(timezone.utc)
    all_measurements = []
    failed_stations = []
    
    for response in api_responses:
        station_code = response.get("station_code")
        
        # ข้ามสถานีที่ block ก่อนหน้าดึงไม่สำเร็จ
        if response.get("status_code") != 200 or not response.get("raw_text"):
            failed_stations.append(station_code)
            continue
        
        # parse JSON string
        try:
            raw_records = json.loads(response["raw_text"])
        except json.JSONDecodeError as e:
            print(f"⚠️ {station_code}: parse JSON ไม่สำเร็จ — {e}")
            failed_stations.append(station_code)
            continue
        
        if not isinstance(raw_records, list):
            print(f"⚠️ {station_code}: response ไม่ใช่ list")
            failed_stations.append(station_code)
            continue
        
        # transform แต่ละ measurement
        for raw_record in raw_records:
            measurement = transform_measurement(raw_record, fetched_at)
            if measurement["datetime"]:  # ข้าม record ที่ไม่มี timestamp
                all_measurements.append(measurement)
    
    # สรุปผล
    print(f"\n📊 รวม measurement records: {len(all_measurements):,}")
    print(f"📍 สถานีที่ transform สำเร็จ: {len(api_responses) - len(failed_stations)} / {len(api_responses)}")
    
    if failed_stations:
        print(f"⚠️ สถานีที่ล้มเหลว: {failed_stations}")
    
    if all_measurements:
        print(f"\n📄 ตัวอย่าง record แรก:")
        import pprint
        pprint.pprint(all_measurements[0])
    
    return all_measurements