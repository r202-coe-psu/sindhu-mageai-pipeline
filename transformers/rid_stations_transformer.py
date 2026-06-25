import requests
import pytz
from datetime import datetime, timedelta

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process Data")
    station_outputs = dict()

    import pprint

    pprint.pprint(data[0])

    for d in data:
        attribute_outputs = []
        station = d.get("station", {})
        if station:
            code = str(station.get("station_code") or "").strip()
            name_th = (station.get("name_th") or "").strip()
            name_en = (station.get("name_en") or "").strip()
            basin = (station.get("basin") or "").strip()
            location = (station.get("location") or "").strip()
            longitude = station.get("longitude")
            latitude = station.get("latitude")
            station_type = (
                station.get("station_type") or station.get("station_type_raw") or ""
            ).strip()
            url = (station.get("url") or "https://telerid.rid.go.th").strip()
            water_level_warning = station.get("water_level_warning")
            water_level_critical = station.get("water_level_critical")
            source = "rid"

            attribute_outputs.append(
                {
                    "code": code,
                    "name_en": name_en,
                    "name_th": name_th,
                    "station_type": station_type,
                    "location": location,
                    "basin": basin,
                    "longitude": longitude,
                    "latitude": latitude,
                    "url": url,
                    "source": source,
                    "water_level_warning": water_level_warning,
                    "water_level_critical": water_level_critical,
                }
            )

            if attribute_outputs:
                station_outputs[code] = attribute_outputs

    print(f"\nTotal stations:", len(station_outputs))

    return station_outputs
