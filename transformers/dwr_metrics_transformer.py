import requests
import pytz
from datetime import datetime, timedelta

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process STN Data")
    metric_outputs = dict()
    for i, d in enumerate(data):
        province = str(d.get("province", "")).strip()
        if "สงขลา" not in province:
            continue

        date_str = d.get("date", None)
        rain     = d.get("rain", None)
        rain12h  = d.get("rain12h", None)
        rain07h  = d.get("rain07h", None)
        temp     = d.get("temp", None)
        wl       = d.get("wl", None)
        wl07h    = d.get("wl07h", None)
        soil     = d.get("soil", None)
        soil07h  = d.get("soil07h", None)

        # format datetime e.g. "18/05/67 03:00 น." -> "2024-05-18T03:00:00"
        waterlevel_datetime = None
        if date_str and date_str != "N/A":
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

        code    = str(d.get("stn", "")).strip()
        name_th = str(d.get("name", "")).strip()
        source  = "dwr"

        if code:
            record = {
                "code":               code,
                "name_th":            name_th,
                "source":             source,
                "waterlevel_datetime": waterlevel_datetime,
                "rain":    to_float(rain),
                "rain12h": to_float(rain12h),
                "rain07h": to_float(rain07h),
                "temp":    to_float(temp),
                "wl":      to_float(wl),
                "wl07h":   to_float(wl07h),
                "soil":    to_float(soil),
                "soil07h": to_float(soil07h),
            }

            
            metric_outputs.setdefault(code, []).append(record)

    print(f"\nTotal metric stations in Songkhla:", len(metric_outputs))

    return metric_outputs