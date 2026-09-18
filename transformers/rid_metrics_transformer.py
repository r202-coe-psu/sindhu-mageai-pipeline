import pytz
from datetime import datetime, timedelta

if "transformer" not in globals():
    from mage_ai.data_preparation.decorators import transformer

# RID รายงานเซ็นเซอร์ที่ตายด้วยค่าคงที่แทน null ถ้าปล่อยผ่านจะกลายเป็น
# diff_wl_bank ติดลบมหาศาล ซึ่งระบบจะอ่านว่า "น้ำต่ำกว่าตลิ่งมาก = ปลอดภัย"
# ทั้งที่ความจริงคือไม่มีข้อมูล
WATER_LEVEL_SENTINELS = (-9.99, -999.0)
WATER_LEVEL_FLOOR = -50.0

# วันฝนของ RID ตัดรอบที่ 07:00 (ตามเว็บ telerid)
# rain_sum_now    = ฝนสะสมตั้งแต่ 07:00 วันนี้ถึงเวลาที่วัด
# rain_sum[0]     = ฝนสะสม 24 ชม. (07:00 เมื่อวาน - 07:00 วันนี้)
# rain_sum[1..6]  = ฝนสะสม 2-7 วัน สิ้นสุด 07:00 วันนี้
TZ_THAILAND = pytz.timezone("Asia/Bangkok")
RAIN_DAY_CUTOFF_HOUR = 7


def parse_rain(val):
    """แปลงค่าฝนเป็น float คืน None ถ้าไม่มีข้อมูลหรือติดลบ"""
    if val is None or (isinstance(val, str) and val.strip() in ("", "-")):
        return None
    try:
        rain = float(val)
    except (TypeError, ValueError):
        return None
    return rain if rain >= 0 else None


def first_unixtime(u):
    if isinstance(u, list):
        u = u[0] if u else None
    try:
        return float(u)
    except (TypeError, ValueError):
        return None


def rain_day_end(unixtime):
    """เวลา 07:00 ล่าสุดที่ไม่เกิน unixtime คือจุดสิ้นสุดของรอบฝน 24 ชม."""
    dt = datetime.fromtimestamp(unixtime, tz=TZ_THAILAND)
    end = dt.replace(hour=RAIN_DAY_CUTOFF_HOUR, minute=0, second=0, microsecond=0)
    if end > dt:
        end -= timedelta(days=1)
    return end


def parse_water_level(val, code):
    """แปลงค่าระดับน้ำเป็น float คืน None ถ้าไม่มีข้อมูลหรือเป็นค่า sentinel"""
    if val is None or (isinstance(val, str) and val.strip() in ("", "-")):
        return None

    try:
        level = float(val)
    except (TypeError, ValueError):
        return None

    if any(abs(level - sentinel) < 1e-6 for sentinel in WATER_LEVEL_SENTINELS):
        print(f"(stn: {code}) ระดับน้ำ {level} เป็นค่า sentinel เซ็นเซอร์ไม่ส่งข้อมูล ข้าม")
        return None

    if level < WATER_LEVEL_FLOOR:
        print(f"(stn: {code}) ระดับน้ำ {level} ต่ำผิดปกติเกินจริง ข้าม")
        return None

    return level


