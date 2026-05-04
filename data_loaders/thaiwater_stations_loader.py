import httpx
import datetime
import pytz
import bson
from beanie.odm.operators.find.comparison import In
import asyncio
import nest_asyncio
import requests
import json

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

nest_asyncio.apply()

async def test_thaiwater_api():
    url = "https://api-v3.thaiwater.net/api/v1/thaiwater30/provinces/waterlevel"

    print(f"กำลังยิง API ไปที่: {url} ...")

    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}\n")

        if response.status_code == 200:
            data = response.json()

            print("--- โครงสร้าง JSON ที่ได้จาก API (ดึงมาให้ดูแค่ 1 รายการ) ---")
            if isinstance(data, list) and len(data) > 0:
                # print(json.dumps(data[0], ensure_ascii=False, indent=2))
                print(f"\n✅ ดึงข้อมูลสำเร็จ! มีข้อมูลทั้งหมด {len(data)} จังหวัด/สถานี")
            else:
                # print(json.dumps(data, ensure_ascii=False, indent=2))
                print(f"\n✅ ดึงข้อมูลสำเร็จ! มีข้อมูลทั้งหมด {len(data)} รายการ")
        else:
            print("❌ API ตอบกลับมาแบบมี Error:")
            print(response.text)

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")

    return data["data"]

@data_loader
def load_data_from_api(*args, **kwargs):
    results = asyncio.run(test_thaiwater_api())
    return results


