import sqlite3
import re
import json

conn = sqlite3.connect("kamu_radar.db")
c = conn.cursor()
c.execute("""SELECT title, organization, employment_type, application_deadline, url,
             source, positions, mezuniyet, kpss_sart, yas_siniri, kontenjan,
             kpss_puan, mezuniyet_seviyesi, tecrube, basvuru_sekli, sinav_tarihi,
             COALESCE(arama_etiketleri,''), COALESCE(pozisyonlar_json,'')
             FROM jobs ORDER BY source, organization""")
all_rows = c.fetchall()
conn.close()

# Duplicate eliminasyonu: aynı kurum + benzer başlık → kamuilan öncelikli
seen = {}
for row in all_rows:
    title, org = row[0], row[1]
    anahtar = (org.strip().lower()[:30], re.sub(r'\d+', '#', title.lower())[:30])
    src = row[5]
    if anahtar not in seen:
        seen[anahtar] = row
    elif src == 'kamuilan':
        seen[anahtar] = row
rows = list(seen.values())

AYLAR = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

MESLEK_KALIPLARI = [
    ("psikolog", "Psikolog"),
    ("hemşire", "Hemşire"),
    ("doktor", "Doktor"), ("hekim", "Doktor"), ("tabip", "Doktor"),
    ("eczacı", "Eczacı"),
    ("fizyoterapist", "Fizyoterapist"),
    ("diyetisyen", "Diyetisyen"),
    ("veteriner", "Veteriner"),
    ("sosyal çalışmacı", "Sosyal Çalışmacı"),
    ("öğretim üyesi", "Öğretim Üyesi"),
    ("öğretim görevlisi", "Öğretim Görevlisi"),
    ("öğretim elemanı", "Öğretim Elemanı"),
    ("araştırma görevlisi", "Araştırma Görevlisi"),
    ("mühendis", "Mühendis"),
    ("mimar", "Mimar"),
    ("avukat", "Avukat"),
    ("müfettiş yardımcısı", "Müfettiş Yardımcısı"),
    ("müfettiş", "Müfettiş"),
    ("uzman yardımcısı", "Uzman Yardımcısı"),
    ("uzman", "Uzman"),
    ("zabıta memuru", "Zabıta Memuru"), ("zabıta", "Zabıta"),
    ("itfaiye eri", "İtfaiye Eri"), ("itfaiye", "İtfaiye"),
    ("büro görevlisi", "Büro Görevlisi"),
    ("iletişim görevlisi", "İletişim Görevlisi"),
    ("bilişim personeli", "Bilişim Personeli"),
    ("sekreter", "Sekreter"),
    ("programcı", "Programcı"),
    ("tekniker", "Tekniker"), ("teknisyen", "Teknisyen"),
    ("denetmen", "Denetmen"),
    ("sürekli işçi", "Sürekli İşçi"), ("işçi", "İşçi"),
    ("sözleşmeli personel", "Sözleşmeli Personel"),
    ("memur", "Memur"),
]

_TR = str.maketrans('İIĞÜŞÖÇ', 'iığüşöç')

def _norm(s):
    return (s or "").translate(_TR).lower()

def clean_positions(positions_text, title):
    baslik = _norm(title)
    pozisyon = _norm(positions_text)
    bulunanlar = []
    genel = {"Memur", "Sözleşmeli Personel", "İşçi"}
    for kalip, etiket in MESLEK_KALIPLARI:
        if etiket in genel:
            continue
        if kalip in baslik and etiket not in bulunanlar:
            bulunanlar.append(etiket)
        if len(bulunanlar) >= 3:
            break
    if not bulunanlar:
        for kalip, etiket in MESLEK_KALIPLARI:
            if kalip in pozisyon and etiket not in bulunanlar:
                bulunanlar.append(etiket)
            if len(bulunanlar) >= 3:
                break
    if not bulunanlar:
        for kalip, etiket in [("memur","Memur"),("sözleşmeli","Sözleşmeli Personel"),("işçi","İşçi")]:
            if kalip in baslik:
                bulunanlar.append(etiket)
                break
    # Üst küme varsa alt kümeyi çıkar (Zabıta Memuru varsa Zabıta'yı kaldır)
    temiz = []
    for e in bulunanlar:
        if not any(e != b and e in b for b in bulunanlar):
            temiz.append(e)
    return ", ".join(temiz) if temiz else ""

