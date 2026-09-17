import requests
import pytz
from datetime import datetime, timedelta

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer

PROVINCE_CODE = "90"
# API returns Thai local time without an offset
TZ_THAILAND = pytz.timezone("Asia/Bangkok")


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process Data (Rain Metrics)")
    metric_outputs = dict()

    for i, d in enumerate(data):
        attribute_outputs = []

        geocode = d.get("geocode") or {}
        if str(geocode.get("province_code", "")).strip() != PROVINCE_CODE:
            continue

        station = d.get("station", {})
        if not station:
            continue

        code = str(station.get("id")).strip()
        name = station.get("tele_station_name", {})
        name_th = name.get("th", "").strip()
        source = "thaiwater_rain"

        rainfall_datetime_str = d.get("rainfall_datetime", None)
        rain_24h = d.get("rain_24h", None)
        rain_1h = d.get("rain_1h", None)

        # แปลง string วันเวลาจาก API เป็น datetime object
        if rainfall_datetime_str:
            try:
                rainfall_datetime = TZ_THAILAND.localize(
                    datetime.strptime(rainfall_datetime_str, "%Y-%m-%d %H:%M")
                )
            except Exception as e:
                print(f"Error parsing datetime for station {code}: {e}")
                continue
        else:
            continue

        if rain_24h is None:
            continue

        attribute_outputs.append(
            {
                "code": code,
                "name_th": name_th,
                "source": source,
                "rainfall_datetime": rainfall_datetime.isoformat(),
                # parameter names ต้องตรงกับ RAIN_PARAMETERS ใน
                # sindhu/services/interpolations.py ("rain")
                "rain": float(rain_24h),
                "rain_1h": float(rain_1h) if rain_1h is not None else None,
            }
        )

        if attribute_outputs:
            metric_outputs[code] = attribute_outputs

    print(f"Total rain stations processed in Transformer: {len(metric_outputs)}")
    return metric_outputs
