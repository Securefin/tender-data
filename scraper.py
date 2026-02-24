import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
import hashlib

# ================= RSS FEEDS (FIXED) =================
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=mahatenders.gov.in+tender&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=gem.gov.in+tender&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=government+tender+Maharashtra&hl=en-IN&gl=IN&ceid=IN:en"
]

IGNORE = ['corrigendum', 'cancelled', 'extension']

# ====================================================

def clean_date(pub):
    try:
        return datetime.strptime(pub[:16], "%a, %d %b %Y")
    except:
        return datetime.now()

def get_category(title):
    t = title.lower()
    if any(k in t for k in ['road', 'civil', 'construction', 'building']):
        return "Civil"
    if any(k in t for k in ['electric', 'transformer', 'lighting', 'wiring']):
        return "Electrical"
    if any(k in t for k in ['vehicle', 'bus', 'transport']):
        return "Transport"
    if any(k in t for k in ['computer', 'software', 'it']):
        return "IT"
    return "General"

def get_location(text):
    t = text.lower()
    if "mumbai" in t: return "Mumbai"
    if "pune" in t: return "Pune"
    if "nagpur" in t: return "Nagpur"
    if "nashik" in t: return "Nashik"
    if "thane" in t: return "Thane"
    return "Maharashtra"

print("Fetching tenders from multiple feeds...")

items = []

# ================= MULTI FEED FETCH =================
for feed in RSS_FEEDS:
    try:
        r = requests.get(feed, timeout=30)
        root = ET.fromstring(r.content)
        items += root.findall(".//item")
    except Exception as e:
        print("Feed error:", e)

print("Total raw items:", len(items))

# ====================================================

data = []
seen_titles = set()

for it in items:
    try:
        title = it.find("title").text.split(" - ")[0]
        link = it.find("link").text
        pub = it.find("pubDate").text
    except:
        continue

    title_lower = title.lower()

    # Ignore unwanted
    if any(w in title_lower for w in IGNORE):
        continue

    # Remove duplicates
    if title in seen_titles:
        continue
    seen_titles.add(title)

    pub_dt = clean_date(pub)
    expiry = pub_dt + timedelta(days=15)

    tender = {
        "id": hashlib.md5(title.encode()).hexdigest(),
        "title": title,
        "link": link,
        "category": get_category(title),
        "location": get_location(title + link),
        "published": pub_dt.strftime("%Y-%m-%d"),
        "expiry": expiry.strftime("%Y-%m-%d"),
        "summary": f"{get_location(title)} me {get_category(title)} ka tender jari hua hai."
    }

    data.append(tender)

print("Clean tenders:", len(data))

# ================= JSON OUTPUT =================
output = {
    "updated": datetime.now().strftime("%d %b %Y %H:%M"),
    "total": len(data),
    "data": data
}

with open("tenders.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("tenders.json generated successfully")
