import requests
import pytz
from datetime import datetime, timedelta

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process Data (Filtering for Songkhla)")
    station_outputs = dict()

    # ลูปเพื่อตรวจสอบข้อมูลสถานีทั้งหมด
    for d in data:
        attribute_outputs = []
        
        # 1. ดึงข้อมูล geocode มาตรวจสอบจังหวัดก่อน
        geocode = d.get("geocode", {})
        province_name_th = geocode.get("province_name", {}).get("th", "").strip()
        province_name_en = geocode.get("province_name", {}).get("en", "").strip().lower()
        province_code = geocode.get("province_code", "").strip()

        TARGET_PROVINCES = ["สงขลา", "songkhla"]

        # 🎯 เงื่อนไข: เช็คว่าจังหวัดอยู่ในเป้าหมายหรือไม่
        if not any(target in province_name_th for target in TARGET_PROVINCES) and not any(target in province_name_en for target in TARGET_PROVINCES):
            continue

        # 2. ถ้าเป็นจังหวัดสงขลา จะทำกระบวนการดึงข้อมูลด้านล่างต่อตามปกติ
        station = d.get("station", {})
        if station:
            code = str(station.get("id")).strip()
            name = station.get("tele_station_name", {})
            name_en = name.get("en", "").strip()
            name_th = name.get("th", "").strip()
            station_type = station.get("tele_station_type", "").strip()
            longitude = station.get("tele_station_long")
            latitude = station.get("tele_station_lat")
            url = station.get("url", "https://thaiwater.net").strip()
            source = "thaiwater"

            min_bank = station.get("min_bank")
            critical_level_m = station.get("critical_level_m")
            warning_level_m = station.get("warning_level_m")
            
            water_level_critical = critical_level_m if critical_level_m is not None else min_bank
            water_level_warning = warning_level_m
            if water_level_warning is None and water_level_critical is not None:
                water_level_warning = water_level_critical * 0.8

            tumbon_code = geocode.get("tumbon_code", "").strip()
            tumbon_name = geocode.get("tumbon_name", {})
            tumbon_name_en = tumbon_name.get("en", "").strip()
            tumbon_name_th = tumbon_name.get("th", "").strip()

            amphoe_code = geocode.get("amphoe_code", "").strip()
            amphoe_name = geocode.get("amphoe_name", {})
            amphoe_name_en = amphoe_name.get("en", "").strip()
            amphoe_name_th = amphoe_name.get("th", "").strip()

            attribute_outputs.append(
                {
                    "code": code,
                    "name": name_en,
                    "name_th": name_th,
                    "station_type": station_type,
                    "longitude": longitude,
                    "latitude": latitude,
                    "url": url,
                    "source": source,
                    "water_level_critical": water_level_critical,
                    "water_level_warning": water_level_warning,
                    "tumbon_code": tumbon_code,
                    "tumbon_name_en": tumbon_name_en,
                    "tumbon_name_th": tumbon_name_th,
                    "amphoe_code": amphoe_code,
                    "amphoe_name_en": amphoe_name_en,
                    "amphoe_name_th": amphoe_name_th,
                    "province_code": province_code,
                    "province_name_en": geocode.get("province_name", {}).get("en", "").strip(),
                    "province_name_th": province_name_th,
                }
            )

            if attribute_outputs:
                station_outputs[code] = attribute_outputs

    print(f"\nTotal stations in Songkhla:", len(station_outputs))

    return station_outputs