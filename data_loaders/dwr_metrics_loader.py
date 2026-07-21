import requests

if "data_loader" not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if "test" not in globals():
    from mage_ai.data_preparation.decorators import test

BASE = "https://telemetry.dwr.go.th"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE}/home",
    "Content-Type": "application/json",
    "Accept": "application/json, */*",
}

PAYLOAD = {
    "filter": {
        "waterStatusMode": "RiverBasinCapStatus",
        "mode": "ANY",
        "onlyCCTV": False,
        "eqWl": True, "eqRf": True, "eqCctv": True,
        "agencyDwr": True, "agencyRid": True,
        "agencyHii": True, "agencyEws": True, "agencyEgat": True,
        "rfLvNone": True, "rfLvLight": True, "rfLvModerate": True,
        "rfLvHeavy": True, "rfLvVeryHeavy": True,
        "rbCapCritLow": True, "rbCapLow": True, "rbCapNormal": True,
        "rbCapHigh": True, "rbCapOverCap": True,
    }
}


@data_loader
def load_data_from_api(*args, **kwargs):
    resp = requests.post(
        f"{BASE}/api/public/teleMap/stnSearch",
        json=PAYLOAD,
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    stations = resp.json().get("value", [])
    print(f"✅ ดึงข้อมูลสำเร็จ {len(stations)} สถานี (ทุกจังหวัด ไม่กรอง)")
    return stations


@test
def test_output(output, *args) -> None:
    assert output is not None, "output is None"
