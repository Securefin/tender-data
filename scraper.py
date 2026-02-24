import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import hashlib

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

IGNORE = ['corrigendum', 'cancelled', 'extension']

# ======================================================
# MAHATENDERS SCRAPER (Public listing pages)
# ======================================================

MAHA_URLS = [
    "https://mahatenders.gov.in/nicgep/app?page=FrontEndTendersByOrganisation&service=page",
    "https://mahatenders.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page"
]

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

def fetch_mahatenders():
    tenders = []
    seen = set()

    for url in MAHA_URLS:
        try:
            print("Fetching:", url)
            r = requests.get(url, headers=HEADERS, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")

            links = soup.find_all("a")

            for a in links:
                title = a.text.strip()

                if len(title) < 15:
                    continue

                title_lower = title.lower()

                if any(w in title_lower for w in IGNORE):
                    continue

                if title in seen:
                    continue
                seen.add(title)

                link = a.get("href")
                if link and not link.startswith("http"):
                    link = "https://mahatenders.gov.in" + link

                pub = datetime.now()
                expiry = pub + timedelta(days=15)

                tenders.append({
                    "id": hashlib.md5(title.encode()).hexdigest(),
                    "title": title,
                    "link": link or "https://mahatenders.gov.in",
                    "category": get_category(title),
                    "location": get_location(title),
                    "published": pub.strftime("%Y-%m-%d"),
                    "expiry": expiry.strftime("%Y-%m-%d"),
                    "summary": f"{get_location(title)} me {get_category(title)} ka tender jari hua hai."
                })

        except Exception as e:
            print("Error:", e)

    return tenders

# ======================================================
# FALLBACK RSS (if portal returns low data)
# ======================================================

def fallback_rss():
    print("Using fallback RSS...")
    RSS = "https://news.google.com/rss/search?q=mahatenders.gov.in+tender&hl=en-IN&gl=IN&ceid=IN:en"
    tenders = []

    try:
        import xml.etree.ElementTree as ET
        r = requests.get(RSS, timeout=30)
        root = ET.fromstring(r.content)
        items = root.findall(".//item")

        for it in items[:10]:
            title = it.find("title").text.split(" - ")[0]
            link = it.find("link").text

            pub = datetime.now()
            expiry = pub + timedelta(days=15)

            tenders.append({
                "id": hashlib.md5(title.encode()).hexdigest(),
                "title": title,
                "link": link,
                "category": get_category(title),
                "location": get_location(title),
                "published": pub.strftime("%Y-%m-%d"),
                "expiry": expiry.strftime("%Y-%m-%d"),
                "summary": f"{get_location(title)} me {get_category(title)} ka tender jari hua hai."
            })

    except:
        pass

    return tenders

# ======================================================
# MAIN
# ======================================================

print("Starting real tender scrape...")

data = fetch_mahatenders()

# If portal blocked / low results
if len(data) < 5:
    print("Low data, using fallback...")
    data = fallback_rss()

print("Final tenders:", len(data))

output = {
    "updated": datetime.now().strftime("%d %b %Y %H:%M"),
    "total": len(data),
    "data": data
}

with open("tenders.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("tenders.json created")
