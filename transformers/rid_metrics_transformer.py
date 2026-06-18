import pytz
from datetime import datetime

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process Data (Metrics)")
    metric_outputs = dict()

    for d in data:
        code = str(d.get("code", "")).strip()
        if not code:
            continue

        vals = d.get("values", {})
        val_wl = vals.get("water_level", {})
        val_r = vals.get("rain_sum_now", {})

        # 1. Extract and format date/time
        unixtime = val_wl.get("unixtime") or val_r.get("unixtime")
        if isinstance(unixtime, list):
            unixtime = unixtime[0] if unixtime else None

        if not unixtime:
            for k, v in vals.items():
                if isinstance(v, dict) and v.get("unixtime"):
                    u = v.get("unixtime")
                    if isinstance(u, list) and u:
                        unixtime = u[0]
                        break
                    elif isinstance(u, (int, float)):
                        unixtime = u
                        break

        if not isinstance(unixtime, (int, float)):
            try:
                unixtime = float(unixtime)
            except (TypeError, ValueError):
                unixtime = datetime.now().timestamp()

        tz_thailand = pytz.timezone('Asia/Bangkok')
        waterlevel_datetime = datetime.fromtimestamp(unixtime, tz=tz_thailand)

        # 2. Extract Water Level (WL_UP, WL_DOWN)
        wl_list = vals.get("water_level_value_list", {}).get("value", [])
        wl_up = None
        wl_down = None

        if wl_list and len(wl_list) > 0:
            try:
                val0 = wl_list[0]
                if val0 and val0 != "-":
                    wl_up = float(val0)
            except ValueError:
                pass

        if wl_list and len(wl_list) > 1:
            try:
                val1 = wl_list[1]
                if val1 and val1 != "-":
                    wl_down = float(val1)
            except ValueError:
                pass

        # Fallback to single water_level value for wl_up
        if wl_up is None and val_wl.get("value") is not None:
            try:
                val_val = val_wl.get("value")
                if val_val and val_val != "-":
                    wl_up = float(val_val)
            except ValueError:
                pass

        # 3. Extract Rainfall (RF15)
        rf = None
        if val_r.get("value") is not None:
            try:
                val_val = val_r.get("value")
                if val_val and val_val != "-":
                    rf = float(val_val)
            except ValueError:
                pass

        # 4. Gather metrics and metadata
        attribute_outputs = [
            {
                "code": code,
                "source": "rid",
                "waterlevel_datetime": waterlevel_datetime,
                "waterlevel_msl_up": wl_up,
                "waterlevel_msl_down": wl_down,
                "flow": None,
                "rainfall_15m": rf,
                "do": None,
                "ec": None,
                "ph": None,
                "tp": None,
                "sa": None,
                # Pass physical profile details to exporter
                "cross_section": d.get("cross_section"),
                "zerogate": d.get("zerogate"),
                "water_level_warning": d.get("water_level_warning"),
                "water_level_critical": d.get("water_level_critical"),
            }
        ]

        metric_outputs[code] = attribute_outputs

    print(f"\nTotal stations processed:", len(metric_outputs))

    return metric_outputs
