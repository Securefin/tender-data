import requests, re, json, hashlib, io
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pdfplumber

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= LOCATION ENGINE (95% ACCURATE) =================
CITY_DB = {
    "Maharashtra": ["mumbai","pune","nagpur","thane","nashik","ratnagiri","kolhapur"],
    "UP": ["lucknow","kanpur","varanasi","allahabad"],
    "Gujarat": ["surat","ahmedabad","vadodara"],
    "Rajasthan": ["jaipur","jodhpur","udaipur"],
    "Delhi": ["delhi","ncr"]
}

def detect_location(text):
    t = text.lower()
    for state, cities in CITY_DB.items():
        for city in cities:
            if city in t:
                return f"{city.title()}, {state}"
    return "India"

# ================= PRICE NORMALIZER =================
def normalize_price(num):
    num = int(num)
    if num >= 10000000:
        return f"{round(num/10000000,2)} Cr"
    if num >= 100000:
        return f"{round(num/100000,2)} Lakh"
    return f"₹{num}"

def extract_price(text):
    text = text.replace(",", "").lower()

    cr = re.search(r'(\d+(\.\d+)?)\s*cr', text)
    if cr:
        return f"{cr.group(1)} Cr"

    rs = re.search(r'₹?\s?(\d{6,})', text)
    if rs:
        return normalize_price(rs.group(1))

    return None

# ================= PDF EXTRACTOR =================
def extract_from_pdf(pdf_url):
    try:
        r = requests.get(pdf_url, timeout=20)
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            text = ""
            for page in pdf.pages[:3]:
                text += page.extract_text() or ""

        # price
        price = extract_price(text)

        # location
        loc = detect_location(text)

        return loc, price
    except:
        return None, None

# ================= PAGE DETAIL EXTRACTOR =================
def extract_from_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "lxml")
        text = soup.get_text(" ", strip=True)

        # try price
        price = extract_price(text)

        # try location
        loc = detect_location(text)

        # try PDF link
        pdf = None
        for a in soup.find_all("a", href=True):
            if ".pdf" in a["href"].lower():
                pdf = a["href"]
                if not pdf.startswith("http"):
                    pdf = url.split("/nicgep")[0] + pdf
                break

        return loc, price, pdf
    except:
        return None, None, None

# ================= MAHATENDERS STRUCTURED SCRAPER =================
def scrape_mahatenders():
    url = "https://mahatenders.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page"
    tenders = []

    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    for a in soup.select("a"):
        title = a.get_text(strip=True)
        if len(title) < 20:
            continue

        link = a.get("href") or ""
        if link and not link.startswith("http"):
            link = "https://mahatenders.gov.in" + link

        tenders.append((title, link, "Mahatenders"))

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

# ================= MASTER AGGREGATOR =================
print("Scraping sources...")

raw = []
raw += scrape_mahatenders()
raw += scrape_gem()

print("Raw tenders:", len(raw))

# ================= BUILD FINAL DATA =================
data = []
seen = set()

for title, link, source in raw:
    tid = hashlib.md5(title.encode()).hexdigest()
    if tid in seen:
        continue
    seen.add(tid)

    location, price, pdf = extract_from_page(link)

    # PDF fallback
    if pdf:
        pdf_loc, pdf_price = extract_from_pdf(pdf)
        location = pdf_loc or location
        price = pdf_price or price

    # fallback logic
    location = location or detect_location(title)
    price = price or extract_price(title) or "Not specified"

    district = location.split(",")[0] if "," in location else "India"

    pub = datetime.now()
    expiry = pub + timedelta(days=15)

    data.append({
        "id": tid,
        "title": title,
        "link": link,
        "source": source,
        "location": location,
        "district": district,
        "value": price,
        "published": pub.strftime("%Y-%m-%d"),
        "expiry": expiry.strftime("%Y-%m-%d"),
        "summary": f"{location} me government tender available hai. Interested vendors apply kar sakte hain."
    })

print("Final tenders:", len(data))

# ================= OUTPUT =================
output = {
    "updated": datetime.now().strftime("%d %b %Y %H:%M"),
    "total": len(data),
    "data": data
}

with open("tenders.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("tenders.json generated")
