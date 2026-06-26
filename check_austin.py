import requests

resp = requests.get(
    "https://data.austintexas.gov/resource/cnaj-c72e.json",
    params={"$limit": 3},
    timeout=20
)
print("Status:", resp.status_code)
print(resp.text[:500])