import httpx
import datetime
import pytz
import bson
from beanie.odm.operators.find.comparison import In
import asyncio
import nest_asyncio
import requests
import json
from playwright.async_api import async_playwright

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

nest_asyncio.apply()

async def fetch_dwr_stations():
    url  = "https://ews.dwr.go.th/ews/web-service/stn"
    data = {"action": "LoadStation"}

    print(f"กำลังยิง API: {url}")
    response = requests.post(url, data=data, timeout=30)
    response.raise_for_status()

    result = response.json()
    print(f"ดึงข้อมูลสำเร็จ! {len(result)} สถานี")
    return result

@data_loader
def load_data_from_api(*args, **kwargs):
    results = asyncio.run(fetch_dwr_stations())
    return results