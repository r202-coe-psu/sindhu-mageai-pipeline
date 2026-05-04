import requests
import pytz
from datetime import datetime, timedelta

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process Data")
    metric_outputs = dict()

    # import pprint
    # pprint.pprint(data[741])

    for i, d in enumerate(data):
        attribute_outputs = []
        waterlevel_datetime = d.get("waterlevel_datetime", None)
        waterlevel_m = d.get("waterlevel_m", None)
        waterlevel_msl = d.get("waterlevel_msl", None)
        diff_wl_bank = d.get("diff_wl_bank", None)
        diff_wl_bank_text = d.get("diff_wl_bank_text", None)
        storage_percent = d.get("storage_percent", None)
        discharge = d.get("discharge", None)
        flow_rate = d.get("flow_rate", None)

        # format datetime e.g. 2026-05-04 16:20
        waterlevel_datetime = datetime.strptime(waterlevel_datetime, "%Y-%m-%d %H:%M")

        # process diff data
        # ต่ำกว่าตลิ่ง -> negative
        # ล้นตลิ่ง -> postive
        # ถ้าไม่มีข้อมูล diff -> 0
        if diff_wl_bank:
            diff_wl_bank = float(diff_wl_bank)
            if diff_wl_bank_text.startswith("ต่ำกว่าตลิ่ง"):
                diff_wl_bank = -diff_wl_bank
            elif diff_wl_bank_text.startswith("ล้นตลิ่ง"):
                diff_wl_bank = diff_wl_bank
            else:
                diff_wl_bank = 0
        # ensure numeric value
        if waterlevel_m:
            waterlevel_m = float(waterlevel_m)
        if waterlevel_msl:  # msl is mean sea level,
            waterlevel_msl = float(waterlevel_msl)
        if discharge:
            # print(
            #     f"(index: {i}, station: {d['station']['id']})discharge: {discharge} ({type(discharge)})"
            # )
            discharge = float(discharge)
        if flow_rate:
            # print(
            #     f"(index: {i}, station: {d['station']['id']})flow_rate: {flow_rate} ({type(flow_rate)})"
            # )
            flow_rate = float(flow_rate)

        station = d.get("station", {})
        if station:
            code = str(station.get("id")).strip()
            name = station.get("tele_station_name", {})
            name_th = name.get("th", "").strip()
            source = "thaiwater"

            attribute_outputs.append(
                {
                    "code": code,
                    "name_th": name_th,
                    "source": source,
                    "waterlevel_datetime": waterlevel_datetime,
                    "waterlevel_m": waterlevel_m,
                    "waterlevel_msl": waterlevel_msl,
                    "diff_wl_bank": diff_wl_bank,
                    "storage_percent": storage_percent,
                    "discharge": discharge,
                    "flow_rate": flow_rate,
                }
            )

            if attribute_outputs:
                metric_outputs[code] = attribute_outputs

    print(f"\nTotal stations:", len(metric_outputs))

    return metric_outputs
