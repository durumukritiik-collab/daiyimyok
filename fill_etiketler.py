"""
Arama etiketlerini doldur.
Strateji: 70b'nin PDF'den çıkardığı yapısal alanları kullan (mezuniyet, positions, pozisyonlar_json).
Yeni ilanlar için pipeline.py zaten groq_etiket_cıkar() çağırıyor.
Bu script sadece mevcut ilanları toplu doldurur.
"""
import argparse
import json
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from db import DB_PATH, update_job_fields
from dotenv import load_dotenv
load_dotenv()


def etiket_uret(row: dict) -> str:
    """Yapısal alanlardan etiket üret — Groq'un PDF'den çıkardığı veriler."""
    etiketler = set()

    # Bölüm / mezuniyet
    for alan in ['mezuniyet', 'positions']:
        val = row.get(alan, '') or ''
        if len(val) > 300:
            val = val[:300]
        for kelime in re.split(r'[,|/\n]', val):
            kelime = kelime.strip().lower()
            if 2 < len(kelime) < 60 and not kelime.startswith('http'):
                etiketler.add(kelime)

    # pozisyonlar_json'dan unvan ve bölüm
    poz_json = row.get('pozisyonlar_json', '') or ''
    if poz_json:
        try:
            for poz in json.loads(poz_json):
                for alan in ['unvan', 'bolum']:
                    val = str(poz.get(alan, '') or '')
                    for kelime in re.split(r'[,/]', val):
                        kelime = kelime.strip().lower()
                        if 2 < len(kelime) < 60:
                            etiketler.add(kelime)
                if poz.get('kpss_turu'):
                    etiketler.add(str(poz['kpss_turu']).lower().strip())
        except Exception:
            pass

    # İstihdam türü
    emp = (row.get('employment_type', '') or '').lower().strip()
    if emp:
        etiketler.add(emp)

    # Kurum adı
    org = (row.get('organization', '') or '').strip()
    if org and len(org) < 60:
        etiketler.add(org.lower())

    # KPSS puan türleri
    for puan in re.findall(r'p\d+', (row.get('kpss_sart', '') or '').lower()):
        etiketler.add(puan)

    # Mezuniyet seviyesi
    sev = (row.get('mezuniyet_seviyesi', '') or '').lower().strip()
    if sev:
        etiketler.add(sev)

    # Temizle ve döndür
    temiz = {e for e in etiketler if len(e) > 2}
    return ", ".join(sorted(temiz)[:20])


def calistir(limit: int = 999):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, title, organization, mezuniyet, positions, pozisyonlar_json,
               employment_type, kpss_sart, mezuniyet_seviyesi
        FROM jobs
        WHERE (arama_etiketleri IS NULL OR arama_etiketleri = '')
        ORDER BY created_at
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    kolonlar = ['id','title','organization','mezuniyet','positions','pozisyonlar_json',
                'employment_type','kpss_sart','mezuniyet_seviyesi']
    conn.close()

    print(f"Etiket bekleyen ilan: {len(rows)}")
    if not rows:
        print("Hepsi dolu.")
        return

    basarili = 0
    for i, row_tuple in enumerate(rows, 1):
        row = dict(zip(kolonlar, row_tuple))
        sonuc = etiket_uret(row)

        print(f"[{i}/{len(rows)}] {row['organization'][:35]} — {row['title'][:35]}")
        if sonuc:
            update_job_fields(row['id'], {'arama_etiketleri': sonuc})
            print(f"  OK: {sonuc[:90]}")
            basarili += 1
        else:
            print("  Boş — alanlar doldurulmamış")

    print(f"\n=== Tamamlandı: {basarili}/{len(rows)} ilan ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=999)
    args = parser.parse_args()
    calistir(limit=args.limit)
