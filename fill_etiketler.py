"""
Mevcut 132 ilanın arama_etiketleri'ni Groq ile doldur.
Sadece bir kez çalıştırılır.

Kullanım:
    python fill_etiketler.py
    python fill_etiketler.py --limit 20   # test için
"""

import argparse
import sqlite3
import time
import sys

from db import DB_PATH, update_job_fields
from llm_parser import groq_etiket_cıkar

from dotenv import load_dotenv
load_dotenv()


def calistir(limit: int = 999):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, title, organization, pdf_text, arama_etiketleri
        FROM jobs
        WHERE (arama_etiketleri IS NULL OR arama_etiketleri = '')
        AND pdf_text IS NOT NULL AND LENGTH(pdf_text) > 200
        ORDER BY created_at
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()

    print(f"Etiket bekleyen ilan: {len(rows)} (limit={limit})")
    if not rows:
        print("Hepsi dolu, işlem yok.")
        return

    basarili = 0
    for i, (jid, title, org, pdf_text, mevcut) in enumerate(rows, 1):
        print(f"\n[{i}/{len(rows)}] {org[:35]} — {title[:40]}")
        if mevcut:
            print(f"  Zaten dolu, atlanıyor: {mevcut[:60]}")
            continue

        try:
            etiket = groq_etiket_cıkar(pdf_text)
        except Exception as e:
            print(f"  HATA: {e}")
            time.sleep(5)
            continue

        if etiket:
            update_job_fields(jid, {"arama_etiketleri": etiket})
            print(f"  OK: {etiket[:80]}")
            basarili += 1
        else:
            print("  Etiket üretilemedi")

        # Rate limit: 70b model 1000/gün → güvenli bekleme
        time.sleep(3)

    print(f"\n=== Tamamlandı: {basarili}/{len(rows)} ilan güncellendi ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Boş arama etiketlerini Groq ile doldur")
    parser.add_argument("--limit", type=int, default=999, help="Max ilan sayısı (default: hepsi)")
    args = parser.parse_args()
    calistir(limit=args.limit)
