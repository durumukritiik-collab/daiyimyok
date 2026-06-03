"""
DB'deki tüm kamuilan ilanlarının PDF'lerini yeniden indir,
yeni parser ile çek, DB'yi güncelle.

Kullanım: python reparse_pdfs.py
"""
import sqlite3, requests, io, warnings, sys, time
import pdfplumber
from dotenv import load_dotenv
from pdf_parser import parse_pdf_text, parse_pdf_tables, _kpss_cıkar
from llm_parser import llm_parse_if_needed, groq_etiket_cıkar

load_dotenv()
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = "kamu_radar.db"

GUNCELLE_ALANLARI = [
    "mezuniyet", "kpss_sart", "kpss_puan", "yas_siniri",
    "kontenjan", "ilan_tarihi", "basvuru_sekli",
    "tecrube", "mezuniyet_seviyesi", "sinav_tarihi",
    "pdf_text", "arama_etiketleri",
]

def reparse_all():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, url, title, organization FROM jobs WHERE source='kamuilan'")
    rows = c.fetchall()
    conn.close()

    session = requests.Session()
    session.headers['User-Agent'] = 'Mozilla/5.0'
    try:
        session.get('https://kamuilan.sbb.gov.tr/', verify=False, timeout=10)
    except:
        pass

    basarili = 0
    hata = 0
    pdf_degil = 0
    guncellenen = 0

    print(f"Toplam {len(rows)} kamuilan ilanı işlenecek...\n")

    for i, (job_id, url, title, org) in enumerate(rows, 1):
        try:
            r = session.get(url, verify=False, timeout=20,
                            headers={'Referer': 'https://kamuilan.sbb.gov.tr/'})

            # PDF öneki varsa temizle (bazı sunucular binary prefix gönderiyor)
            content = r.content
            if content[:4] != b'%PDF':
                pdf_start = content.find(b'%PDF')
                if pdf_start > 0:
                    content = content[pdf_start:]
                else:
                    pdf_degil += 1
                    print(f"[{i:03d}] PDF DEĞİL — {org[:40]}")
                    continue

            with pdfplumber.open(io.BytesIO(content)) as pdf:
                metin = ' '.join(p.extract_text() or '' for p in pdf.pages)

            if len(metin) < 100:
                print(f"[{i:03d}] BOŞ PDF — {org[:40]}")
                continue

            # 1) Önce tablo modunu dene
            tablo_sonuc = parse_pdf_tables(content)
            # 2) Metin modunu çalıştır
            sonuc = parse_pdf_text(metin)

            # 3) Tablo modundan gelen değerler varsa üzerine yaz (daha güvenilir)
            if tablo_sonuc.get("mezuniyet"):
                sonuc["mezuniyet"] = tablo_sonuc["mezuniyet"]
            if tablo_sonuc.get("mezuniyet_seviyesi"):
                sonuc["mezuniyet_seviyesi"] = tablo_sonuc["mezuniyet_seviyesi"]
            if tablo_sonuc.get("yas_siniri") and not sonuc["yas_siniri"]:
                sonuc["yas_siniri"] = tablo_sonuc["yas_siniri"]
            if tablo_sonuc.get("tecrube") and not sonuc["tecrube"]:
                sonuc["tecrube"] = tablo_sonuc["tecrube"]
            if tablo_sonuc.get("kontenjan") and not sonuc["kontenjan"]:
                sonuc["kontenjan"] = tablo_sonuc["kontenjan"]

            # 4) Tablo'dan gelen KPSS bilgilerini birleştir
            if tablo_sonuc.get("_kpss_turler") and tablo_sonuc.get("_kpss_min_list"):
                turler = tablo_sonuc["_kpss_turler"]
                puanlar = tablo_sonuc["_kpss_min_list"]
                # En yüksek min puan + ilk puan türünü kaydet
                if not sonuc["kpss_puan"]:
                    sonuc["kpss_puan"] = str(min(puanlar))
                if not sonuc["kpss_sart"] or sonuc["kpss_sart"] == "KPSS gerekli":
                    turu = turler[0] if turler else ""
                    min_p = min(puanlar) if puanlar else ""
                    if turu and min_p:
                        sonuc["kpss_sart"] = f"KPSS {turu} — min {min_p}"

            # 5) Kritik alanlar hâlâ boşsa LLM'e sor
            sonuc = llm_parse_if_needed(sonuc, metin)

            # 6) Full PDF metnini kaydet
            sonuc["pdf_text"] = metin[:50000]  # max 50k karakter

            # 7) Groq ile kapsamlı arama etiketleri çıkar (sadece boşsa)
            conn_check = sqlite3.connect(DB_PATH)
            c_check = conn_check.cursor()
            c_check.execute("SELECT arama_etiketleri FROM jobs WHERE id=?", (job_id,))
            mevcut_etiket = (c_check.fetchone() or [""])[0] or ""
            conn_check.close()

            if not mevcut_etiket:
                print(f"  [ETİKET] Groq ile etiket çıkarılıyor...")
                time.sleep(2)
                etiketler = groq_etiket_cıkar(metin)
                sonuc["arama_etiketleri"] = etiketler
                if etiketler:
                    print(f"  [ETİKET] {etiketler[:80]}...")
            else:
                sonuc["arama_etiketleri"] = mevcut_etiket  # mevcut kalsın

            basarili += 1
            kaynak = "tablo+metin" if tablo_sonuc else "metin"

            # DB'yi güncelle
            conn = sqlite3.connect(DB_PATH)
            c2 = conn.cursor()
            set_clause = ", ".join(f"{a} = ?" for a in GUNCELLE_ALANLARI)
            degerler = [sonuc.get(a, "") for a in GUNCELLE_ALANLARI]
            degerler.append(job_id)
            c2.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", degerler)

            if c2.rowcount > 0:
                guncellenen += 1

            conn.commit()
            conn.close()

            mez = sonuc.get('mezuniyet', '')[:30]
            kpss = sonuc.get('kpss_sart', '')[:35]
            print(f"[{i:03d}][{kaynak[:1].upper()}] {org[:32]:<32} | {mez:<30} | {kpss}")

        except Exception as e:
            hata += 1
            print(f"[{i:03d}] HATA — {org[:40]}: {e}")

        # Rate limiting
        time.sleep(0.3)

    print(f"\n{'='*60}")
    print(f"Tamamlandı:")
    print(f"  PDF okundu:    {basarili}")
    print(f"  DB güncellendi: {guncellenen}")
    print(f"  PDF değil:     {pdf_degil}")
    print(f"  Hata:          {hata}")

    # Özet doluluk oranları
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM jobs")
    total = c.fetchone()[0]
    print(f"\nGüncel doluluk oranları ({total} ilan):")
    for a in GUNCELLE_ALANLARI:
        c.execute(f"SELECT COUNT(*) FROM jobs WHERE {a} != '' AND {a} IS NOT NULL")
        dolu = c.fetchone()[0]
        print(f"  {a:22s}: {dolu:3d}/{total} (%{round(dolu/total*100)})")
    conn.close()

if __name__ == "__main__":
    reparse_all()
