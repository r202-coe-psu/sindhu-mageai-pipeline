import requests
import pytz
from datetime import datetime, timedelta

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer

@transformer
def transform(data, *args, **kwargs):
    
    output = dict()
    for station_code, datas in station_datas.items():

        transform_output = []
        for data in datas:
            station_name = data.get("nameEN")
            if station_name:
                station_name = station_name.strip()

            name_th = data.get("nameTH")
            if name_th:
                name_th = name_th.strip()

            area_en = data.get("areaEN")
            if area_en:
                area_en = area_en.strip()

            area_th = data.get("areaTH")
            if area_th:
                area_th = area_th.strip()

            station_type = data.get("stationType")
            if station_type:
                station_type = station_type.strip()

            longitude = data.get("long")
            latitude = data.get("lat")
            status = data.get("status")
            url = "http://air4thai.com/"
            source = "air4thai"

            transform_output.append(
                {
                    "name": station_name,
                    "name_th": name_th,
                    "url": url,
                    "source": source,
                    "area_en": area_en,
                    "area_th": area_th,
                    "station_type": station_type,
                    "is_gas": status,
                    "longitude": longitude,
                    "latitude": latitude,
                }
            )

        if transform_output:
            output[station_code] = transform_output

    return output
