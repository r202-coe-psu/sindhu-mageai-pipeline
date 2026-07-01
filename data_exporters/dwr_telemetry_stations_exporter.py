import asyncio
import datetime
import nest_asyncio

from sindhu import models

nest_asyncio.apply()

if "data_exporter" not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

SOURCE = "dwr_telemetry"


async def insert_data(stations):
    print("### Initialize Beanie")
    await models.init_default_beanie_client()

    stations_to_insert = []

    inserted = 0
    updated = 0
    skipped = 0

    now = datetime.datetime.now(datetime.timezone.utc)

    print("### Start insert data")

    for _, station_list in stations.items():

        for raw in station_list:

            data = raw.copy()

            name = data.get("name")
            name_th = data.get("name_th")
            code = data.get("code")

            # ใช้ source เดียวทั้งระบบ
            source = SOURCE

            url = data.get("url")
            status = data.get("status", "active")

            lat = data.get("lat")
            lon = data.get("lon")

            metadata = data.get("metadata", {})

            coordinates = {
                "type": "Point",
                "coordinates": [
                    lon or 0.0,
                    lat or 0.0,
                ],
            }

            existing = (
                await models.Station.find(
                    models.Station.code == code,
                    models.Station.source == source,
                )
                .sort(-models.Station.updated_date)
                .first_or_none()
            )

            if existing:

                changed = False

                updates = {
                    "name": name or existing.name,
                    "name_th": name_th or existing.name_th,
                    "url": url,
                    "station_metadata": metadata,
                    "coordinates": coordinates,
                    "status": status,
                }

                for field, value in updates.items():
                    if getattr(existing, field) != value:
                        setattr(existing, field, value)
                        changed = True

                if changed:
                    existing.updated_date = now

                    print(
                        f"[>] Updating station ({code}) {name_th}"
                    )

                    await existing.save()
                    updated += 1

                else:
                    print(
                        f"[=] Skip unchanged ({code}) {name_th}"
                    )

                    skipped += 1

                continue

            print(
                f"[+] New Station ({code}) {name_th}"
            )

            stations_to_insert.append(
                models.Station(
                    name=name or code,
                    name_th=name_th,
                    code=code,
                    source=source,
                    url=url,
                    station_metadata=metadata,
                    coordinates=coordinates,
                    status=status,
                    created_date=now,
                    updated_date=now,
                )
            )

        # batch insert
        if stations_to_insert:
            await models.Station.insert_many(
                stations_to_insert
            )

            inserted += len(stations_to_insert)
            stations_to_insert.clear()

    print("")
    print("### Done Summary")
    print(f"Inserted : {inserted}")
    print(f"Updated  : {updated}")
    print(f"Skipped  : {skipped}")


@data_exporter
def export_data_to_mongodb(stations, **kwargs):
    asyncio.run(insert_data(stations))
    print("### Done Process")
