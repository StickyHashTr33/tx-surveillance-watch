import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

urls = [
    ("BidNetDirect closed", "https://www.bidnetdirect.com/texas/bexar-county/solicitations/closed-bids"),
    ("CivicEngage",         "https://www.bexar.org/Bids.aspx"),
]

for label, url in urls:
    r = requests.get(url, headers=headers, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select("tr, li, .bid-item")
    print(f"--- {label} ---")
    print(f"  Status: {r.status_code}")
    print(f"  Rows found: {len(rows)}")
    print(f"  Text snippet:\n{soup.get_text()[400:700].strip()}")
    print()