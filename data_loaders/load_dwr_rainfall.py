import requests

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@data_loader
def load_data_from_api(*args, **kwargs):
    url = "https://telemetry.dwr.go.th/api/twsApi/v1/Rainfall?latest=true&interval=C-60"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    
    print(f"Fetching data from DWR: {url}")
    response = session.get(url, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    observations = result.get("value", {}).get("timeSeriesObservation", [])
    print(f"Successfully loaded telemetry data for {len(observations)} stations.")
    return observations


@test
def test_output(output, *args) -> None:
    assert output is not None, 'The output is undefined'
    assert isinstance(output, list), 'The output should be a list of stations'
