import asyncio
import httpx
import nest_asyncio
from bs4 import BeautifulSoup

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader

nest_asyncio.apply()


BASE_URL = "http://119.110.213.190/rid/stations.php"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
}
CONCURRENCY_LIMIT = 10
REQUEST_TIMEOUT = 15

# Mapping element ID → field name ที่จะใช้ในผลลัพธ์
FIELD_MAP = {
    "MainContent_lblSubMaster":       "name_th",
    "MainContent_lblRiverName":       "basin",
    "MainContent_lblStationPicLat":   "latitude",
    "MainContent_lblStationPicLong":  "longitude",
    "MainContent_lblLocation":        "location",
    "MainContent_lblType":            "station_type_raw",
}


def extract_text(soup, element_id):
    """ดึง text จาก element ตาม id, คืน None ถ้าไม่เจอหรือว่างเปล่า"""
    elem = soup.find(id=element_id)
    if elem is None:
        return None
    text = elem.get_text(strip=True)
    # ค่าว่าง "-" หรือ string ว่างคืน None
    if not text or text == "-":
        return None
    return text


def parse_station_html(html, station_code):
    """parse HTML page หนึ่งสถานี → dict ของข้อมูลจำเพาะ"""
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {"station_code": station_code}
    for elem_id, field_name in FIELD_MAP.items():
        result[field_name] = extract_text(soup, elem_id)
    
    return result


async def fetch_one_station_detail(client, station_code, semaphore):
    """ยิง HTML page หนึ่งสถานี"""
    params = {"IdCode": f"08:{station_code}"}
    
    async with semaphore:
        try:
            response = await client.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
            response.encoding = 'utf-8'
            
            result = {"station_code": station_code, "status_code": response.status_code}
            if response.status_code == 200:
                result["html"] = response.text
            return result
            
        except Exception as e:
            return {
                "station_code": station_code,
                "status_code": -1,
                "error": str(e),
            }


async def fetch_all_station_details(station_codes):
    print(f"🚀 ดึงข้อมูลจำเพาะ: {len(station_codes)} สถานี (พร้อมกัน {CONCURRENCY_LIMIT} ตัว)")
    
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    async with httpx.AsyncClient(headers=HEADERS) as client:
        tasks = [
            fetch_one_station_detail(client, code, semaphore)
            for code in station_codes
        ]
        responses = await asyncio.gather(*tasks)
    
    # parse HTML ทุกสถานีใน-process (ไม่ต้อง async — CPU-bound งานเล็ก)
    print("🔍 Parsing HTML...")
    results = []
    failed = []
    
    for resp in responses:
        code = resp["station_code"]
        if resp.get("status_code") != 200 or "html" not in resp:
            failed.append(code)
            continue
        
        try:
            parsed = parse_station_html(resp["html"], code)
            results.append({"station": parsed})
        except Exception as e:
            print(f"⚠️ {code}: parse ผิดพลาด — {e}")
            failed.append(code)
    
    print(f"✅ สำเร็จ: {len(results)} | ❌ ล้มเหลว: {len(failed)}")
    if failed:
        print(f"   สถานีที่ล้มเหลว: {failed}")
    
    if results:
        print(f"\n📄 ตัวอย่าง 5 สถานีแรก:")
        import pprint
        pprint.pprint(results[0:5])
    
    return results


@data_loader
def load_station_details(station_codes, *args, **kwargs):
    if not station_codes:
        print("⚠️ ไม่มี station codes เข้ามา")
        return []
    results = asyncio.run(fetch_all_station_details(station_codes))
    return results