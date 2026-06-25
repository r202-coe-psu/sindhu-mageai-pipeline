import asyncio
import json
import os
import sys
import subprocess
import datetime

if "data_loader" not in globals():
    from mage_ai.data_preparation.decorators import data_loader


def get_ws_data():
    try:
        import websockets
    except ImportError:
        print("websockets not found, installing websockets...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "websockets"]
            )
        except Exception as e:
            print(f"Normal install failed: {e}. Trying user install...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "--user", "websockets"]
                )
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
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                print(
                    f"Connecting to WebSocket: {uri} (Attempt {attempt}/{max_retries}) ..."
                )
                async with websockets.connect(
                    uri, max_size=20 * 1024 * 1024, open_timeout=15
                ) as websocket:
                    print("Connected! Receiving INIT message...")
                    message = await websocket.recv()
                    outer = json.loads(message)
                    inner = json.loads(outer.get("message", "{}"))
                    return inner.get("data", {})
            except Exception as e:
                print(f"Connection attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    backoff = 2**attempt
                    print(f"Waiting {backoff} seconds before retrying...")
                    await asyncio.sleep(backoff)
                else:
                    raise e

    return asyncio.run(_fetch())


@data_loader
def fetch_station_plots(*args, **kwargs):
    print("🚀 เริ่มดึงข้อมูลการวัด (Metrics) ดิบจาก WebSocket...")
    try:
        data = get_ws_data()
    except Exception as e:
        print(f"❌ ดึงข้อมูลจาก WebSocket ล้มเหลว: {e}")
        return []

    # ดึงเฉพาะรายการข้อมูลสถานีในจังหวัดสงขลา
    results = []
    for key, item in data.items():
        province = item.get("province") or ""
        if "สงขลา" in province:
            results.append(item)

    print(f"✅ โหลดข้อมูลดิบสำเร็จ ทั้งหมด {len(results)} สถานี ในจังหวัดสงขลา")

    if results:
        print(f"\n📄 ตัวอย่างข้อมูลสถานีแรกที่ดึงได้:")
        import pprint

        pprint.pprint(results[0])

    return results
