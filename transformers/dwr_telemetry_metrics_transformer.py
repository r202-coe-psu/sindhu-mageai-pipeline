import requests
from datetime import datetime

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer

BASE = "https://telemetry.dwr.go.th"
PROVINCE_CODE = "90"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE}/home",
    "Accept": "application/json, */*",
}


def to_float(val):
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def parse_timestamp(ts_str) -> str | None:
    if not ts_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(ts_str)[:19], fmt).isoformat()
        except ValueError:
            continue
    return None


def fetch_thresholds(code: str) -> dict:
    try:
        resp = requests.get(
            f"{BASE}/api/public/station/getByCode/{code}",
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code != 200:
            return {}
        entity = (resp.json().get("value", {})
                             .get("fullCon", {})
                             .get("entity", {}))
        return {
            "lbMsl":    to_float(entity.get("lbMsl")),
            "rbMsl":    to_float(entity.get("rbMsl")),
            "bbMsl":    to_float(entity.get("bbMsl")),
            "zflowMsl": to_float(entity.get("zflowMsl")),
            "wlFw": to_float(entity.get("wlFw")),
            "wlFc": to_float(entity.get("wlFc")),
            "wlDw": to_float(entity.get("wlDw")),
            "wlDc": to_float(entity.get("wlDc")),
            "rfFw": to_float(entity.get("rfFw")),
            "rfFc": to_float(entity.get("rfFc")),
            "qfw":  to_float(entity.get("qfw")),
            "qfc":  to_float(entity.get("qfc")),
            "qdw":  to_float(entity.get("qdw")),
            "qdc":  to_float(entity.get("qdc")),
        }
    except Exception as exc:
        print(f"    [!] getByCode {code} error: {exc}")
        return {}


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process DWR Telemetry Data")

    metric_outputs = dict()

    for i, d in enumerate(data):
        province_code = (d.get("provinceInfo") or {}).get("code", "")
        if str(province_code) != PROVINCE_CODE:
            continue

        code    = str(d.get("code", "")).strip()
        name_th = str(d.get("nameTh", "")).strip()
        source  = "dwr_telemetry"

        if not code:
            continue

        wl_raw   = to_float(d.get("currWaterLevelValue"))
        rf24_raw = to_float(d.get("currRainfallValue"))
        fr_raw   = to_float(d.get("currFlowRateValue"))

        ts_raw = (d.get("currWlTimestamp")
                  or d.get("currRfTimestamp")
                  or d.get("currDataTimestamp"))
        waterlevel_datetime = parse_timestamp(ts_raw)

        if not waterlevel_datetime:
            print(f"(index: {i}, stn: {code}) ไม่มี timestamp ข้าม")
            continue

        thresh = fetch_thresholds(code)
        lb = thresh.get("lbMsl")
        rb = thresh.get("rbMsl")

        if lb is not None and rb is not None:
            bank_msl = min(lb, rb)
        elif lb is not None:
            bank_msl = lb
        elif rb is not None:
            bank_msl = rb
        else:
            bank_msl = None

        diff_wl_bank = (round(wl_raw - bank_msl, 4)
                        if wl_raw is not None and bank_msl is not None else None)

        record = {
            "code":                code,
            "name_th":             name_th,
            "source":              source,
            "waterlevel_datetime": waterlevel_datetime,
            "waterlevel_msl":      wl_raw,
            "flow_rate":           fr_raw,
            "rainfall_24h":        rf24_raw,
            "diff_wl_bank":        diff_wl_bank,
            "lbMsl":    lb,
            "rbMsl":    rb,
            "bbMsl":    thresh.get("bbMsl"),
            "zflowMsl": thresh.get("zflowMsl"),
            "wlFw": thresh.get("wlFw"),
            "wlFc": thresh.get("wlFc"),
            "wlDw": thresh.get("wlDw"),
            "wlDc": thresh.get("wlDc"),
            "rfFw": thresh.get("rfFw"),
            "rfFc": thresh.get("rfFc"),
            "qfw":  thresh.get("qfw"),
            "qfc":  thresh.get("qfc"),
            "qdw":  thresh.get("qdw"),
            "qdc":  thresh.get("qdc"),
        }

        metric_outputs.setdefault(code, []).append(record)

    print(f"\nTotal metric stations in Songkhla: {len(metric_outputs)}")
    return metric_outputs