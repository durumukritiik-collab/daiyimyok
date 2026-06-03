import re
import requests
import warnings
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bs4 import BeautifulSoup
from db import make_hash
from city_extractor import extract_city

warnings.filterwarnings("ignore")

BASE_URL = "https://ilan.memurlar.net"
LIST_URL = f"{BASE_URL}/default.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def _parse_employment_type(text: str) -> str:
    t = text.lower()
    if "memur" in t: return "Memur"
    if "sözleşmeli" in t: return "Sözleşmeli"
    if "işçi" in t: return "Sürekli İşçi"
    if "akademik" in t or "öğretim" in t or "araştırma görevlisi" in t: return "Akademik"
    return ""

UNVAN_MAP = {
    "psikolog": "Psikolog", "hemşire": "Hemşire", "doktor": "Doktor",
    "hekim": "Hekim", "mühendis": "Mühendis", "müfettiş": "Müfettiş",
    "avukat": "Avukat", "hukuk": "Hukuk Müşaviri", "zabıta": "Zabıta",
    "itfaiye": "İtfaiye Eri", "büro": "Büro Görevlisi", "iletişim": "İletişim Görevlisi",
    "uzman-yardimcisi": "Uzman Yardımcısı", "uzman-yardımcısı": "Uzman Yardımcısı",
    "uzman": "Uzman", "mufettis": "Müfettiş", "mufettis-yardimcisi": "Müfettiş Yardımcısı",
    "denetmen": "Denetmen", "tekniker": "Tekniker", "teknisyen": "Teknisyen",
    "sekreter": "Sekreter", "tercuman": "Tercüman", "sosyal": "Sosyal Çalışmacı",
    "eczaci": "Eczacı", "diyetisyen": "Diyetisyen", "fizyoterapist": "Fizyoterapist",
    "veteriner": "Veteriner", "ogretim-uyesi": "Öğretim Üyesi",
    "ogretim-elemani": "Öğretim Elemanı", "arastirma-gorevlisi": "Araştırma Görevlisi",
    "bilisim": "Bilişim Personeli", "personel": "Personel", "memur": "Memur",
    "isci": "İşçi", "sozlesmeli": "Sözleşmeli Personel",
}

def _extract_position_from_slug(url: str) -> str:
    """URL slug'ından unvan çıkar: /ilan/85065/kamu-ihale-kurumu-10-buro-gorevlisi.html"""
    try:
        slug = url.rstrip("/").split("/")[-1].replace(".html", "")
        # Rakamları ve kurum adını çıkar, kalan = unvan
        parts = slug.split("-")
        # Rakam sonrasındaki kısım unvan
        pos_start = 0
        for i, p in enumerate(parts):
            if p.isdigit():
                pos_start = i + 1
                break

        position_parts = parts[pos_start:] if pos_start > 0 else parts
        slug_key = "-".join(position_parts[:4])

        for key, label in UNVAN_MAP.items():
            if key in slug_key:
                return label
        return ""
    except Exception:
        return ""

def scrape() -> list[dict]:
    jobs = []
    try:
        resp = requests.get(LIST_URL, headers=HEADERS, timeout=15, verify=False)
        html_text = resp.content.decode("iso-8859-9", errors="replace")
        soup = BeautifulSoup(html_text, "lxml")

        ilan_links = [
            a for a in soup.select("a[href]")
            if "/ilan/" in a.get("href", "")
            and "default" not in a.get("href", "")
            and "cok" not in a.get("href", "")
            and "kategori" not in a.get("href", "")
        ]

        seen = set()
        for link in ilan_links:
            try:
                href = link.get("href", "")
                url = f"https:{href}" if href.startswith("//") else (
                    f"{BASE_URL}{href}" if href.startswith("/") else href
                )
                if url in seen:
                    continue
                seen.add(url)

                title_el = link.select_one("h2.title")
                title = title_el.get_text(strip=True) if title_el else link.get("title", "")

                # h4 genellikle "Kurum Adı. Son başvuru tarihi X Ay Yıl" formatında
                org_el = link.select_one("h4")
                h4_text = org_el.get_text(strip=True) if org_el else ""

                # h4'ten tarihi ayır
                deadline = ""
                organization = h4_text
                tarih_match = re.search(
                    r'[Ss]on\s+ba[şs]vuru\s+tarihi\s+(.+?)(?:\.|$)',
                    h4_text
                )
                if tarih_match:
                    deadline = tarih_match.group(1).strip()
                    # organization = h4'ün tarih öncesi kısmı
                    organization = h4_text[:tarih_match.start()].strip().rstrip(".")

                # Eğer h4 temizlendiyse title'dan al
                if not organization and title:
                    organization = ""

                # Ayrı date element varsa kullan
                date_el = link.select_one(".date, .tarih, time, .deadline")
                if date_el and not deadline:
                    deadline = date_el.get_text(strip=True)

                if not title or len(title) < 5:
                    continue

                # URL slug'ından unvan çıkar
                positions = _extract_position_from_slug(url)

                employment_type = _parse_employment_type(title + " " + positions)
                hash_val = make_hash(title, organization, deadline)
                city = extract_city(organization, title)

                jobs.append({
                    "source": "memurlar",
                    "title": title,
                    "organization": organization,
                    "city": city,
                    "employment_type": employment_type,
                    "application_deadline": deadline,
                    "url": url,
                    "hash": hash_val,
                    "positions": positions,
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[memurlar] Hata: {e}")

    return jobs
