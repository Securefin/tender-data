import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import hashlib
import xml.etree.ElementTree as ET

HEADERS = {"User-Agent": "Mozilla/5.0"}
IGNORE = ['corrigendum', 'cancelled', 'extension']

# ================= DISTRICT ENGINE =================
DISTRICTS = {
    "Mumbai": ["mumbai", "bmc"],
    "Pune": ["pune", "pcmc"],
    "Nagpur": ["nagpur"],
    "Nashik": ["nashik"],
    "Thane": ["thane"],
    "Ratnagiri": ["ratnagiri", "dapoli", "chiplun"]
}

def detect_district(text):
    t = text.lower()
    for d, keys in DISTRICTS.items():
        if any(k in t for k in keys):
            return d
    return "Other"

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

# ================= FREE AI SUMMARY =================
def ai_summary(title, category, district):
    return f"{district} me {category} se related ek naya tender jari hua hai. Contractors apply kar sakte hain."

# ================= MAHATENDERS =================
def scrape_mahatenders():
    urls = [
        "https://mahatenders.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page"
    ]

    tenders = []
    seen = set()

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")

            for a in soup.find_all("a"):
                title = a.text.strip()
                if len(title) < 15:
                    continue

                if any(w in title.lower() for w in IGNORE):
                    continue

                if title in seen:
                    continue
                seen.add(title)

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
        lines = r.text.split("\n")

        for line in lines:
            if "bid no" in line.lower():
                title = line.strip()
                tenders.append((title, "https://gem.gov.in", "GeM"))
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
        items = root.findall(".//item")

        for it in items[:20]:
            title = it.find("title").text.split(" - ")[0]
            link = it.find("link").text
            tenders.append((title, link, "RSS"))
    except:
        pass

    return tenders

# ================= MASTER AGGREGATOR =================
print("Fetching tenders...")

raw = []
raw += scrape_mahatenders()
raw += scrape_gem()

if len(raw) < 10:
    raw += scrape_rss()

print("Raw tenders:", len(raw))

# ================= CLEAN + BUILD =================
data = []
seen_ids = set()

for title, link, source in raw:
    tid = hashlib.md5(title.encode()).hexdigest()
    if tid in seen_ids:
        continue
    seen_ids.add(tid)

    category = get_category(title)
    district = detect_district(title)
    pub = datetime.now()
    expiry = pub + timedelta(days=15)

    data.append({
        "id": tid,
        "title": title,
        "link": link,
        "source": source,
        "category": category,
        "location": "India",
        "district": district,
        "published": pub.strftime("%Y-%m-%d"),
        "expiry": expiry.strftime("%Y-%m-%d"),
        "summary": ai_summary(title, category, district)
    })

print("Clean tenders:", len(data))

# ================= OUTPUT =================
output = {
    "updated": datetime.now().strftime("%d %b %Y %H:%M"),
    "total": len(data),
    "data": data
}

with open("tenders.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("tenders.json generated")
