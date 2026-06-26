import datetime
from typing import List
import asyncio
import bson

from sindhu import models
from sindhu.schemas import bases

if "data_exporter" not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

PROVINCE = "Songkhla"

async def insert_data(stations):
    print("### Initialize Beanie")
    await models.init_default_beanie_client()

    stations_to_save = []
    print("### Start insert data")
    
    for code, station in stations.items():
        for data in station:  # ย้ายกระบวนการจัดการข้อมูลเข้ามาทำใน Inner Loop ทั้งหมด
            name = data.pop("name", None)
            name_th = data.pop("name_th", None)
            station_code = data.pop("code", None)
            source = data.pop("source", None)
            url = data.pop("url", None)
            station_type = data.pop("station_type", None)
            longitude = data.pop("longitude", None)
            latitude = data.pop("latitude", None)
            
            created_date = datetime.datetime.now(datetime.timezone.utc)
            updated_date = datetime.datetime.now(datetime.timezone.utc)

            # metadata
            tumbon_code = data.pop("tumbon_code", None)
            tumbon_name_en = data.pop("tumbon_name_en", None)
            tumbon_name_th = data.pop("tumbon_name_th", None)

            amphoe_code = data.pop("amphoe_code", None)
            amphoe_name_en = data.pop("amphoe_name_en", None)
            amphoe_name_th = data.pop("amphoe_name_th", None)

            province_code = data.pop("province_code", None)
            province_name_en = data.pop("province_name_en", None)
            province_name_th = data.pop("province_name_th", None)
            
            water_level_critical = data.pop("water_level_critical", None)
            water_level_warning = data.pop("water_level_warning", None)

            # Filtering is already handled in Transformer

            metadata = dict(
                tumbon_code=tumbon_code,
                tumbon_name_en=tumbon_name_en,
                tumbon_name_th=tumbon_name_th,
                amphoe_code=amphoe_code,
                amphoe_name_en=amphoe_name_en,
                amphoe_name_th=amphoe_name_th,
                province_code=province_code,
                province_name_en=province_name_en,
                province_name_th=province_name_th,
                water_level_critical=water_level_critical,
                water_level_warning=water_level_warning,
            )

            # ตรวจสอบสถานีเดิมในระบบจาก code และ source
            exists_name_th_station = (
                await models.Station.find(
                    models.Station.code == station_code,
                    models.Station.source == source,
                )
                .sort(-models.Station.updated_date)
                .first_or_none()
            )
            
            if exists_name_th_station:
                print(f"[>] Updating station ({station_code}) {name_th}")
                exists_name_th_station.name = name
                exists_name_th_station.name_th = name_th
                exists_name_th_station.code = station_code
                exists_name_th_station.source = source
                exists_name_th_station.url = url
                exists_name_th_station.metadata = metadata
                exists_name_th_station.coordinates = bases.GeoObject(
                    coordinates=[longitude, latitude]
                )
                exists_name_th_station.status = "active"
                exists_name_th_station.updated_date = datetime.datetime.now(
                    datetime.timezone.utc
                )
                await exists_name_th_station.save()
                continue  # อัปเดตเสร็จแล้ว ข้ามไปประมวลผลข้อมูลตัวถัดไป

            # กรณีเป็นสถานีใหม่
            print(f"[+] New Station ({station_code}) {name_th}")
            station_model = models.Station(
                name=name,
                name_th=name_th,
                code=station_code,
                source=source,
                url=url,
                metadata=metadata,
                coordinates=bases.GeoObject(coordinates=[longitude, latitude]),
                created_date=created_date,
                updated_date=updated_date,
                status="active",
            )

            stations_to_save.append(station_model)

    # บันทึกสถานีใหม่ทั้งหมดเข้า MongoDB แบบรอบเดียว (Bulk Insert)
    if stations_to_save:
        await models.Station.insert_many(stations_to_save)

    print("### Success insert data:", len(stations_to_save))


@data_exporter
def export_data_to_mongodb(stations, **kwargs) -> None:
    asyncio.run(insert_data(stations))
    print("### Done Process")