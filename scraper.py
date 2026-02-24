import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import hashlib
import xml.etree.ElementTree as ET
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}
IGNORE = ['corrigendum', 'cancelled', 'extension']

# ================= LOCATION ENGINE =================
INDIA_STATES = {
    "Maharashtra": ["mumbai","pune","nagpur","thane","nashik","ratnagiri"],
    "UP": ["lucknow","kanpur","varanasi"],
    "Delhi": ["delhi","ncr"],
    "Gujarat": ["surat","ahmedabad"],
    "Rajasthan": ["jaipur","jodhpur"]
}

def detect_location(text):
    t = text.lower()
    for state, cities in INDIA_STATES.items():
        for city in cities:
            if city in t:
                return f"{city.title()}, {state}"
    return "India"

# ================= PRICE EXTRACTOR =================
def extract_price(text):
    text = text.replace(",", "").lower()

    cr = re.search(r'(\d+(\.\d+)?)\s*cr', text)
    if cr:
        return f"{cr.group(1)} Cr"

    lk = re.search(r'(\d+(\.\d+)?)\s*lakh', text)
    if lk:
        return f"{lk.group(1)} Lakh"

    rs = re.search(r'₹?\s?(\d{5,})', text)
    if rs:
        val = int(rs.group(1))
        if val >= 10000000:
            return f"{round(val/10000000,2)} Cr"
        elif val >= 100000:
            return f"{round(val/100000,2)} Lakh"
        return f"₹{val}"

    return "Not specified"

# ================= CATEGORY =================
def get_category(title):
    t = title.lower()
    if any(k in t for k in ['road','civil','construction','building']):
        return "Civil"
    if any(k in t for k in ['electric','transformer','lighting','wiring']):
        return "Electrical"
    if any(k in t for k in ['vehicle','bus','transport']):
        return "Transport"
    if any(k in t for k in ['computer','software','it']):
        return "IT"
    return "General"

# ================= SUMMARY =================
def ai_summary(title, category, location):
    if location == "India":
        return f"India level par {category} ka ek naya tender jari hua hai."
    return f"{location} me {category} se related ek naya tender jari hua hai."

# ================= MAHATENDERS =================
def scrape_mahatenders():
    url = "https://mahatenders.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page"
    tenders = []

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a"):
            title = a.text.strip()
            if len(title) < 15:
                continue
            if any(w in title.lower() for w in IGNORE):
                continue

            link = a.get("href") or ""
            if link and not link.startswith("http"):
                link = "https://mahatenders.gov.in" + link

            tenders.append((title, link, "Mahatenders"))
    except:
        pass

    return tenders

# ================= GEM BASIC =================
def scrape_gem():
    tenders = []
    try:
        r = requests.get("https://mkp.gem.gov.in/search?q=tender", headers=HEADERS, timeout=30)
        for line in r.text.split("\n"):
            if "bid no" in line.lower():
                tenders.append((line.strip(), "https://gem.gov.in", "GeM"))
    except:
        pass
    return tenders

# ================= RSS FALLBACK =================
def scrape_rss():
    RSS = "https://news.google.com/rss/search?q=government+tender+india&hl=en-IN&gl=IN&ceid=IN:en"
    tenders = []

    try:
        r = requests.get(RSS, timeout=30)
        root = ET.fromstring(r.content)
        for it in root.findall(".//item")[:20]:
            title = it.find("title").text.split(" - ")[0]
            link = it.find("link").text
            tenders.append((title, link, "RSS"))
    except:
        pass

    return tenders

# ================= AGGREGATOR =================
print("Fetching tenders...")

raw = []
raw += scrape_mahatenders()
raw += scrape_gem()

if len(raw) < 10:
    raw += scrape_rss()

print("Raw:", len(raw))

# ================= CLEAN + BUILD =================
data = []
seen = set()

for title, link, source in raw:
    tid = hashlib.md5(title.encode()).hexdigest()
    if tid in seen:
        continue
    seen.add(tid)

    combined = title + " " + link

    location = detect_location(combined)
    district = location.split(",")[0] if "," in location else "India"
    value = extract_price(combined)
    category = get_category(title)

    pub = datetime.now()
    expiry = pub + timedelta(days=15)

    data.append({
        "id": tid,
        "title": title,
        "link": link,
        "source": source,
        "category": category,
        "location": location,
        "district": district,
        "value": value,
        "published": pub.strftime("%Y-%m-%d"),
        "expiry": expiry.strftime("%Y-%m-%d"),
        "summary": ai_summary(title, category, location)
    })

print("Clean:", len(data))

# ================= OUTPUT =================
output = {
    "updated": datetime.now().strftime("%d %b %Y %H:%M"),
    "total": len(data),
    "data": data
}

with open("tenders.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("tenders.json ready")
