import sqlite3, requests, warnings, sys, io, pdfplumber
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8')

session = requests.Session()
session.headers['User-Agent'] = 'Mozilla/5.0'
session.get('https://kamuilan.sbb.gov.tr/', verify=False, timeout=10)

conn = sqlite3.connect('kamu_radar.db')
c = conn.cursor()
c.execute("""SELECT url, title, organization FROM jobs
             WHERE source='kamuilan'
             AND title NOT LIKE '%DÜZELTME%'
             AND title NOT LIKE '%IPTAL%'
             ORDER BY RANDOM() LIMIT 10 OFFSET 10""")
rows = c.fetchall()
conn.close()

for i, (url, title, org) in enumerate(rows, 1):
    try:
        r = session.get(url, verify=False, timeout=10, headers={'Referer': 'https://kamuilan.sbb.gov.tr/'})
        if r.content[:4] != b'%PDF':
            continue
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            sayfa_sayisi = len(pdf.pages)
            tam_metin = ' '.join(p.extract_text() or '' for p in pdf.pages)

        print('='*70)
        print(f'[{i}] {org}')
        print(f'     {title}')
        print(f'     Sayfa: {sayfa_sayisi} | Karakter: {len(tam_metin)}')
        print()
        print(tam_metin[:3000])
        print()
    except Exception as e:
        print(f'HATA [{title}]: {e}')