def split_memurlar_title(title):
    m = re.search(r'\d', title)
    if m:
        org = title[:m.start()].strip().rstrip(",")
        pos = title[m.start():].strip()
        return org, pos
    for kw in ["Öğretim Üyesi","Öğretim Eleman","Araştırma Görevlisi","Öğretim Görevlisi"]:
        idx = title.find(kw)
        if idx > 0:
            return title[:idx].strip(), title[idx:].strip()
    return "", title

# Aktif ilan sayısı
aktif = 0
ay_map = {"ocak":1,"şubat":2,"mart":3,"nisan":4,"mayıs":5,"haziran":6,
          "temmuz":7,"ağustos":8,"eylül":9,"ekim":10,"kasım":11,"aralık":12}
from datetime import datetime
bugun = datetime.now()
for row in rows:
    dl = row[3]
    if not dl: continue
    matches = re.findall(r'(\d+)\s+([a-zA-ZğüşıöçĞÜŞİÖÇ]+)', dl.lower())
    if not matches: continue
    last = matches[-1]
    ay = ay_map.get(last[1], 0)
    if not ay: continue
    try:
        if datetime(2026, ay, int(last[0])) >= bugun:
            aktif += 1
    except: pass

html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Kamu Kariyer Radarı</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; background: #f0f2f5; }}
  .header {{ background: #1a237e; color: white; padding: 16px 24px; }}
  .header h1 {{ font-size: 1.4em; }}
  .header p {{ font-size: 0.85em; opacity: 0.75; margin-top: 2px; }}
  .stats {{ display: flex; gap: 20px; padding: 16px 24px; flex-wrap: wrap; background: #283593; }}
  .stat {{ text-align: center; color: white; }}
  .stat-num {{ font-size: 1.8em; font-weight: bold; }}
  .stat-label {{ font-size: 0.75em; opacity: 0.8; }}
  .toolbar {{ padding: 12px 24px; display: flex; gap: 10px; align-items: center; background: white; border-bottom: 1px solid #ddd; }}
  .toolbar input {{ padding: 8px 12px; width: 300px; border: 1px solid #ccc; border-radius: 6px; font-size: 0.9em; }}
  .toolbar select {{ padding: 8px; border: 1px solid #ccc; border-radius: 6px; font-size: 0.9em; }}
  .table-wrap {{ padding: 16px 24px; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  th {{ background: #283593; color: white; padding: 11px 14px; text-align: left; font-size: 0.85em; }}
  td {{ padding: 9px 14px; border-bottom: 1px solid #f0f0f0; font-size: 0.85em; vertical-align: middle; }}
  tbody tr {{ cursor: pointer; transition: background 0.15s; }}
  tbody tr:hover {{ background: #e8eaf6; }}
  .tag {{ padding: 2px 8px; border-radius: 20px; font-size: 0.72em; font-weight: bold; display: inline-block; }}
  .memur {{ background: #c8e6c9; color: #1b5e20; }}
  .sozlesmeli {{ background: #fff9c4; color: #f57f17; }}
  .other {{ background: #e1f5fe; color: #01579b; }}
  .meslek-tag {{ background: #ede7f6; color: #4527a0; padding: 2px 8px; border-radius: 20px; font-size: 0.72em; font-weight: bold; }}
  .bolum {{ color: #1565c0; font-size: 0.82em; }}
  .kpss {{ color: #c62828; font-size: 0.8em; }}
  .yas {{ color: #e65100; font-weight: bold; }}

  /* MODAL */
  .overlay {{ display:none; position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:100; align-items:center; justify-content:center; }}
  .overlay.open {{ display:flex; }}
  .modal {{ background:white; border-radius:14px; width:560px; max-width:95vw; max-height:90vh; overflow-y:auto; box-shadow:0 8px 40px rgba(0,0,0,0.25); }}
  .modal-header {{ background:#1a237e; color:white; padding:18px 22px; border-radius:14px 14px 0 0; position:relative; }}
  .modal-header h2 {{ font-size:1.05em; line-height:1.4; padding-right:30px; }}
  .modal-header .org {{ font-size:0.8em; opacity:0.8; margin-top:4px; }}
  .modal-close {{ position:absolute; top:14px; right:16px; background:none; border:none; color:white; font-size:1.4em; cursor:pointer; line-height:1; }}
  .modal-body {{ padding:20px 22px; }}
  .detail-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px; }}
  .detail-item {{ background:#f8f9ff; border-radius:8px; padding:10px 14px; }}
  .detail-item .label {{ font-size:0.7em; color:#666; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:3px; }}
  .detail-item .value {{ font-size:0.9em; font-weight:600; color:#1a237e; }}
  .detail-item.full {{ grid-column:1/-1; }}
  .kpss-box {{ background:#fff3e0; border-left:3px solid #e65100; border-radius:4px; padding:10px 14px; margin-bottom:14px; font-size:0.88em; color:#bf360c; }}
  .modal-actions {{ display:flex; gap:10px; margin-top:16px; }}
  .btn {{ padding:9px 18px; border-radius:8px; font-size:0.9em; font-weight:bold; cursor:pointer; border:none; text-decoration:none; display:inline-block; text-align:center; }}
  .btn-primary {{ background:#1a237e; color:white; }}
  .btn-primary:hover {{ background:#283593; }}
  .btn-secondary {{ background:#e8eaf6; color:#1a237e; }}
</style>
</head>
<body>
<div class="header">
  <h1>📡 Kamu Kariyer Radarı</h1>
  <p>Kamu ilanlarını takip et, şartlarını karşıla, başvur.</p>
</div>
<div class="stats">
  <div class="stat"><div class="stat-num">{len(rows)}</div><div class="stat-label">Toplam İlan</div></div>
  <div class="stat"><div class="stat-num">{aktif}</div><div class="stat-label">Aktif İlan</div></div>
  <div class="stat"><div class="stat-num">2</div><div class="stat-label">Kaynak</div></div>
</div>
<div class="toolbar">
  <input type="text" id="search" onkeyup="filterTable()" placeholder="🔍  Kurum, bölüm, meslek ara...">
  <select id="sourceFilter" onchange="filterTable()">
    <option value="">Tüm Kaynaklar</option>
    <option value="kamuilan">Kamu İlan Portalı</option>
    <option value="memurlar">Memurlar.net</option>
  </select>
</div>
<div class="table-wrap">
<table id="ilanTable">
<thead><tr>
  <th>Kurum</th><th>Pozisyon</th><th>Meslek</th><th>Bölüm</th>
  <th>KPSS</th><th>Yaş</th><th>Kişi</th><th>Son Başvuru</th>
</tr></thead>
<tbody>
"""

ilan_data = []

for row in rows:
    (title, org, etype, deadline, url, source, positions, mezuniyet,
     kpss_sart, yas_siniri, kontenjan, kpss_puan, mez_seviye,
     tecrube, basvuru_sekli, sinav_tarihi, arama_etiketleri, poz_json) = row

    # Pozisyon listesi varsa → her pozisyon için ayrı satır oluştur
    try:
        pozisyon_listesi = json.loads(poz_json) if poz_json else []
    except:
        pozisyon_listesi = []

    tag_class = "memur" if etype == "Memur" else ("sozlesmeli" if etype == "Sözleşmeli" else "other")
    tag_label = etype if etype else "Diğer"

    if source == "kamuilan":
        display_org = org
        display_title = title
        display_deadline = deadline
        meslek = clean_positions(positions, title)
    else:
        clean = title.split(". Son")[0].split(". son")[0].strip()
        half = len(clean) // 2
        if half > 0 and clean[:half].strip() == clean[half:].strip():
            clean = clean[:half].strip()
        parsed_org, parsed_pos = split_memurlar_title(clean)
        display_org = parsed_org if parsed_org else (org.split(".")[0] if org else "")
        display_title = parsed_pos if parsed_pos else clean
        display_deadline = deadline if deadline and any(ay in deadline for ay in AYLAR) else ""
        meslek = clean_positions(positions, clean)

    # Kontenjan: başlıktaki sayı ile DB değerini karşılaştır, büyük olanı al
    m_kont = re.match(r'^(\d+)\s+', (display_title or "").strip())
    baslik_sayisi = int(m_kont.group(1)) if m_kont else 0
    try:
        db_kont = int(kontenjan) if kontenjan else 0
    except ValueError:
        db_kont = 0
    gercek_kont = str(max(baslik_sayisi, db_kont)) if max(baslik_sayisi, db_kont) > 0 else (kontenjan or "")

    # Ortak ilan verisi (tüm pozisyonlar için aynı)
    ilan_base = {
        "org": display_org,
        "title": display_title,
        "url": url or "",
        "etype": tag_label,
        "kpss_sart": kpss_sart or "",
        "yas_siniri": yas_siniri or "",
        "basvuru_sekli": basvuru_sekli or "",
        "sinav_tarihi": sinav_tarihi or "",
        "deadline": display_deadline,
        "source": source,
        "tecrube": tecrube or "",
    }

    # Pozisyon listesi varsa her biri ayrı satır, yoksa tek satır
    if pozisyon_listesi:
        satirlar = []
        for poz in pozisyon_listesi:
            p_bolum   = poz.get("bolum", "") or mezuniyet or ""
            p_unvan   = poz.get("unvan", "") or meslek
            p_kont    = str(poz.get("kontenjan", "")) or ""
            p_kpss_t  = poz.get("kpss_turu", "") or ""
            p_kpss_m  = str(poz.get("kpss_min", "")) or kpss_puan or ""
            p_yas     = str(poz.get("yas_max", "")) or yas_siniri or ""
            p_akademik = poz.get("akademik_unvan_gerekli", False)
            p_sev     = poz.get("mezuniyet_seviyesi", "") or mez_seviye or ""
            p_kpss_sart = ("⛔ Akademik unvan gerekli" if p_akademik else
                           (f"KPSS {p_kpss_t} — min {p_kpss_m}" if p_kpss_t and p_kpss_m else
                            kpss_sart or ""))
            satirlar.append({**ilan_base,
                "meslek": p_unvan,
                "mezuniyet": p_bolum,
                "mezuniyet_seviyesi": p_sev,
                "kpss_sart": p_kpss_sart,
                "kpss_puan": p_kpss_m,
                "yas_siniri": p_yas,
                "kontenjan": p_kont,
                "ara_metin": (arama_etiketleri + " " + p_bolum + " " + p_unvan)[:500].lower(),
            })
    else:
        satirlar = [{**ilan_base,
            "meslek": meslek,
            "mezuniyet": mezuniyet or "",
            "mezuniyet_seviyesi": mez_seviye or "",
            "kpss_puan": kpss_puan or "",
            "kontenjan": gercek_kont,
            "ara_metin": (arama_etiketleri + " " + (mezuniyet or "") + " " + (positions or ""))[:500].lower(),
        }]

    for satir in satirlar:
        idx = len(ilan_data)
        ilan_data.append(satir)

        s_meslek  = satir["meslek"]
        s_bolum   = satir["mezuniyet"]
        s_kpss    = satir["kpss_sart"]
        s_yas     = satir["yas_siniri"]
        s_kont    = satir["kontenjan"]

        meslek_html = f'<span class="meslek-tag">{s_meslek}</span>' if s_meslek else ""
        kpss_kisa = f'<span class="kpss">{s_kpss.split("|")[0].strip()}</span>' if s_kpss else ""
        bolum_html = f'<span class="bolum">{s_bolum}</span>' if s_bolum else ""
        yas_html   = f'<span class="yas">{s_yas}</span>' if s_yas else ""
        kont_html  = f'<b>{s_kont}</b>' if s_kont else ""

        html += f'<tr onclick="openModal({idx})">'
        html += f'<td>{display_org}</td>'
        html += f'<td>{display_title}</td>'
        html += f'<td>{meslek_html}</td>'
        html += f'<td>{bolum_html}</td>'
        html += f'<td>{kpss_kisa}</td>'
        html += f'<td>{yas_html}</td>'
        html += f'<td>{kont_html}</td>'
        html += f'<td>{display_deadline}</td>'
        html += '</tr>\n'

html += f"""</tbody></table>
</div>

<!-- MODAL -->
<div class="overlay" id="overlay" onclick="closeModal(event)">
  <div class="modal" id="modal">
    <div class="modal-header">
      <h2 id="m-title"></h2>
      <div class="org" id="m-org"></div>
      <button class="modal-close" onclick="document.getElementById('overlay').classList.remove('open')">✕</button>
    </div>
    <div class="modal-body">
      <div class="kpss-box" id="m-kpss" style="display:none"></div>
      <div class="detail-grid">
        <div class="detail-item"><div class="label">Bölüm / Alan</div><div class="value" id="m-bolum">—</div></div>
        <div class="detail-item"><div class="label">Mezuniyet Seviyesi</div><div class="value" id="m-seviyes">—</div></div>
        <div class="detail-item"><div class="label">Min. KPSS Puanı</div><div class="value" id="m-kpss-puan">—</div></div>
        <div class="detail-item"><div class="label">Yaş Sınırı</div><div class="value" id="m-yas">—</div></div>
        <div class="detail-item"><div class="label">Kontenjan</div><div class="value" id="m-kont">—</div></div>
        <div class="detail-item"><div class="label">İstihdam Türü</div><div class="value" id="m-etype">—</div></div>
        <div class="detail-item"><div class="label">Tecrübe Şartı</div><div class="value" id="m-tec">—</div></div>
        <div class="detail-item"><div class="label">Başvuru Şekli</div><div class="value" id="m-bsek">—</div></div>
        <div class="detail-item full"><div class="label">Sınav Tarihi</div><div class="value" id="m-sinav">—</div></div>
        <div class="detail-item full"><div class="label">Son Başvuru</div><div class="value" id="m-deadline">—</div></div>
      </div>
      <div class="modal-actions">
        <a class="btn btn-primary" id="m-link" href="#" target="_blank">İlana Git →</a>
        <a class="btn btn-secondary" id="m-link2" href="https://kamuilan.sbb.gov.tr/" target="_blank" style="display:none">Kamuilan.sbb.gov.tr</a>
        <button class="btn btn-secondary" onclick="document.getElementById('overlay').classList.remove('open')">Kapat</button>
      </div>
    </div>
  </div>
</div>

<script>
var DATA = {json.dumps(ilan_data, ensure_ascii=False)};

function openModal(i) {{
  var d = DATA[i];
  document.getElementById('m-title').textContent = d.title;
  document.getElementById('m-org').textContent = d.org;
  document.getElementById('m-bolum').textContent = d.mezuniyet || '—';
  document.getElementById('m-seviyes').textContent = d.mezuniyet_seviyesi || '—';
  document.getElementById('m-kpss-puan').textContent = d.kpss_puan ? d.kpss_puan + ' puan' : '—';
  document.getElementById('m-yas').textContent = d.yas_siniri ? 'Max ' + d.yas_siniri + ' yaş' : '—';
  document.getElementById('m-kont').textContent = d.kontenjan ? d.kontenjan + ' kişi' : '—';
  document.getElementById('m-etype').textContent = d.etype || '—';
  document.getElementById('m-tec').textContent = d.tecrube || 'Yok';
  document.getElementById('m-bsek').textContent = d.basvuru_sekli || '—';
  document.getElementById('m-sinav').textContent = d.sinav_tarihi || '—';
  document.getElementById('m-deadline').textContent = d.deadline || '—';
  var kpssBox = document.getElementById('m-kpss');
  if (d.kpss_sart) {{
    kpssBox.textContent = d.kpss_sart;
    kpssBox.style.display = 'block';
  }} else {{
    kpssBox.style.display = 'none';
  }}
  var link = document.getElementById('m-link');
  var link2 = document.getElementById('m-link2');
  if (d.url) {{
    if (d.url.includes('kamuilan.sbb.gov.tr')) {{
      // Proxy üzerinden PDF aç (radar_server.py çalışıyorsa)
      var proxyUrl = 'http://localhost:8765/pdf?url=' + encodeURIComponent(d.url);
      link.href = proxyUrl;
      link.onclick = null;
      link.textContent = 'PDF Aç →';
      // Yedek: direkt link
      link2.href = d.url;
      link2.style.display = 'inline-block';
      link2.textContent = 'Direkt Link';
    }} else {{
      link.href = d.url;
      link.onclick = null;
      link.textContent = 'İlana Git →';
      link2.style.display = 'none';
    }}
    link.style.display = 'inline-block';
  }} else {{
    link.style.display = 'none';
    link2.style.display = 'none';
  }}
  document.getElementById('overlay').classList.add('open');
}}

function closeModal(e) {{
  if (e.target === document.getElementById('overlay'))
    document.getElementById('overlay').classList.remove('open');
}}

function filterTable() {{
  var q = document.getElementById('search').value.toLowerCase();
  var src = document.getElementById('sourceFilter').value.toLowerCase();
  var rows = document.getElementById('ilanTable').getElementsByTagName('tr');
  for (var i = 1; i < rows.length; i++) {{
    var d = DATA[i-1];
    // Görünen metin + positions/mezuniyet tam metni
    var text = rows[i].textContent.toLowerCase() + ' ' + (d.ara_metin || '');
    var show = text.includes(q) && (src === '' || d.source.includes(src));
    rows[i].style.display = show ? '' : 'none';
  }}
}}
</script>
</body></html>"""

with open("radar.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"radar.html hazır! ({len(rows)} ilan, {aktif} aktif)")
