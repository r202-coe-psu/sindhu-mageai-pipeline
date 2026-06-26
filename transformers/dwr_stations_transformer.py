import requests
import pytz
from datetime import datetime, timedelta

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process Data")
    station_outputs = dict()

    for d in data:
        attribute_outputs = []

        code        = str(d.get("stn", "")).strip()
        name        = str(d.get("name", "")).strip()
        name_th     = str(d.get("name", "")).strip()
        source      = "dwr"
        url         = "https://ews.dwr.go.th"

        station_type = str(d.get("stn_type", "")).strip()
        dept         = str(d.get("dept", "")).strip()
        rtu_grp      = str(d.get("rtu_grp", "")).strip()
        gd_id        = str(d.get("gd_id", "")).strip()

        latitude         = d.get("latitude")
        longitude        = d.get("longitude")
        tambon_name_th   = str(d.get("tambon", "")).strip()
        amphoe_name_th   = str(d.get("amphoe", "")).strip()
        province_name_th = str(d.get("province", "")).strip()

        TARGET_PROVINCES = ["สงขลา", "songkhla"]
        
        province_name_lower = province_name_th.lower()
        if not any(target in province_name_lower for target in TARGET_PROVINCES):
            continue

        main_basin  = str(d.get("main_basin", "")).strip()
        sub_basin   = str(d.get("sub_basin", "")).strip()
        sub_station = d.get("sub_station", [])

        if code:
            attribute_outputs.append(
                {
                    "code":    code,
                    "name":    name,
                    "name_th": name_th,
                    "source":  source,
                    "url":     url,

                    "station_type": station_type,
                    "dept":         dept,
                    "rtu_grp":      rtu_grp,
                    "gd_id":        gd_id,

                    "latitude":          latitude,
                    "longitude":         longitude,
                    "tambon_name_th":    tambon_name_th,
                    "amphoe_name_th":    amphoe_name_th,
                    "province_name_th":  province_name_th,

                    "main_basin":  main_basin,
                    "sub_basin":   sub_basin,
                    "sub_station": sub_station,
                }
            )

        if attribute_outputs:
            station_outputs[code] = attribute_outputs

    print(f"\nTotal stations:", len(station_outputs))
    return station_outputs