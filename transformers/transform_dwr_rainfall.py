if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@transformer
def transform(data, *args, **kwargs):
    print("### เริ่มต้นกระบวนการประมวลผลข้อมูลน้ำฝน DWR")
    metric_outputs = dict()
    
    for i, d in enumerate(data):
        station_info = d.get("station", {})
        station_code = station_info.get("stationCode")
        
        # กรองเฉพาะสถานีที่อยู่ในลุ่มน้ำทะเลสาบสงขลา (TA20)
        if not station_code or "TA20" not in station_code:
            continue
            
        results = d.get("measurementResults", [])
        if not results:
            continue
            
        res = results[0]
        # เลือกเฉพาะบันทึกข้อมูลน้ำฝน (Rainfall) เท่านั้น
        if res.get("variable") != "Rainfall":
            continue
            
        measure_time = res.get("measureTime")
        rain_val = res.get("value")

        # ตรวจสอบความถูกต้องว่ามีข้อมูลอยู่จริง
        if not measure_time or rain_val is None:
            continue

        # Normalize timestamp (DWR may return ISO 8601 with trailing 'Z')
        if isinstance(measure_time, str) and measure_time.endswith("Z"):
            measure_time = measure_time[:-1] + "+00:00"

        try:
            rain_float = float(rain_val)
        except (TypeError, ValueError):
            continue

        code = str(station_code).strip()

        record = {
            "code": code,
            "name_th": station_info.get("stationName", ""),
            "source": "dwr",
            "waterlevel_datetime": measure_time,
            "rain": rain_float,
        }
        
        metric_outputs.setdefault(code, []).append(record)
        
    print(f"รวมสถานีโทรมาตรสงขลาที่จับคู่ข้อมูลแล้ว: {len(metric_outputs)}")
    return metric_outputs


@test
def test_output(output, *args) -> None:
    assert output is not None, 'ผลลัพธ์ (Output) ไม่ได้ถูกกำหนดไว้ (เป็น Undefined)'
    assert isinstance(output, dict), 'ผลลัพธ์ควรจะเป็น Dictionary ที่จัดกลุ่มตามรหัสสถานี'