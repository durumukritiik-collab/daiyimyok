import requests
from bs4 import BeautifulSoup
from db import make_hash

BASE_URL = "https://esube.iskur.gov.tr"
SEARCH_URL = f"{BASE_URL}/istihdam/AcikIsIlanAra.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
}

def _get_form_state(session: requests.Session) -> dict:
    """ASP.NET ViewState ve EventValidation değerlerini çek."""
    resp = session.get(SEARCH_URL, headers=HEADERS, timeout=15, verify=False)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    viewstate = soup.select_one("#__VIEWSTATE")
    eventval = soup.select_one("#__EVENTVALIDATION")
    viewstategen = soup.select_one("#__VIEWSTATEGENERATOR")

    return {
        "__VIEWSTATE": viewstate["value"] if viewstate else "",
        "__EVENTVALIDATION": eventval["value"] if eventval else "",
        "__VIEWSTATEGENERATOR": viewstategen["value"] if viewstategen else "",
    }

def scrape() -> list[dict]:
    jobs = []
    session = requests.Session()

    try:
        form_state = _get_form_state(session)

        # Kamu ilanlarını filtrele
        payload = {
            **form_state,
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "ctl00$ContentPlaceHolder1$ddlIsyeriTuru": "K",  # K = Kamu
            "ctl00$ContentPlaceHolder1$ddlIl": "0",           # 0 = Tüm İller
            "ctl00$ContentPlaceHolder1$ddlIlce": "0",
            "ctl00$ContentPlaceHolder1$txtMeslek": "",
            "ctl00$ContentPlaceHolder1$ddlCalismaPeriyodu": "D",  # D = Daimi
            "ctl00$ContentPlaceHolder1$ddlOgrenimDurumu": "0",
            "ctl00$ContentPlaceHolder1$btnAra": "Ara",
        }

        resp = session.post(SEARCH_URL, data=payload, headers=HEADERS, timeout=20, verify=False)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        # Sonuç tablosunu bul
        table = soup.select_one("table.grid, table#ctl00_ContentPlaceHolder1_GridView1, table[id*='Grid']")
        if not table:
            rows = soup.select("tr[class*='row'], tr[class*='Row']")
        else:
            rows = table.select("tr")[1:]  # İlk satır header

        for row in rows:
            cols = row.select("td")
            if len(cols) < 3:
                continue
            try:
                title = cols[0].get_text(strip=True)
                organization = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                city = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                deadline = cols[-1].get_text(strip=True) if cols else ""

                link = row.select_one("a")
                url = BASE_URL + link["href"] if link and link.get("href", "").startswith("/") else (link["href"] if link else SEARCH_URL)

                if not title:
                    continue

                hash_val = make_hash(title, organization, deadline)
                jobs.append({
                    "source": "iskur",
                    "title": title,
                    "organization": organization,
                    "city": city,
                    "employment_type": "Kamu",
                    "application_deadline": deadline,
                    "url": url,
                    "hash": hash_val
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[iskur] Hata: {e}")

    return jobs
