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

        province = d.get("province", "")
        province_lower = province.lower()
        TARGET_PROVINCES = ["สงขลา", "songkhla"]
        if not any(target in province_lower for target in TARGET_PROVINCES):
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

        # 5. Extract water_level_warning and water_level_critical
        water_level_warning = d.get("water_level_warning")
        if water_level_warning is not None and water_level_warning != "-":
            try:
                water_level_warning = float(water_level_warning)
            except ValueError:
                water_level_warning = None
        else:
            water_level_warning = None

        water_level_critical = d.get("water_level_critical")
        if water_level_critical is not None and water_level_critical != "-":
            try:
                water_level_critical = float(water_level_critical)
            except ValueError:
                water_level_critical = None
        else:
            water_level_critical = None

        # 6. Calculate diff_wl_bank
        diff_wl_bank = None
        if wl_up is not None and water_level_critical is not None:
            diff_wl_bank = wl_up - water_level_critical

        # 7. Gather metrics and metadata
        attribute_outputs = []

        if wl_up is not None or water_level_warning is not None or water_level_critical is not None or diff_wl_bank is not None:
            attribute_outputs.append({
                "code": code,
                "source": "rid",
                "waterlevel_datetime": waterlevel_datetime.isoformat(),
                "waterlevel": wl_up,
                "water_critical_level": water_level_critical,
                "water_warning_level": water_level_warning,
                "diff_wl_bank": diff_wl_bank,
            })

        if attribute_outputs:
            metric_outputs[code] = attribute_outputs

    print(f"\nTotal stations processed:", len(metric_outputs))

    return metric_outputs
