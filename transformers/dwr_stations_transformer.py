import requests

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


def get_province_code(s: dict) -> str:
    prov = s.get("provinceInfo")
    if not isinstance(prov, dict):
        prov = (s.get("addressInfo") or {}).get("provinceInfo") or {}
    if isinstance(prov, dict):
        return str(prov.get("code", ""))
    return ""


def fetch_station_metadata(code: str) -> dict:
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
        point = entity.get("point") or {}
        return {
            "name_en":      entity.get("stnNameEn"),
            "location_th":  entity.get("locationTh"),
            "location_en":  entity.get("locationEn"),
            "stream":       entity.get("stream"),
            "agency":       entity.get("agency"),
            "rating_type":  entity.get("ratingType"),
            "cctv_enabled": entity.get("cctvEnabled"),
            "lat": to_float(point.get("lat")),
            "lon": to_float(point.get("lon")),
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
    print("### Starting Process DWR Telemetry Stations (Filtering for Songkhla)")
    station_outputs = dict()

    for d in data:
        attribute_outputs = []

        if get_province_code(d) != PROVINCE_CODE:
            continue

        code = str(d.get("code", "")).strip()
        if not code:
            continue

        meta       = fetch_station_metadata(code)
        point      = d.get("point") or {}
        name_th    = d.get("nameTh") or meta.get("name_en") or code
        lat        = meta.get("lat") or to_float(point.get("lat"))
        lon        = meta.get("lon") or to_float(point.get("lon"))
        equipments = d.get("stnEquipments") or []
        basin      = ((d.get("mainBasinInfo") or {}).get("nameTh")
                      or (d.get("mainBasinInfo") or {}).get("code"))
        sub_basin  = ((d.get("subBasinInfo") or {}).get("nameTh")
                      or (d.get("subBasinInfo") or {}).get("code"))

        attribute_outputs.append({
            "code":    code,
            "name":    meta.get("name_en") or name_th,
            "name_th": name_th,
            "source":  "dwr_telemetry",
            "url":     f"{BASE}/home?stnCode={code}",
            "status":  "active",
            "lat": lat,
            "lon": lon,
            "metadata": {
                "station_type": equipments,
                "agency":       meta.get("agency") or d.get("agency"),
                "rating_type":  meta.get("rating_type"),
                "cctv_enabled": meta.get("cctv_enabled"),
                "stream":       meta.get("stream"),
                "location_th":  meta.get("location_th"),
                "location_en":  meta.get("location_en"),
                "province_code": PROVINCE_CODE,
                "basin":         basin,
                "sub_basin":     sub_basin,
                "lbMsl":    meta.get("lbMsl"),
                "rbMsl":    meta.get("rbMsl"),
                "bbMsl":    meta.get("bbMsl"),
                "zflowMsl": meta.get("zflowMsl"),
                "wlFw": meta.get("wlFw"),
                "wlFc": meta.get("wlFc"),
                "wlDw": meta.get("wlDw"),
                "wlDc": meta.get("wlDc"),
                "rfFw": meta.get("rfFw"),
                "rfFc": meta.get("rfFc"),
                "qfw":  meta.get("qfw"),
                "qfc":  meta.get("qfc"),
                "qdw":  meta.get("qdw"),
                "qdc":  meta.get("qdc"),
            },
        })

        if attribute_outputs:
            station_outputs[code] = attribute_outputs

    print(f"\nTotal stations in Songkhla:", len(station_outputs))
    return station_outputs