import asyncio
import json
import os
import sys
import subprocess
import nest_asyncio

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader

nest_asyncio.apply()


def get_ws_data():
    try:
        import websockets
    except ImportError:
        print("websockets not found, installing websockets...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
        except Exception as e:
            print(f"Normal install failed: {e}. Trying user install...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "websockets"])
            except Exception as ue:
                print(f"User install failed: {ue}")
        
        # Refresh python paths to find the newly installed package
        import site
        import importlib
        if hasattr(site, "getusersitepackages"):
            user_site = site.getusersitepackages()
            if user_site not in sys.path:
                sys.path.append(user_site)
        importlib.invalidate_caches()
        import websockets

    async def _fetch():
        uri = "wss://telerid.rid.go.th/ws/public/"
        print(f"Connecting to WebSocket: {uri} ...")
        async with websockets.connect(uri, max_size=20 * 1024 * 1024) as websocket:
            print("Connected! Receiving INIT message...")
            message = await websocket.recv()
            outer = json.loads(message)
            inner = json.loads(outer.get("message", "{}"))
            return inner.get("data", {})

    return asyncio.run(_fetch())


def map_station_data(item):
    code = item.get("code")
    if not code:
        return None
    
    # Format Thai location address
    tambon = item.get("tambon")
    amphur = item.get("amphur")
    province = item.get("province")
    loc_parts = []
    if tambon:
        loc_parts.append(f"ต.{tambon.strip()}")
    if amphur:
        loc_parts.append(f"อ.{amphur.strip()}")
    if province:
        loc_parts.append(f"จ.{province.strip()}")
    location_str = " ".join(loc_parts) if loc_parts else "-"

    # Format Station Type
    measure = item.get("measure", {})
    types = []
    if measure.get("wl"):
        types.append("วัดระดับน้ำ")
    if measure.get("r"):
        types.append("วัดปริมาณน้ำฝน")
    if measure.get("wq"):
        types.append("วัดคุณภาพน้ำ")
    station_type_raw = "  ".join(types) if types else "-"

    # Coordinates
    coords = item.get("location", {})
    longitude = coords.get("x")
    latitude = coords.get("y")

    # Basin name
    basin = item.get("basin", {})
    basin_name = basin.get("name") if isinstance(basin, dict) else None

    return {
        "station": {
            "station_code": code,
            "name_th": item.get("name") or code,
            "name_en": None,
            "basin": basin_name,
            "location": location_str,
            "longitude": longitude,
            "latitude": latitude,
            "station_type_raw": station_type_raw,
            "url": "https://telerid.rid.go.th",
        }
    }


@data_loader
def load_station_details(*args, **kwargs):
    print("🚀 เริ่มดึงข้อมูลสถานี (Stations) จาก WebSocket...")
    try:
        data = get_ws_data()
    except Exception as e:
        print(f"❌ ดึงข้อมูลจาก WebSocket ล้มเหลว: {e}")
        return []

    results = []
    for key, item in data.items():
        province = item.get("province") or ""
        if "สงขลา" in province:
            station_detail = map_station_data(item)
            if station_detail:
                results.append(station_detail)

    print(f"✅ สำเร็จ: โหลดสถานีทั้งหมด {len(results)} สถานี ในจังหวัดสงขลา")
    if results:
        print(f"\n📄 ตัวอย่าง 5 สถานีแรก:")
        import pprint
        pprint.pprint(results[0:5])
    
    return results