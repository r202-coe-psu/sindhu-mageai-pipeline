# rid api loader 

import asyncio
import httpx
import nest_asyncio
from datetime import datetime

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader

nest_asyncio.apply()


BASE_URL = "http://119.110.213.190/rid/getStationPlot.php"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
}
CONCURRENCY_LIMIT = 10   # ยิงพร้อมกันสูงสุด 10 requests
REQUEST_TIMEOUT = 15     # วินาที


async def fetch_one_station(client, station_code, site_time, semaphore):
    """ยิง API หนึ่งสถานี และคืนค่า raw response"""
    params = {
        "table": f"DB_SONGKHLA.dbo.TBL_{station_code}",
        "dateBack": "-99",
        "site_time": site_time,
    }

    async with semaphore:  # ควบคุมไม่ให้ยิงเกิน 10 ตัวพร้อมกัน
        try:
            response = await client.get(
                BASE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            return {
                "station_code": station_code,
                "status_code": response.status_code,
                "raw_text": response.text if response.status_code == 200 else None,
                "error": None,
            }
        except Exception as e:
            return {
                "station_code": station_code,
                "status_code": None,
                "raw_text": None,
                "error": str(e),
            }


async def fetch_all_stations(station_codes):
    # สร้าง site_time เป็นวันที่ปัจจุบัน รูปแบบ MM/DD/YYYY
    site_time = datetime.now().strftime("%m/%d/%Y")
    print(f"ดึงข้อมูลของวันที่: {site_time}")
    print(f"จำนวนสถานี: {len(station_codes)} (ยิงพร้อมกัน {CONCURRENCY_LIMIT} ตัว)")

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async with httpx.AsyncClient(headers=HEADERS) as client:
        tasks = [
            fetch_one_station(client, code, site_time, semaphore)
            for code in station_codes
        ]
        results = await asyncio.gather(*tasks)

    # สรุปผล
    success = sum(1 for r in results if r["status_code"] == 200)
    failed = len(results) - success
    print(f"สำเร็จ: {success} | ล้มเหลว: {failed}")

    if failed > 0:
        failed_codes = [r["station_code"] for r in results if r["status_code"] != 200]
        print(f"   สถานีที่ล้มเหลว: {failed_codes}")

    return results


@data_loader
def fetch_station_plots(station_codes, *args, **kwargs):
    if not station_codes:
        print("ไม่มี station codes เข้ามา — ข้ามการยิง API")
        return []
    
    results = asyncio.run(fetch_all_stations(station_codes))
    
    # ดูตัวอย่าง raw_text ตัวแรกที่สำเร็จ
    first_success = next((r for r in results if r["status_code"] == 200), None)
    if first_success:
        print(f"\nตัวอย่าง response จาก {first_success['station_code']}:")
        print(first_success["raw_text"][:500])  # 500 ตัวอักษรแรก
    
    return results