"""
DayımYok — Ana Pipeline
Çalıştır: python pipeline.py
GitHub Actions her sabah 09:00 TR bunu çalıştırır.
"""

import sys
import time
from datetime import datetime

from db import init_db, insert_job, get_stats, update_job_fields
from supabase_client import sb_ping
from fix_iptal import is_iptal

# Scraper modülleri
from scrapers.kamuilan import scrape as scrape_kamuilan
from scrapers.memurlar import scrape as scrape_memurlar
from scrapers.iskur import scrape as scrape_iskur
from scrapers.kariyerkapisi import scrape as scrape_kariyerkapisi

from ilan_processor import process_job
from llm_parser import groq_etiket_cıkar

_KAYNAKLAR = [
    ("kamuilan",      scrape_kamuilan,      True),   # True → PDF analizi yap
    ("memurlar",      scrape_memurlar,      False),
    ("iskur",         scrape_iskur,         False),
    ("kariyerkapisi", scrape_kariyerkapisi, False),
]


def _log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def calistir():
    _log("=== DayımYok Pipeline Başlıyor ===")

    # Bağlantı kontrolleri
    init_db()
    if not sb_ping():
        _log("UYARI: Supabase bağlantısı yok — sadece SQLite'a yazılacak")
    else:
        _log("Supabase bağlantısı OK")

    toplam_yeni = 0
    toplam_cekilen = 0
    ozet = {}

    for kaynak_adi, scrape_fn, pdf_var in _KAYNAKLAR:
        _log(f"--- {kaynak_adi} scraping ---")
        try:
            ilanlar = scrape_fn()
        except Exception as e:
            _log(f"  HATA scrape({kaynak_adi}): {e}")
            ozet[kaynak_adi] = {"cekilen": 0, "yeni": 0, "hata": str(e)}
            continue

        _log(f"  {len(ilanlar)} ilan çekildi")
        toplam_cekilen += len(ilanlar)

        yeni_sayisi = 0
        for ilan in ilanlar:
            try:
                yeni = insert_job(ilan)
            except Exception as e:
                _log(f"  insert hata: {e}")
                continue

            if not yeni:
                continue

            # İPTAL ilanını hemen pasife çek
            if is_iptal(ilan.get("title", "")):
                update_job_fields(ilan["hash"], {"is_active": 0})
                _log(f"  [İPTAL] {ilan.get('title','')[:50]}")
                continue

            yeni_sayisi += 1
            toplam_yeni += 1
            _log(f"  + {ilan.get('organization', '')[:30]} — {ilan.get('title', '')[:40]}")

            if pdf_var:
                # kamuilan: tam PDF analizi (regex + tablo + Groq)
                try:
                    process_job(
                        job_id=ilan["hash"],
                        url=ilan["url"],
                        title=ilan.get("title", ""),
                        org=ilan.get("organization", ""),
                    )
                except Exception as e:
                    _log(f"    process_job hata: {e}")
            else:
                # Diğer kaynaklar: en azından etiket üret
                pdf_text = ilan.get("pdf_text", "") or ilan.get("positions", "")
                if pdf_text and len(pdf_text) > 50:
                    try:
                        time.sleep(2)
                        etiket = groq_etiket_cıkar(pdf_text)
                        if etiket:
                            from db import update_job_fields
                            update_job_fields(ilan["hash"], {"arama_etiketleri": etiket})
                    except Exception as e:
                        _log(f"    etiket hata: {e}")

        ozet[kaynak_adi] = {"cekilen": len(ilanlar), "yeni": yeni_sayisi}
        _log(f"  → {yeni_sayisi} yeni ilan kaydedildi")

    # Özet
    toplam, by_source = get_stats()
    _log("=== Pipeline Tamamlandı ===")
    _log(f"Toplam çekilen: {toplam_cekilen} | Yeni: {toplam_yeni} | DB toplam: {toplam}")
    for kaynak, veriler in ozet.items():
        hata = f" (HATA: {veriler['hata']})" if "hata" in veriler else ""
        _log(f"  {kaynak}: {veriler['cekilen']} çekildi, {veriler['yeni']} yeni{hata}")

    return toplam_yeni


if __name__ == "__main__":
    yeni = calistir()
    sys.exit(0 if yeni >= 0 else 1)
