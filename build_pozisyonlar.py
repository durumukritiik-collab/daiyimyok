"""
Her PDF ilanı için Groq ile pozisyon listesi çıkar, DB'ye kaydet.
Çalıştır: python build_pozisyonlar.py
"""
import sqlite3, json, time, warnings, sys
from dotenv import load_dotenv
from llm_parser import groq_analiz

load_dotenv()
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8')

DB = "kamu_radar.db"

def run():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Sadece PDF metni olan ve pozisyon listesi henüz çıkarılmamış ilanlar
    c.execute("""SELECT id, organization, title, pdf_text FROM jobs
                 WHERE source='kamuilan'
                 AND LENGTH(COALESCE(pdf_text,'')) > 500
                 AND (pozisyonlar_json='' OR pozisyonlar_json IS NULL)
                 ORDER BY rowid""")
    rows = c.fetchall()
    conn.close()

    print(f"Analiz edilecek: {len(rows)} ilan\n")

    for i, (jid, org, title, pdf) in enumerate(rows, 1):
        print(f"[{i:02d}/{len(rows)}] {org[:45]}")
        print(f"         {title[:50]}")

        time.sleep(2)
        analiz = groq_analiz(pdf)

        if analiz and analiz.get("pozisyonlar"):
            poz = analiz["pozisyonlar"]
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("UPDATE jobs SET pozisyonlar_json=? WHERE id=?",
                      (json.dumps(poz, ensure_ascii=False), jid))
            conn.commit()
            conn.close()
            print(f"         → {len(poz)} pozisyon kaydedildi")
            for p in poz[:3]:
                bolum = p.get('bolum','')[:40]
                unvan = p.get('unvan','')
                adet  = p.get('kontenjan','?')
                print(f"           • {unvan} | {bolum} | {adet} kişi")
        else:
            print(f"         → pozisyon çıkarılamadı")
        print()

    # Özet
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM jobs WHERE pozisyonlar_json!='' AND pozisyonlar_json IS NOT NULL")
    print(f"Tamamlandi: {c.fetchone()[0]} ilan pozisyon verisi var")
    conn.close()

if __name__ == "__main__":
    run()
