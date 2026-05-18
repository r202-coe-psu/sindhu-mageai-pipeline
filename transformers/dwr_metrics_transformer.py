import requests
import pytz
from datetime import datetime, timedelta

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer


WL_TYPES = {"wl"}


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process STN WL Data")
    metric_outputs = dict()

    for i, d in enumerate(data):
        attribute_outputs = []

        stn_type = d.get("stn_type", "").strip()
        date_str = d.get("date", None)
        rain = d.get("rain", None)
        rain12h = d.get("rain12h", None)
        rain07h = d.get("rain07h", None)
        temp = d.get("temp", None)
        wl = d.get("wl", None)
        wl07h = d.get("wl07h", None)

        if stn_type not in WL_TYPES:
            continue

        # format datetime e.g. "18/05/26 03:00 น." -> "2026-05-18T03:00:00"
        waterlevel_datetime = None
        try:
            clean = date_str.replace(" น.", "").strip()
            day, month, year_th = clean.split(" ")[0].split("/")
            time_part = clean.split(" ")[1]
            year_ce = int(year_th) + 1957
            waterlevel_datetime = datetime.strptime(
                f"{year_ce}-{month}-{day} {time_part}", "%Y-%m-%d %H:%M"
            ).isoformat()
        except Exception as e:
            print(f"(index: {i}, stn: {d.get('stn')}) datetime parse error: {e}")

        # ensure numeric value
        def to_float(val):
            try:
                return float(val) if val and val != "N/A" else None
            except (ValueError, TypeError):
                return None

        rain = to_float(rain)
        rain12h = to_float(rain12h)
        rain07h = to_float(rain07h)
        temp = to_float(temp)
        wl = to_float(wl)
        wl07h = to_float(wl07h)

        code = str(d.get("stn", "")).strip()
        name_th = str(d.get("name", "")).strip()
        source = "dwr"

        if code:
            attribute_outputs.append(
                {
                    "code": code,
                    "name_th": name_th,
                    "source": source,
                    "waterlevel_datetime": waterlevel_datetime,
                    "rain": rain,
                    "rain12h": rain12h,
                    "rain07h": rain07h,
                    "temp": temp,
                    "wl": wl,
                    "wl07h": wl07h,
                }
            )

            if attribute_outputs:
                metric_outputs[code] = attribute_outputs

    print(f"\nTotal stations:", len(metric_outputs))

    return metric_outputs