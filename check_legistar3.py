import requests

BASE = "https://webapi.legistar.com/v1"

for client in ["sanantonio", "austintexas"]:
    print(f"=== {client} ===")

    # Get most recent events first
    r = requests.get(
        f"{BASE}/{client}/events",
        params={"$orderby": "EventDate desc", "$top": 5},
        timeout=20
    )
    data = r.json()
    print(f"Most recent events ({len(data)} returned):")
    for e in data:
        print(f"  {e.get('EventDate','')[:10]}  {e.get('EventBodyName','')}")

    # Get count of all events
    r2 = requests.get(
        f"{BASE}/{client}/events",
        params={"$inlinecount": "allpages", "$top": 1},
        timeout=20
    )
    print(f"Raw count response: {r2.text[:200]}")
    print()