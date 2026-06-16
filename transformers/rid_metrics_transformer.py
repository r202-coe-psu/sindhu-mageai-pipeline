import json
from datetime import datetime

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process Data")
    metric_outputs = dict()
 
    for d in data:
        if d.get("status_code") != 200:
            continue

        raw_text = d.get("raw_text")
        if not raw_text:
            continue

        code = str(d.get("station_code", "")).strip()
        if not code:
            continue

        try:
            rows = json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"[!] Failed to parse raw_text for station {code}: {e}")
            continue

        # เอาเฉพาะข้อมูลล่าสุดของแต่ละสถานี (เหมือนที่หน้าเว็บ RID sort client-side)
        rows = [r for r in rows if r.get("DateValue")]
        if not rows:
            continue
        rows.sort(key=lambda r: r["DateValue"], reverse=True)
        rows = rows[:1]

        attribute_outputs = []
        for row in rows:
            date_value = row.get("DateValue")
            if not date_value:
                continue
            try:
                waterlevel_datetime = datetime.strptime(
                    date_value, "%Y-%m-%d %H:%M:%S.%f"
                )
            except ValueError:
                print(f"[!] Invalid DateValue for station {code}: {date_value}")
                continue

            waterlevel_msl_up = row.get("WL_UP_MSL")
            waterlevel_msl_down = row.get("WL_DOWN_MSL")
            flow = row.get("FLOW")
            rainfall_15m = row.get("RF15")
            do_value = row.get("DO")
            ec = row.get("EC")
            ph = row.get("PH")
            tp = row.get("TP")
            sa = row.get("SA")

            # ensure numeric value
            if waterlevel_msl_up is not None:
                waterlevel_msl_up = float(waterlevel_msl_up)
            if waterlevel_msl_down is not None:
                waterlevel_msl_down = float(waterlevel_msl_down)
            if flow is not None:
                flow = float(flow)
            if rainfall_15m is not None:
                rainfall_15m = float(rainfall_15m)
            if do_value is not None:
                do_value = float(do_value)
            if ec is not None:
                ec = float(ec)
            if ph is not None:
                ph = float(ph)
            if tp is not None:
                tp = float(tp)
            if sa is not None:
                sa = float(sa)

            attribute_outputs.append(
                {
                    "code": code,
                    "source": "rid",
                    "waterlevel_datetime": waterlevel_datetime,
                    "waterlevel_msl_up": waterlevel_msl_up,
                    "waterlevel_msl_down": waterlevel_msl_down,
                    "flow": flow,
                    "rainfall_15m": rainfall_15m,
                    "do": do_value,
                    "ec": ec,
                    "ph": ph,
                    "tp": tp,
                    "sa": sa,
                }
            )

        if attribute_outputs:
            metric_outputs[code] = attribute_outputs

    print(f"\nTotal stations:", len(metric_outputs))

    return metric_outputs
