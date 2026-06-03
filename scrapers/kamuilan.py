import requests
import warnings
from bs4 import BeautifulSoup
from db import make_hash

warnings.filterwarnings("ignore")

BASE_URL = "https://kamuilan.sbb.gov.tr"
LIST_URL = f"{BASE_URL}/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def _parse_employment_type(text: str) -> str:
    t = text.lower()
    if "memur" in t:
        return "Memur"
    if "sözleşmeli" in t or "sozlesmeli" in t:
        return "Sözleşmeli"
    if "işçi" in t or "isci" in t:
        return "Sürekli İşçi"
    if "öğretim" in t or "akademik" in t or "araştırma" in t:
        return "Akademik"
    return ""

def scrape() -> list[dict]:
    jobs = []
    try:
        resp = requests.get(LIST_URL, headers=HEADERS, timeout=15, verify=False)
        soup = BeautifulSoup(resp.content, "lxml")
        cards = soup.select("a[href*='ilanDetay']")

        for card in cards:
            try:
                href = card.get("href", "")
                url = f"{BASE_URL}/{href}" if not href.startswith("http") else href

                organization = ""
                title = ""
                deadline = ""

                # Format 1: span.black / span.patrol / span.h5date
                black = card.select_one("span.black")
                patrol = card.select_one("span.patrol")
                date1 = card.select_one("span.h5date")

                # Format 2: p.alt_p1 / p.alt_p2 / em
                alt1 = card.select_one("p.alt_p1")
                alt2 = card.select_one("p.alt_p2")
                em = card.select_one("p.alt_p2 em")

                if black and patrol:
                    organization = black.get_text(strip=True)
                    title = patrol.get_text(strip=True)
                    deadline = date1.get_text(strip=True) if date1 else ""
                elif alt1 and alt2:
                    organization = alt1.get_text(strip=True)
                    # deadline em içinde, title = em dışındaki metin
                    if em:
                        deadline = em.get_text(strip=True).strip("()")
                        title = alt2.get_text(strip=True).replace(em.get_text(strip=True), "").strip()
                    else:
                        title = alt2.get_text(strip=True)
                else:
                    continue

                if not organization and not title:
                    continue

                employment_type = _parse_employment_type(title)
                hash_val = make_hash(title, organization, deadline)

                jobs.append({
                    "source": "kamuilan",
                    "title": title,
                    "organization": organization,
                    "city": "",
                    "employment_type": employment_type,
                    "application_deadline": deadline,
                    "url": url,
                    "hash": hash_val
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[kamuilan] Hata: {e}")

    return jobs
