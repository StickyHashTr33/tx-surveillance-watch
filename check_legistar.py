import requests

BASE = "https://webapi.legistar.com/v1"

for client in ["sanantonio", "austintexas"]:
    print(f"\n=== {client} ===")

    # Test 1: no filter, just get any events
    r = requests.get(f"{BASE}/{client}/events", params={"$top": 2}, timeout=20)
    print(f"Events (no filter): {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"  Count: {len(data)}")
        if data:
            print(f"  First event date: {data[0].get('EventDate')}")
            print(f"  First event body: {data[0].get('EventBodyName')}")
    else:
        print(f"  Error: {r.text[:200]}")

    # Test 2: try bodies endpoint to confirm client name works
    r2 = requests.get(f"{BASE}/{client}/bodies", params={"$top": 2}, timeout=20)
    print(f"Bodies endpoint: {r2.status_code}")
    if r2.status_code == 200:
        data2 = r2.json()
        if data2:
            print(f"  First body: {data2[0].get('BodyName')}")
    else:
        print(f"  Error: {r2.text[:200]}")