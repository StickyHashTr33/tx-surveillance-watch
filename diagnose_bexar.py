import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

# ── BidNetDirect ──────────────────────────────────────────────────────────────
print("=== BIDNETDIRECT ===")
r = requests.get(
    "https://www.bidnetdirect.com/texas/bexar-county/solicitations/closed-bids",
    headers=headers, timeout=20
)
soup = BeautifulSoup(r.text, "html.parser")

# Print every unique class name that appears on <tr>, <li>, <div> elements
# so we can find the real bid container selector
classes = set()
for tag in soup.find_all(["tr", "li", "div", "article"]):
    for c in tag.get("class", []):
        classes.add(c)
print("Classes found:", sorted(classes)[:40])
print()

# Print first 5 <tr> that have meaningful text (more than 30 chars)
print("First 5 meaningful <tr> rows:")
count = 0
for row in soup.find_all("tr"):
    text = row.get_text(separator=" ", strip=True)
    if len(text) > 30 and count < 5:
        print(f"  [{count}] {text[:150]}")
        count += 1

print()

# ── CivicEngage ───────────────────────────────────────────────────────────────
print("=== CIVICENGAGE (bexar.org) ===")
r2 = requests.get("https://www.bexar.org/Bids.aspx", headers=headers, timeout=20)
soup2 = BeautifulSoup(r2.text, "html.parser")

classes2 = set()
for tag in soup2.find_all(["tr", "li", "div"]):
    for c in tag.get("class", []):
        classes2.add(c)
print("Classes found:", sorted(classes2)[:40])
print()

print("First 5 meaningful <tr> rows:")
count = 0
for row in soup2.find_all("tr"):
    text = row.get_text(separator=" ", strip=True)
    if len(text) > 30 and count < 5:
        print(f"  [{count}] {text[:150]}")
        count += 1