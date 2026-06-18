import asyncio
import json
import os
import sys
import subprocess
import datetime

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


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


def simulate_raw_text(item):
    """จำลองผลลัพธ์ JSON string ให้ตรงกับโครงสร้างที่ได้จาก API แบบดั้งเดิม (getStationPlot.php)"""
    vals = item.get("values", {})
    val_wl = vals.get("water_level", {})
    val_r = vals.get("rain_sum_now", {})

    # หาวันเวลา (unixtime) และแปลงเป็นเขตเวลาประเทศไทย (UTC+7)
    unixtime = val_wl.get("unixtime") or val_r.get("unixtime")

    if isinstance(unixtime, list):
        unixtime = unixtime[0] if unixtime else None

    if not unixtime:
        # ลองดึงจากฟิลด์อื่นใน values
        for k, v in vals.items():
            if isinstance(v, dict) and v.get("unixtime"):
                u = v.get("unixtime")
                if isinstance(u, list):
                    if u:
                        unixtime = u[0]
                        break
                elif isinstance(u, (int, float)):
                    unixtime = u
                    break

    # ป้องกันกรณีที่ unixtime ไม่ใช่ตัวเลข
    if not isinstance(unixtime, (int, float)):
        try:
            unixtime = float(unixtime)
        except (TypeError, ValueError):
            unixtime = int(datetime.datetime.now().timestamp())

    tz_thailand = datetime.timezone(datetime.timedelta(hours=7))
    dt = datetime.datetime.fromtimestamp(unixtime, tz=tz_thailand)
    date_str = dt.strftime("%Y-%m-%d %H:%M:%S.000")

    wl_up = None
    wl_down = None

    # ดึงค่าระดับน้ำ WL_UP และ WL_DOWN จาก water_level_value_list.value
    wl_list = vals.get("water_level_value_list", {}).get("value", [])
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

    # หากไม่ได้ค่า wl_up ให้ใช้ค่าเดี่ยวจาก water_level
    if wl_up is None and val_wl.get("value") is not None:
        try:
            val_val = val_wl.get("value")
            if val_val and val_val != "-":
                wl_up = float(val_val)
        except ValueError:
            pass

    # ดึงค่าน้ำฝน RF15
    rf = None
    if val_r.get("value") is not None:
        try:
            val_val = val_r.get("value")
            if val_val and val_val != "-":
                rf = float(val_val)
        except ValueError:
            pass

    # สร้างข้อมูลแถวเดียว
    rows = [
        {
            "DateValue": date_str,
            "WL_UP_MSL": wl_up,
            "WL_DOWN_MSL": wl_down,
            "FLOW": None,
            "RF15": rf,
            "DO": None,
            "EC": None,
            "PH": None,
            "TP": None,
            "SA": None,
        }
    ]

    return json.dumps(rows)


@data_loader
def fetch_station_plots(*args, **kwargs):
    print("🚀 เริ่มดึงข้อมูลการวัด (Metrics) จาก WebSocket สำหรับสถานีทั้งหมด...")
    try:
        data = get_ws_data()
    except Exception as e:
        print(f"❌ ดึงข้อมูลจาก WebSocket ล้มเหลว: {e}")
        return []

    results = []

    for key, item in data.items():
        code = item.get("code", "")
        if code:
            try:
                raw_text_simulated = simulate_raw_text(item)
                results.append(
                    {
                        "station_code": code,
                        "status_code": 200,
                        "raw_text": raw_text_simulated,
                        "error": None,
                    }
                )
            except Exception as e:
                print(f"⚠️ ข้อผิดพลาดในการประมวลผลข้อมูลการวัดของสถานี {code}: {e}")
                results.append(
                    {
                        "station_code": code,
                        "status_code": 500,
                        "raw_text": None,
                        "error": str(e),
                    }
                )

    success = sum(1 for r in results if r["status_code"] == 200)
    failed = len(results) - success
    print(f"✅ ประมวลผลสำเร็จ: {success} | ❌ ล้มเหลว: {failed}")

    # แสดงตัวอย่างข้อมูล
    first_success = next((r for r in results if r["status_code"] == 200), None)
    if first_success:
        print(f"\n📄 ตัวอย่างข้อมูลผลลัพธ์จำลองของ {first_success['station_code']}:")
        print(first_success["raw_text"])

    return results