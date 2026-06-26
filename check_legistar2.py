import requests
from datetime import datetime, timedelta, timezone

BASE = "https://webapi.legistar.com/v1"

now   = datetime.now(timezone.utc)
start = (now - timedelta(days=14)).strftime("%Y-%m-%d")
end   = (now + timedelta(days=14)).strftime("%Y-%m-%d")

print(f"Date range: {start} to {end}")
print()

for client in ["sanantonio", "austintexas"]:
    print(f"=== {client} ===")

    # Try the exact filter we're using
    filter_str = f"EventDate ge datetime'{start}' and EventDate le datetime'{end}'"
    print(f"Filter: {filter_str}")

    r = requests.get(
        f"{BASE}/{client}/events",
        params={"$filter": filter_str, "$top": 5, "$orderby": "EventDate desc"},
        timeout=20
    )
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:400]}")
    print()

    # Also try without orderby
    r2 = requests.get(
        f"{BASE}/{client}/events",
        params={"$filter": filter_str, "$top": 5},
        timeout=20
    )
    print(f"Without orderby - Status: {r2.status_code}")
    print(f"Response: {r2.text[:400]}")
    print()