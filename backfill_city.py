"""
Mevcut ilanların city alanını organization adından doldur.
Tek seferlik çalıştır.
"""
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from db import DB_PATH, update_job_fields
from city_extractor import extract_city


def calistir():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, organization, title, pdf_text
        FROM jobs
        WHERE city IS NULL OR city = ''
    """)
    rows = c.fetchall()
    conn.close()

    print(f"City boş ilan: {len(rows)}")

    doldurulan = 0
    bos_kalan = 0

    for jid, org, title, pdf_text in rows:
        city = extract_city(org or "", title or "", pdf_text or "")
        if city:
            update_job_fields(jid, {"city": city})
            doldurulan += 1
        else:
            bos_kalan += 1

    print(f"\nSonuç:")
    print(f"  Doldurulan : {doldurulan}")
    print(f"  Boş kalan  : {bos_kalan} (kaynak sayfada şehir bilgisi yok)")
    print(f"  Toplam     : {len(rows)}")

    # Doluluğu kontrol et
    conn2 = sqlite3.connect(DB_PATH)
    c2 = conn2.cursor()
    c2.execute("SELECT COUNT(*) FROM jobs WHERE city != '' AND city IS NOT NULL")
    dolu = c2.fetchone()[0]
    c2.execute("SELECT COUNT(*) FROM jobs")
    toplam = c2.fetchone()[0]
    conn2.close()
    print(f"\nCity doluluğu: {dolu}/{toplam} (%{int(dolu/toplam*100)})")


if __name__ == "__main__":
    calistir()
