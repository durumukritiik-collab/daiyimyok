"""
Yeni ilan DB'ye girince bu modül çalışır:
  1. PDF'i indir
  2. Regex + tablo ile temel alanları çıkar
  3. Eksik varsa Groq doldursun
  4. Groq pozisyon listesini çıkarsın
  5. Arama etiketlerini oluştur
  6. Hepsini DB'ye kaydet

Kullanım (main.py içinden):
  from ilan_processor import process_job
  process_job(job_id, url, title, org)
"""

import io
import json
import time
import warnings

import pdfplumber
import requests

from llm_parser import groq_analiz, groq_etiket_cıkar, llm_parse_if_needed
from pdf_parser import parse_pdf_text, parse_pdf_tables

warnings.filterwarnings("ignore")

_SESSION = None


def _get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = "Mozilla/5.0"
        try:
            _SESSION.get("https://kamuilan.sbb.gov.tr/", verify=False, timeout=10)
        except Exception:
            pass
    return _SESSION


def _pdf_indir(url: str) -> bytes | None:
    """PDF'i indir, bytes döndür. Başarısız olursa None."""
    try:
        r = _get_session().get(
            url, verify=False, timeout=20,
            headers={"Referer": "https://kamuilan.sbb.gov.tr/"}
        )
        content = r.content
        # Bazı sunucular PDF'den önce binary prefix gönderiyor
        pdf_start = content.find(b"%PDF")
        if pdf_start > 0:
            content = content[pdf_start:]
        if content[:4] == b"%PDF":
            return content
    except Exception:
        pass
    return None


def process_job(job_id: str, url: str, title: str = "", org: str = "") -> bool:
    """
    Bir ilanı tam analiz et ve DB'ye kaydet.
    True → başarılı, False → PDF bulunamadı/okunamadı
    """
    print(f"  [Analiz] {org[:40]} — {title[:40]}")

    # 1) PDF indir
    pdf_bytes = _pdf_indir(url)
    if not pdf_bytes:
        print(f"  [Analiz] PDF bulunamadı, atlandı")
        return False

    # 2) Metin çıkar
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            metin = " ".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        print(f"  [Analiz] PDF okunamadı: {e}")
        return False

    if len(metin) < 100:
        print(f"  [Analiz] PDF boş")
        return False

    # 3) Regex + tablo ile temel alanlar
    tablo = parse_pdf_tables(pdf_bytes)
    alanlar = parse_pdf_text(metin)
    for k in ["mezuniyet", "mezuniyet_seviyesi", "yas_siniri", "tecrube", "kontenjan"]:
        if tablo.get(k):
            alanlar[k] = tablo[k]

    # 4) Eksik kritik alanları Groq ile doldur (hızlı model)
    alanlar = llm_parse_if_needed(alanlar, metin)

    # 5) Pozisyon listesini Groq ile çıkar (akıllı model)
    time.sleep(2)
    pozisyonlar = []
    analiz = groq_analiz(metin)
    if analiz and analiz.get("pozisyonlar"):
        pozisyonlar = analiz["pozisyonlar"]
        print(f"  [Analiz] {len(pozisyonlar)} pozisyon bulundu")

    # 6) Arama etiketleri
    time.sleep(2)
    etiketler = groq_etiket_cıkar(metin)

    # 7) DB'ye kaydet (SQLite + Supabase)
    from db import update_job_fields
    update_job_fields(job_id, {
        "mezuniyet":          alanlar.get("mezuniyet", ""),
        "kpss_sart":          alanlar.get("kpss_sart", ""),
        "kpss_puan":          alanlar.get("kpss_puan", ""),
        "yas_siniri":         alanlar.get("yas_siniri", ""),
        "kontenjan":          alanlar.get("kontenjan", ""),
        "basvuru_sekli":      alanlar.get("basvuru_sekli", ""),
        "tecrube":            alanlar.get("tecrube", ""),
        "mezuniyet_seviyesi": alanlar.get("mezuniyet_seviyesi", ""),
        "sinav_tarihi":       alanlar.get("sinav_tarihi", ""),
        "pdf_text":           metin[:50000],
        "arama_etiketleri":   etiketler,
        "pozisyonlar_json":   json.dumps(pozisyonlar, ensure_ascii=False) if pozisyonlar else "",
    })

    print(f"  [Analiz] Kaydedildi — mez={alanlar.get('mezuniyet','')[:30]}")
    return True


def backfill_missing(limit: int = 20):
    """
    DB'deki eksik analizleri tamamla.
    Sadece pdf_text veya pozisyonlar_json boş olanları işle.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, url, title, organization FROM jobs
        WHERE source='kamuilan'
        AND (pdf_text IS NULL OR LENGTH(pdf_text) < 200
             OR pozisyonlar_json IS NULL OR pozisyonlar_json = '')
        ORDER BY rowid
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()

    print(f"Eksik analiz: {len(rows)} ilan (limit={limit})")
    for jid, url, title, org in rows:
        process_job(jid, url, title, org)
        time.sleep(1)
    print("Backfill tamamlandı")
