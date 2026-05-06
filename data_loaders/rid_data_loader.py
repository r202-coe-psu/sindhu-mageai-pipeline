import httpx
import datetime
import pytz
import bson
from beanie.odm.operators.find.comparison import In
import asyncio
import nest_asyncio
import requests
import json
import requests
from bs4 import BeautifulSoup

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


def fetch_rid_station_codes():
    url = "http://119.110.213.190/rid/showlist.php?list=08"
    print(f"กำลังยิง URL ไปที่: {url} ...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36',
    }

    station_codes = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        print(f"Status Code: {response.status_code}")

        if response.status_code != 200:
            print("Server ตอบกลับมาแบบมี Error:")
            print(response.text)
            return station_codes

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')

        if not table:
            print("ไม่พบตารางในหน้าเว็บ")
            return station_codes

        rows = table.find_all('tr')

        # ข้ามแถวแรก (header)
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue

            # คอลัมน์ที่ 1: รหัสสถานี (อยู่ใน <a> tag)
            code_cell = cells[0]
            link_tag = code_cell.find('a')
            station_code = (
                link_tag.get_text(strip=True)
                if link_tag
                else code_cell.get_text(strip=True)
            )

            if station_code:
                station_codes.append(station_code)

        print(f"ดึงรหัสสถานีสำเร็จ ทั้งหมด {len(station_codes)} สถานี")

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")

    return station_codes


@data_loader
def load_data_from_rid(*args, **kwargs):
    codes = fetch_rid_station_codes()
    print(f"รหัสสถานีทั้งหมด : {codes[:]}")
    return codes