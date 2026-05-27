import requests
import pytz
from datetime import datetime, timedelta

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process Data (Metrics)")
    metric_outputs = dict()

    for i, d in enumerate(data):
        attribute_outputs = []
        
        station = d.get("station", {})
        if not station:
            continue
            
        code = str(station.get("id")).strip()
        name = station.get("tele_station_name", {})
        name_th = name.get("th", "").strip()
        source = "thaiwater"

        waterlevel_datetime_str = d.get("waterlevel_datetime", None)
        waterlevel_m = d.get("waterlevel_m", None)
        waterlevel_msl = d.get("waterlevel_msl", None)
        diff_wl_bank = d.get("diff_wl_bank", None)
        diff_wl_bank_text = d.get("diff_wl_bank_text", None)
        storage_percent = d.get("storage_percent", None)
        discharge = d.get("discharge", None)
        flow_rate = d.get("flow_rate", None)

        # แปลง string วันเวลาจาก API เป็น datetime object
        if waterlevel_datetime_str:
            try:
                waterlevel_datetime = datetime.strptime(waterlevel_datetime_str, "%Y-%m-%d %H:%M")
            except Exception as e:
                print(f"Error parsing datetime for station {code}: {e}")
                continue
        else:
            continue

        # คำนวณค่าน้ำล้นตลิ่ง / ต่ำกว่าตลิ่ง
        if diff_wl_bank:
            diff_wl_bank = float(diff_wl_bank)
            if diff_wl_bank_text and diff_wl_bank_text.startswith("ต่ำกว่าตลิ่ง"):
                diff_wl_bank = -diff_wl_bank
            elif diff_wl_bank_text and diff_wl_bank_text.startswith("ล้นตลิ่ง"):
                diff_wl_bank = diff_wl_bank
            else:
                diff_wl_bank = 0

        if waterlevel_m:
            waterlevel_m = float(waterlevel_m)
        if waterlevel_msl:
            waterlevel_msl = float(waterlevel_msl)
        if discharge:
            discharge = float(discharge)
        if flow_rate:
            flow_rate = float(flow_rate)

        attribute_outputs.append(
            {
                "code": code,
                "name_th": name_th,
                "source": source,
                # ส่งค่าวันเวลาในรูปแบบ ISO String ไปให้ Exporter
                "waterlevel_datetime": waterlevel_datetime.isoformat(), 
                "waterlevel_m": waterlevel_m,
                "waterlevel_msl": waterlevel_msl,
                "diff_wl_bank": diff_wl_bank,
                "storage_percent": storage_percent,
                "discharge": discharge,
                "flow_rate": flow_rate,
            }
        )

        if attribute_outputs:
            metric_outputs[code] = attribute_outputs

    print(f"Total stations processed in Transformer: {len(metric_outputs)}")
    return metric_outputs