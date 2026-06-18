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
        raw_water_level = vals.get("water_level")
        raw_water_level_value_list = vals.get("water_level_value_list", {}).get("value")
        raw_rain_sum_now = vals.get("rain_sum_now")
        raw_rain_sum = vals.get("rain_sum")

        # 1. Extract and format date/time
        unixtime = None
        if raw_water_level:
            unixtime = raw_water_level.get("unixtime")
        if not unixtime and raw_rain_sum_now:
            unixtime = raw_rain_sum_now.get("unixtime")

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

        # 2. Extract Water Level (water_level, wl_down)
        wl_up = None
        wl_down = None

        if raw_water_level_value_list and len(raw_water_level_value_list) > 0:
            try:
                val0 = raw_water_level_value_list[0]
                if val0 and val0 != "-":
                    wl_up = float(val0)
            except ValueError:
                pass

        if raw_water_level_value_list and len(raw_water_level_value_list) > 1:
            try:
                val1 = raw_water_level_value_list[1]
                if val1 and val1 != "-":
                    wl_down = float(val1)
            except ValueError:
                pass

        # Fallback to single water_level value for wl_up
        if wl_up is None and raw_water_level and raw_water_level.get("value") is not None:
            try:
                val_val = raw_water_level.get("value")
                if val_val and val_val != "-":
                    wl_up = float(val_val)
            except ValueError:
                pass

        # 3. Extract Rainfall (rain_sum_now)
        rf = None
        if raw_rain_sum_now and raw_rain_sum_now.get("value") is not None:
            try:
                val_val = raw_rain_sum_now.get("value")
                if val_val and val_val != "-":
                    rf = float(val_val)
            except ValueError:
                pass

        # 4. Clean cross_section (remove gauge)
        cross_section = d.get("cross_section")
        if cross_section:
            for cs in cross_section:
                cs.pop("gauge", None)

        # 5. Gather metrics and metadata
        attribute_outputs = []

        # Parameter 1: water_level
        if wl_up is not None:
            attribute_outputs.append({
                "code": code,
                "source": "rid",
                "waterlevel_datetime": waterlevel_datetime,
                "parameter_name": "water_level",
                "parameter_value": wl_up,
                # Metadata
                "cross_section": cross_section,
                "zerogate": d.get("zerogate"),
                "water_level_warning": d.get("water_level_warning"),
                "water_level_critical": d.get("water_level_critical"),
                "raw_water_level": raw_water_level,
                "raw_water_level_value_list": raw_water_level_value_list,
                "raw_rain_sum_now": raw_rain_sum_now,
                "raw_rain_sum": raw_rain_sum,
            })

        # Parameter 2: wl_down
        if wl_down is not None:
            attribute_outputs.append({
                "code": code,
                "source": "rid",
                "waterlevel_datetime": waterlevel_datetime,
                "parameter_name": "wl_down",
                "parameter_value": wl_down,
                # Metadata
                "cross_section": cross_section,
                "zerogate": d.get("zerogate"),
                "water_level_warning": d.get("water_level_warning"),
                "water_level_critical": d.get("water_level_critical"),
                "raw_water_level": raw_water_level,
                "raw_water_level_value_list": raw_water_level_value_list,
                "raw_rain_sum_now": raw_rain_sum_now,
                "raw_rain_sum": raw_rain_sum,
            })

        # Parameter 3: rain_sum_now
        if rf is not None:
            attribute_outputs.append({
                "code": code,
                "source": "rid",
                "waterlevel_datetime": waterlevel_datetime,
                "parameter_name": "rain_sum_now",
                "parameter_value": rf,
                # Metadata
                "cross_section": cross_section,
                "zerogate": d.get("zerogate"),
                "water_level_warning": d.get("water_level_warning"),
                "water_level_critical": d.get("water_level_critical"),
                "raw_water_level": raw_water_level,
                "raw_water_level_value_list": raw_water_level_value_list,
                "raw_rain_sum_now": raw_rain_sum_now,
                "raw_rain_sum": raw_rain_sum,
            })

        if attribute_outputs:
            metric_outputs[code] = attribute_outputs

    print(f"\nTotal stations processed:", len(metric_outputs))

    return metric_outputs
