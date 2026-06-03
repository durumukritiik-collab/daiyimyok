import requests
import warnings
from bs4 import BeautifulSoup
from db import make_hash

warnings.filterwarnings("ignore")

BASE_URL = "https://kariyerkapisi.gov.tr"
LIST_URL = f"{BASE_URL}/isealim"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def scrape() -> list[dict]:
    jobs = []
    try:
        resp = requests.get(LIST_URL, headers=HEADERS, timeout=15, verify=False)
        soup = BeautifulSoup(resp.content, "lxml")

        # İlan kartlarını farklı selector'larla dene
        cards = (
            soup.select(".ilan-card, .job-card, .position-card") or
            soup.select("article") or
            soup.select(".list-item, .ilan-item")
        )

        # Eğer kart bulamazsa linkleri tara
        if not cards:
            links = soup.select("a[href*='ilan'], a[href*='pozisyon'], a[href*='job']")
            for link in links:
                try:
                    title = link.get_text(strip=True)
                    if len(title) < 5:
                        continue
                    href = link.get("href", "")
                    url = f"{BASE_URL}{href}" if href.startswith("/") else href
                    hash_val = make_hash(title, "", "")
                    jobs.append({
                        "source": "kariyerkapisi",
                        "title": title,
                        "organization": "",
                        "city": "",
                        "employment_type": "",
                        "application_deadline": "",
                        "url": url,
                        "hash": hash_val
                    })
                except Exception:
                    continue
            return jobs

        for card in cards:
            try:
                title_el = card.select_one("h2, h3, h4, .title, .baslik")
                org_el = card.select_one(".kurum, .organization, .company")
                city_el = card.select_one(".city, .sehir, .il")
                deadline_el = card.select_one(".deadline, .tarih, .son-basvuru")
                link = card.select_one("a")

                title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:80]
                organization = org_el.get_text(strip=True) if org_el else ""
                city = city_el.get_text(strip=True) if city_el else ""
                deadline = deadline_el.get_text(strip=True) if deadline_el else ""
                href = link.get("href", "") if link else ""
                url = f"{BASE_URL}{href}" if href.startswith("/") else (href or LIST_URL)

                if not title:
                    continue

                hash_val = make_hash(title, organization, deadline)
                jobs.append({
                    "source": "kariyerkapisi",
                    "title": title,
                    "organization": organization,
                    "city": city,
                    "employment_type": "",
                    "application_deadline": deadline,
                    "url": url,
                    "hash": hash_val
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[kariyerkapisi] Hata: {e}")

    return jobs
