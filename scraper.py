import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
import hashlib

SEARCH = '"Maharashtra" OR "Mumbai" OR "Pune" OR "Nagpur"'
URL = f"https://news.google.com/rss/search?q=site:mahatenders.gov.in {SEARCH}&hl=en-IN&gl=IN&ceid=IN:en"

IGNORE = ['corrigendum','cancelled','extension']

def clean_date(pub):
    try:
        return datetime.strptime(pub[:16], "%a, %d %b %Y")
    except:
        return datetime.now()

def cat(title):
    t = title.lower()
    if 'road' in t or 'civil' in t: return "Civil"
    if 'electric' in t: return "Electrical"
    if 'vehicle' in t: return "Transport"
    return "General"

def loc(title):
    t = title.lower()
    if 'mumbai' in t: return "Mumbai"
    if 'pune' in t: return "Pune"
    if 'nagpur' in t: return "Nagpur"
    return "Maharashtra"

print("Fetching tenders...")

r = requests.get(URL, timeout=30)
root = ET.fromstring(r.content)
items = root.findall(".//item")

data = []

for it in items:
    title = it.find("title").text.split(" - ")[0]
    link = it.find("link").text
    pub = it.find("pubDate").text

    if any(w in title.lower() for w in IGNORE):
        continue

    pub_dt = clean_date(pub)
    expiry = pub_dt + timedelta(days=15)

    data.append({
        "id": hashlib.md5(title.encode()).hexdigest(),
        "title": title,
        "link": link,
        "category": cat(title),
        "location": loc(title),
        "expiry": expiry.strftime("%Y-%m-%d"),
        "summary": f"{loc(title)} me {cat(title)} ka tender jari hua hai."
    })

print("Total:", len(data))

out = {
    "updated": datetime.now().strftime("%d %b %Y %H:%M"),
    "total": len(data),
    "data": data
}

with open("tenders.json","w",encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print("Done.")
