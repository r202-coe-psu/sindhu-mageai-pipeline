import requests
import pytz
from datetime import datetime, timedelta

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process Data")
    station_outputs = dict()

    # import pprint
    # pprint.pprint(data[0])

    for d in data:
        attribute_outputs = []
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

            # metadata
            geocode = d.get("geocode", {})

            tumbon_code = geocode.get("tumbon_code", "").strip()
            tumbon_name = geocode.get("tumbon_name", {})
            tumbon_name_en = tumbon_name.get("en", "").strip()
            tumbon_name_th = tumbon_name.get("th", "").strip()

            amphoe_code = geocode.get("amphoe_code", "").strip()
            amphoe_name = geocode.get("amphoe_name", {})
            amphoe_name_en = amphoe_name.get("en", "").strip()
            amphoe_name_th = amphoe_name.get("th", "").strip()

            province_code = geocode.get("province_code", "").strip()
            province_name = geocode.get("province_name", {})
            province_name_en = province_name.get("en", "").strip()
            province_name_th = province_name.get("th", "").strip()

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
                    # metadata
                    "tumbon_code": tumbon_code,
                    "tumbon_name_en": tumbon_name_en,
                    "tumbon_name_th": tumbon_name_th,
                    "amphoe_code": amphoe_code,
                    "amphoe_name_en": amphoe_name_en,
                    "amphoe_name_th": amphoe_name_th,
                    "province_code": province_code,
                    "province_name_en": province_name_en,
                    "province_name_th": province_name_th,
                }
            )

            if attribute_outputs:
                station_outputs[code] = attribute_outputs

    print(f"\nTotal stations:", len(station_outputs))

    return station_outputs