@transformer
def transform(data, *args, **kwargs):
    print("### Starting Process Data (Metrics)")
    metric_outputs = dict()

    for d in data:
        code = str(d.get("code", "")).strip()
        if not code:
            continue

        province = d.get("province", "")
        province_lower = province.lower()
        TARGET_PROVINCES = ["สงขลา", "songkhla"]
        if not any(target in province_lower for target in TARGET_PROVINCES):
            continue

        vals = d.get("values", {})
        raw_water_level = vals.get("water_level")
        raw_water_level_value_list = vals.get("water_level_value_list", {}).get("value")
        raw_rain_sum_now = vals.get("rain_sum_now")
        raw_rain_sum = vals.get("rain_sum")

        # 1. Extract and format date/time
        unixtime = None
        if raw_water_level:
            unixtime = raw_water_level.get("unixtime")
        if not unixtime and raw_rain_sum_now:
            unixtime = raw_rain_sum_now.get("unixtime")

        if isinstance(unixtime, list):
            unixtime = unixtime[0] if unixtime else None

        if not unixtime:
            for k, v in vals.items():
                if isinstance(v, dict) and v.get("unixtime"):
                    u = v.get("unixtime")
                    if isinstance(u, list) and u:
                        unixtime = u[0]
                        break
                    elif isinstance(u, (int, float)):
                        unixtime = u
                        break

        if not isinstance(unixtime, (int, float)):
            try:
                unixtime = float(unixtime)
            except (TypeError, ValueError):
                print(f"(stn: {code}) ไม่มี timestamp ข้าม")
                continue

        tz_thailand = pytz.timezone('Asia/Bangkok')
        waterlevel_datetime = datetime.fromtimestamp(unixtime, tz=tz_thailand)

        # 2. Extract Water Level (water_level, wl_down)
        wl_up = None
        wl_down = None

        if raw_water_level_value_list and len(raw_water_level_value_list) > 0:
            wl_up = parse_water_level(raw_water_level_value_list[0], code)

        if raw_water_level_value_list and len(raw_water_level_value_list) > 1:
            wl_down = parse_water_level(raw_water_level_value_list[1], code)

        # Fallback to single water_level value for wl_up
        if wl_up is None and raw_water_level:
            wl_up = parse_water_level(raw_water_level.get("value"), code)

        # 3. Extract Rainfall (เฉพาะสถานีที่มีเครื่องวัดฝน)
        has_rain_gauge = (d.get("measure") or {}).get("r", True)

        rain_now = None
        rain_now_datetime = None
        if has_rain_gauge and raw_rain_sum_now:
            rain_now = parse_rain(raw_rain_sum_now.get("value"))
            rain_now_unixtime = first_unixtime(raw_rain_sum_now.get("unixtime"))
            if rain_now is not None and rain_now_unixtime:
                rain_now_datetime = datetime.fromtimestamp(rain_now_unixtime, tz=TZ_THAILAND)
            else:
                rain_now = None

        rain_24h = None
        rain_24h_datetime = None
        if has_rain_gauge and raw_rain_sum:
            rain_sum_values = raw_rain_sum.get("value") or []
            rain_sum_unixtime = first_unixtime(raw_rain_sum.get("unixtime"))
            # unixtime ของ rain_sum คือเวลาที่ server สร้าง snapshot ไม่ใช่เวลาที่สถานีส่งข้อมูล
            # ถ้าสถานีส่งข้อมูลล่าสุดก่อนปิดรอบ 07:00 แปลว่ารอบนั้นข้อมูลไม่ครบ ไม่บันทึก
            last_reading_unixtime = first_unixtime((raw_rain_sum_now or {}).get("unixtime"))
            if rain_sum_values and rain_sum_unixtime:
                # ประทับเวลาที่ปลายรอบ (07:00) ค่าเดิมจะได้ไม่ถูกบันทึกซ้ำทุกรอบที่รัน
                day_end = rain_day_end(rain_sum_unixtime)
                if last_reading_unixtime and last_reading_unixtime >= day_end.timestamp():
                    rain_24h = parse_rain(rain_sum_values[0])
                    rain_24h_datetime = day_end
                else:
                    print(f"(stn: {code}) ไม่มีข้อมูลหลัง {day_end.isoformat()} ฝน 24 ชม. ไม่ครบรอบ ข้าม")

        # 4. Clean cross_section (remove gauge)
        cross_section = d.get("cross_section")
        if cross_section:
            for cs in cross_section:
                cs.pop("gauge", None)

        # 5. Extract water_level_warning and water_level_critical
        water_level_warning = d.get("water_level_warning")
        if water_level_warning is not None and water_level_warning != "-":
            try:
                water_level_warning = float(water_level_warning)
            except ValueError:
                water_level_warning = None
        else:
            water_level_warning = None

        water_level_critical = d.get("water_level_critical")
        if water_level_critical is not None and water_level_critical != "-":
            try:
                water_level_critical = float(water_level_critical)
            except ValueError:
                water_level_critical = None
        else:
            water_level_critical = None

        # 6. Calculate diff_wl_bank
        diff_wl_bank = None
        if wl_up is not None and water_level_critical is not None:
            diff_wl_bank = wl_up - water_level_critical

        # 7. Gather metrics and metadata
        attribute_outputs = []

        if wl_up is not None or diff_wl_bank is not None:
            attribute_outputs.append({
                "code": code,
                "source": "rid",
                "datetime": waterlevel_datetime.isoformat(),
                "waterlevel": wl_up,
                "diff_wl_bank": diff_wl_bank,
            })

        if rain_now is not None:
            attribute_outputs.append({
                "code": code,
                "source": "rid",
                "datetime": rain_now_datetime.isoformat(),
                "rain": rain_now,
            })

        if rain_24h is not None:
            attribute_outputs.append({
                "code": code,
                "source": "rid",
                "datetime": rain_24h_datetime.isoformat(),
                "rain_24h": rain_24h,
            })

        if attribute_outputs:
            metric_outputs[code] = attribute_outputs

    print(f"\nTotal stations processed:", len(metric_outputs))

    return metric_outputs
