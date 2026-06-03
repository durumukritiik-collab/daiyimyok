"""İPTAL ilanlarını pasife çek — tek seferlik + pipeline'a dahil edilecek fonksiyon."""
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from db import DB_PATH, update_job_fields

# İPTAL tespit kalıpları
IPTAL_KALIPLARI = [
    "iptal ilanı", "iptal i̇lanı",
    "ilan iptali", "i̇lan iptali",
    "kadro iptali",
    "resmi gazete yayimlanan",  # "X sayılı RG'de yayımlanan ... iptali" formatı
]

def is_iptal(title: str, pdf_text: str = "") -> bool:
    """İlanın iptal edilip edilmediğini kontrol et."""
    # Türkçe İ harfi lower() ile 'i̇' (iki karakter) olabilir.
    # ASCII-safe kontrol: büyük harf versiyonuyla karşılaştır.
    title_upper = (title or "").upper()
    sample_upper = ((pdf_text or "")[:200]).upper()
    combined = title_upper + " " + sample_upper

    return (
        "PTAL" in combined  # İPTAL, IPTAL, iptal hepsini yakalar
    )


def backfill_iptal():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, pdf_text FROM jobs WHERE is_active=1")
    rows = c.fetchall()
    conn.close()

    pasife_cekildi = 0
    for jid, title, pdf_text in rows:
        if is_iptal(title or "", pdf_text or ""):
            update_job_fields(jid, {"is_active": 0})
            print(f"  PASSİF: {title[:70]}")
            pasife_cekildi += 1

    print(f"\nPassife çekilen ilan: {pasife_cekildi}")

    # Doğrula
    conn2 = sqlite3.connect(DB_PATH)
    c2 = conn2.cursor()
    c2.execute("SELECT COUNT(*) FROM jobs WHERE is_active=1 AND (title LIKE '%PTAL%' OR title LIKE '%ptal%')")
    kalan = c2.fetchone()[0]
    conn2.close()
    print(f"Aktif kalan İPTAL ilanı: {kalan}")


if __name__ == "__main__":
    backfill_iptal()
