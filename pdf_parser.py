import re
import io

try:
    import pdfplumber
    _PDFPLUMBER_OK = True
except ImportError:
    _PDFPLUMBER_OK = False

# ─── BÖLÜM EŞLEŞTİRME ───────────────────────────────────────────────
BOLUM_KALIPLARI = [
    # Sağlık
    (["psikoloji", "psikolojik danışman"], "Psikoloji"),
    (["tıp fakülte", "tıp bölüm", "tabip"], "Tıp"),
    (["eczacılık"], "Eczacılık"),
    (["hemşirelik"], "Hemşirelik"),
    (["fizyoterapi"], "Fizyoterapi"),
    (["beslenme ve diyetetik"], "Diyetisyen"),
    # Hukuk
    (["hukuk fakülte", "hukuk bölüm", "hukuk lisans"], "Hukuk"),
    # Mühendislik — çok spesifik eşleştir, "mühendislik" tek başına değil
    (["mühendislik fakülte", "mühendis mezun", "mühendislik bölüm",
      "mühendislik lisans", "inşaat müh", "elektrik müh",
      "makine müh", "bilgisayar müh", "çevre müh",
      "endüstri müh", "jeoloji müh", "orman müh"], "Mühendislik"),
    (["mimarlık", "şehir ve bölge planlama", "peyzaj mimarlık"], "Mimarlık"),
    # İktisadi
    (["iktisadi ve idari bilim", "siyasal bilgiler",
      "iktisat,", ", iktisat", "iktisat bölüm", "iktisat fakülte",
      "ekonomi bölüm", "ekonomi fakülte"], "İktisat/İİBF"),
    (["işletme,", ", işletme", "işletme bölüm", "işletme fakülte",
      "işletme ve yönetim"], "İşletme"),
    (["muhasebe", "maliye bölüm", "bankacılık ve finans",
      "finans ve bankacılık"], "Muhasebe/Maliye"),
    (["kamu yönetim", "siyaset bilim", "uluslararası ilişki",
      "kamu yönetimi,", ", kamu yönetimi"], "Kamu Yönetimi"),
    # Sosyal
    (["sosyoloji"], "Sosyoloji"),
    (["psikoloji,", "sosyal çalışma", "sosyal hizmet"], "Sosyal Hizmet"),
    (["istatistik,", "istatistik bölüm", "istatistik fakülte"], "İstatistik"),
    # İletişim
    (["iletişim fakülte", "iletişim bölüm", "iletişim,", ", iletişim",
      "halkla ilişki", "gazetecilik", "radyo televizyon"], "İletişim"),
    # Eğitim
    (["eğitim fakülte", "öğretmenlik", "pedagoji",
      "rehberlik ve psikolojik danışmanlık"], "Eğitim/PDR"),
    # Bilişim
    (["bilgisayar programcılık", "bilişim teknoloji",
      "yönetim bilişim", "bilgisayar ve öğretim"], "Bilgisayar/Bilişim"),
    # Diğer
    (["veteriner"], "Veterinerlik"),
    (["ziraat fakülte", "ziraat bölüm", "ziraat,", ", ziraat"], "Ziraat"),
    (["insan kaynakları yönetim", "insan kaynakları lisans"], "İnsan Kaynakları"),
    (["çalışma ekonomisi", "endüstri ilişkiler", "iş sağlığı ve güvenlik"], "Çalışma Ekonomisi"),
    (["uluslararası ilişki"], "Uluslararası İlişkiler"),
    (["ekonometri"], "Ekonometri"),
    (["gıda mühendis", "gıda bilimleri", "gıda teknoloji", "gıda işleme"], "Gıda Mühendisliği"),
    (["biyoloji", "biolog"], "Biyoloji"),
    (["elektrik-elektronik", "elektrik elektronik", "elektronik mühendis"], "Elektrik-Elektronik Müh."),
    (["tekniker", "teknik program", "teknik önlisans"], "Teknik Önlisans"),
    (["harita ve kadastro", "harita mühendis", "geomatik"], "Harita/Geomatik"),
    (["orman mühendis", "ormancılık"], "Orman Mühendisliği"),
    (["turizm işletme", "turizm ve otel", "gastronomi"], "Turizm"),
    (["beden eğitim", "spor bilim", "antrenörlük"], "Spor Bilimleri"),
    (["coğrafya"], "Coğrafya"),
    (["tarih bölüm", "tarih fakülte"], "Tarih"),
    (["felsefe"], "Felsefe"),
    (["matematik bölüm", "matematik fakülte", "matematik,", ", matematik"], "Matematik"),
    (["fizik bölüm", "kimya bölüm", "biyoloji bölüm"], "Fen Bilimleri"),
    (["türk dili", "türkçe öğretmen", "türk edebiyat"], "Türk Dili/Edebiyatı"),
    (["polis", "güvenlik yönetim"], "Güvenlik/Emniyet"),
    # Genel — en son kontrol et
    (["dört yıllık lisans", "4 yıllık lisans",
      "herhangi bir lisans", "lisans düzeyinde eğitim",
      "lisans mezunu olm"], "Herhangi Lisans"),
    (["herhangi bir ön lisans", "herhangi bir önlisans",
      "ön lisans düzeyinde", "önlisans düzeyinde",
      "iki yıllık yüksekokul",
      "ön lisans program", "önlisans program",
      "ön lisans mezun"], "Herhangi Önlisans"),
]

# ─── YARDIMCI ────────────────────────────────────────────────────────

def _bolum_cıkar(t: str) -> str:
    bulunan = []
    for keywords, label in BOLUM_KALIPLARI:
        if any(k in t for k in keywords) and label not in bulunan:
            bulunan.append(label)
        if len(bulunan) >= 4:
            break
    return ", ".join(bulunan[:3])


def _akademik_unvan(t: str) -> str:
    if any(k in t for k in ["profesör", "professor"]):
        return "⛔ Profesör unvanı gerekli"
    if any(k in t for k in ["doçent", "doçentlik"]):
        return "⛔ Doçent unvanı gerekli"
    if any(k in t for k in ["dr. öğr. üyesi", "doktor öğretim üyesi", "yardımcı doçent"]):
        return "⛔ Dr. Öğr. Üyesi (PhD) gerekli"
    if "öğretim üyesi" in t:
        return "⛔ Öğretim Üyesi unvanı gerekli"
    if any(k in t for k in ["doktora mezun", "doktora derecesi", "phd"]):
        return "Doktora mezunu"
    if any(k in t for k in ["yüksek lisans mezun", "yüksek lisans derecesi"]):
        return "Yüksek lisans mezunu"
    if "öğretim görevlisi" in t:
        return "Öğretim Görevlisi"
    if "araştırma görevlisi" in t:
        return "Araştırma Görevlisi (Lisans)"
    return ""


def _kpss_cıkar(t: str) -> tuple[str, str]:
    """(kpss_sart_str, min_puan_str)"""
    if "kpss" not in t:
        return "KPSS şartı yok", ""

    # Puan türü — hem "P3" hem "KPSSP3" hem "KPSS P 3" formatlarını yakala
    puan_turu = ""
    for pt in ["p121","p120","p110","p101","p103","p93","p94","p87",
               "p86","p85","p84","p3","p10","p1","p2"]:
        # Farklı yazım biçimlerini dene
        patterns_pt = [
            rf'\b{pt}\b',           # P3
            rf'kpss\s*{pt}\b',      # KPSSP3
            rf'{pt}\s+puan',        # P3 puan
            rf'puan\s+türü\s*{pt}', # puan türü P3
        ]
        if any(re.search(p, t) for p in patterns_pt):
            puan_turu = pt.upper()
            break

    # Min puan — KPSS puanı 50-100 arasındadır
    # "en az 70", "70 ve üzeri", "70 puan" kalıpları
    min_puan = ""
    patterns = [
        r'(?:en az|en düşük|taban|asgari|minimum)[^\d]{0,15}(\d{2,3})',
        r'(\d{2,3})\s*(?:ve üzeri|ve üzerinde|puan ve)',
        r'kpss[^\d]{0,30}(\d{2,3})',
        r'(?:puan\s*almış\s*olmak)[^\d]{0,20}(\d{2,3})',
    ]
    for p in patterns:
        m = re.search(p, t)
        if m:
            val = int(m.group(1))
            if 40 <= val <= 100:  # Geçerli KPSS aralığı (Diyanet 50 puan istiyor)
                min_puan = str(val)
                break

    if puan_turu and min_puan:
        return f"KPSS {puan_turu} — min {min_puan}", min_puan
    elif puan_turu:
        return f"KPSS {puan_turu}", ""
    elif min_puan:
        return f"KPSS min {min_puan}", min_puan
    return "KPSS gerekli", ""


def _yas_siniri(t: str) -> str:
    """Yaş sınırını çıkar."""
    patterns = [
        # "35 yaşını doldurmamış olmak" — en yaygın kamu formatı
        r'(\d{2})\s*\(?(?:otuz|kırk|elli)\s*\w*\)?\s*yaş[ıi]n[ıi]\s*doldurmam[ıi]ş',
        r'(\d{2})\s*yaş[ıi]n[ıi]\s*doldurmam[ıi]ş',
        # "35 yaşından küçük/büyük"
        r'(\d{2})\s*yaş(?:[ıi]ndan|[ıi]nda|dan)?\s*(?:küçük|altında)',
        r'(\d{2})\s*yaşından\s*(?:büyük|küçük)\s*olmamak',
        # "en fazla 35 yaş" / "azami 35 yaş"
        r'(?:en fazla|en çok|azami)\s*(\d{2})\s*yaş',
        # "itibarıyla 35 yaşını"
        r'itibar[ıi]yla\s*(\d{2})\s*yaş',
        r'(\d{2})\s*yaş\s*(?:sınırı|şartı)',
        # "yaş sınırı: 35" / "yaş şartı 35"
        r'yaş\s*(?:sınırı|şartı)[:\s]+(\d{2})',
        # tablo formatı: "30 yaş" tek başına satırda
        r'^\s*(\d{2})\s*yaş\s*$',
    ]
    for p in patterns:
        m = re.search(p, t, re.MULTILINE)
        if m:
            yas = int(m.group(1))
            if 18 <= yas <= 65:
                return str(yas)
    return ""


def _ilan_tarihi(t: str) -> str:
    """İlan yayın tarihini çıkar."""
    patterns = [
        r'duyuru başlama tarihi\s*[:\-]?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})',
        r'ilan[ın]?\s*(?:tarihi|yayım)\s*[:\-]?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})',
        r'yayımland[ıi]ğ[ıi]\s*tarih\s*[:\-]?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})',
    ]
    for p in patterns:
        m = re.search(p, t)
        if m:
            return m.group(1)
    return ""


def _tecrube(t: str) -> str:
    """Tecrübe şartı: 'en az 3 yıl mesleki tecrübe'"""
    patterns = [
        r'en az\s*(\d+)\s*\(?[a-zğüşıöç]+\)?\s*yıl[lı]?\s*(?:mesleki\s*)?tecrübe',
        r'(\d+)\s*\(?[a-zğüşıöç]+\)?\s*yıl[lı]?\s*(?:fiili\s*)?(?:mesleki\s*)?tecrübe',
        r'(\d+)\s*yıl[lı]?\s*(?:iş\s*)?deneyim',
    ]
    for p in patterns:
        m = re.search(p, t)
        if m:
            yil = int(m.group(1))
            if 1 <= yil <= 20:
                return f"{yil} yıl"
    return ""


def _mezuniyet_seviyesi(t: str) -> str:
    """Ortaöğretim / Önlisans / Lisans / Y.Lisans / Doktora"""
    if any(k in t for k in ["doktora mezun", "doktora derecesi", "doktorasını tamamlamış",
                             "profesör", "doçent", "dr. öğr. üyesi", "doktor öğretim üyesi"]):
        return "Doktora"
    if any(k in t for k in ["tezli yüksek lisans", "yüksek lisans mezun", "yüksek lisans derecesi",
                             "yüksek lisans programı"]):
        return "Yüksek Lisans"
    if any(k in t for k in ["önlisans", "ön lisans", "meslek yüksekokul", "iki yıllık",
                             "herhangi bir ön lisans"]):
        return "Önlisans"
    if any(k in t for k in ["ortaöğretim", "lise veya dengi", "lise mezunu", "lise diploması"]):
        return "Ortaöğretim/Lise"
    if any(k in t for k in ["dört yıllık lisans", "4 yıllık lisans", "lisans mezun",
                             "lisans düzeyinde", "lisans programından", "lisans bölümünden",
                             "fakülte mezun", "fakültelerden mezun", "fakültesinden mezun"]):
        return "Lisans"
    return ""


def _sinav_tarihi(t: str) -> str:
    """Sınav tarihini çıkar"""
    # "11 Temmuz 2026", "20-24 Temmuz 2026" gibi
    aylar_tr = ["ocak","şubat","mart","nisan","mayıs","haziran",
                "temmuz","ağustos","eylül","ekim","kasım","aralık"]
    pattern = r'(\d{1,2}(?:\s*[-–]\s*\d{1,2})?\s+(?:' + '|'.join(aylar_tr) + r')\s+\d{4})'
    matches = re.findall(pattern, t)
    # Sınav tarihi genelde "sınav" kelimesiyle birlikte geçer
    for m in re.finditer(pattern, t):
        idx = m.start()
        bolge = t[max(0, idx-50):idx+5]
        if any(k in bolge for k in ["sınav", "mülakat", "sözlü"]):
            return m.group(0)
    return ""


def _basvuru_sekli(t: str) -> str:
    """Başvuru şeklini çıkar."""
    if 'e-devlet' in t or 'kariyer kapısı' in t or 'elektronik ortamda' in t:
        return 'e-Devlet / Online'
    if 'şahsen' in t and 'posta' in t:
        return 'Şahsen veya Posta'
    if 'şahsen' in t:
        return 'Şahsen'
    if 'posta' in t:
        return 'Posta'
    return ''


def _kontenjan(t: str) -> str:
    """Kaç kişi alınacak"""
    patterns = [
        r'toplam\s*(\d+)\s*(?:\([^)]+\)\s*)?(?:adet|kişi|personel)',
        r'(\d+)\s*(?:\([^)]+\)\s*)?(?:adet\s*)?(?:sözleşmeli|memur|personel|uzman|görevli)',
        r'(\d+)\s*kadro(?:da|ya|su)',
        r'(\d+)\s*(?:adet\s*)?pozisyon',
        # "20 (yirmi) Uzman" gibi format
        r'(\d+)\s*\([a-zğüşıöçA-ZĞÜŞİÖÇ]+\)\s*\w+\s*(?:uzman|memur|personel|görevli)',
    ]
    for p in patterns:
        m = re.search(p, t)
        if m:
            val = int(m.group(1))
            # Yıl sayıları (2020-2030) kontenjan olamaz
            if 1 <= val <= 5000 and not (2015 <= val <= 2035):
                return str(val)
    return ""


def _yabanci_dil(t: str) -> str:
    sonuclar = []
    for sinav in ["yds", "yokdil", "yökdil", "toefl", "ielts"]:
        if sinav in t:
            idx = t.find(sinav)
            bolge = t[max(0, idx-30):idx+100]
            puan = re.search(r'(\d{2,3})', bolge)
            label = sinav.upper().replace("YOKDIL", "YÖKDİL")
            if puan:
                val = int(puan.group(1))
                if 40 <= val <= 100:
                    sonuclar.append(f"{label} min {val}")
                    continue
            sonuclar.append(label)
    return ", ".join(sonuclar[:2])


def _ales(t: str) -> str:
    if "ales" not in t:
        return ""
    idx = t.find("ales")
    bolge = t[max(0, idx-20):idx+80]
    puan = re.search(r'(\d{2,3})', bolge)
    if puan:
        val = int(puan.group(1))
        if 50 <= val <= 100:
            return f"ALES min {val}"
    return "ALES gerekli"


def _diger(t: str) -> list:
    sartlar = []
    if any(k in t for k in ["adli sicil", "sabıka"]):
        sartlar.append("Adli sicil temiz")
    if any(k in t for k in ["askerlik", "askerliğini yapmış", "terhis"]):
        sartlar.append("Askerlik şartı")
    if "sürücü belgesi" in t or "ehliyet" in t:
        sartlar.append("Sürücü belgesi")
    return sartlar[:2]


# ─── TABLO OKUMA (kendisi öğrenen katman) ────────────────────────────

# Sütun adı → hangi alanla eşleştiği
# Yeni format gelince sadece buraya eklemek yeterli
TABLO_SUTUN_MAP = {
    # Nitelik / bölüm şartı
    "nitelik": "nitelik",
    "gerekli şart": "nitelik",
    "özel şart": "nitelik",
    "aranan nitelik": "nitelik",
    "aranılan nitelik": "nitelik",
    # KPSS puan türü
    "kpss puan türü": "kpss_turu",
    "puan türü": "kpss_turu",
    "kpss puantürü": "kpss_turu",
    # KPSS taban puan
    "kpss taban puan": "kpss_min",
    "taban puan": "kpss_min",
    "kpss tabanpuan": "kpss_min",
    "asgari puan": "kpss_min",
    # Kadro sayısı / kontenjan
    "kadro adedi": "kontenjan",
    "kadro sayısı": "kontenjan",
    "kontenjan": "kontenjan",
    "adet": "kontenjan",
    # Kadro unvanı
    "unvan": "unvan",
    "kadro unvanı": "unvan",
    "pozisyon": "unvan",
}


def _sutun_esles(baslik: str) -> str | None:
    """Sütun başlığını normalize edip eşleştir."""
    tr_map = {'İ': 'i', 'I': 'ı', 'Ğ': 'ğ', 'Ü': 'ü', 'Ş': 'ş', 'Ö': 'ö', 'Ç': 'ç'}
    b = baslik or ""
    for big, small in tr_map.items():
        b = b.replace(big, small)
    b = re.sub(r'\s+', ' ', b.lower()).strip()
    for anahtar, alan in TABLO_SUTUN_MAP.items():
        if anahtar in b:
            return alan
    return None


def parse_pdf_tables(pdf_bytes: bytes) -> dict:
    """
    pdfplumber ile tabloları oku, sütun adlarına göre alanları çıkar.
    Başarısız olursa boş dict döner, çağıran text-based parse'a düşer.
    """
    if not _PDFPLUMBER_OK:
        return {}

    toplanan = {
        "nitelik": [],
        "kpss_turu": [],
        "kpss_min": [],
        "kontenjan": [],
        "unvan": [],
    }

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    # İlk satır başlık mı?
                    baslik_satiri = table[0]
                    sutun_alanlari = [_sutun_esles(str(h)) for h in baslik_satiri]

                    if not any(sutun_alanlari):
                        continue

                    # Veri satırlarını topla
                    for satir in table[1:]:
                        for j, hucre in enumerate(satir):
                            if j >= len(sutun_alanlari):
                                break
                            alan = sutun_alanlari[j]
                            if alan and hucre:
                                deger = re.sub(r'\s+', ' ', str(hucre)).strip()
                                if deger:
                                    toplanan[alan].append(deger)
    except Exception:
        return {}

    if not any(toplanan.values()):
        return {}

    # Sonuçları birleştir
    result = {}

    # Nitelik → mezuniyet alanına parse et
    if toplanan["nitelik"]:
        nitelik_metni = " ".join(toplanan["nitelik"])
        t = _normalize(nitelik_metni)
        result["mezuniyet"] = _bolum_cıkar(t)
        result["mezuniyet_seviyesi"] = _mezuniyet_seviyesi(t)
        result["tecrube"] = _tecrube(t)
        result["yas_siniri"] = _yas_siniri(t)

    # KPSS puan türleri
    if toplanan["kpss_turu"]:
        turler = []
        for v in toplanan["kpss_turu"]:
            m = re.search(r'P(\d+)', v, re.IGNORECASE)
            if m:
                turler.append(f"P{m.group(1)}")
        if turler:
            result["_kpss_turler"] = list(dict.fromkeys(turler))

    # KPSS minimum puanlar
    if toplanan["kpss_min"]:
        puanlar = []
        for v in toplanan["kpss_min"]:
            m = re.search(r'(\d{2,3})', v)
            if m:
                val = int(m.group(1))
                if 40 <= val <= 100:
                    puanlar.append(val)
        if puanlar:
            result["_kpss_min_list"] = puanlar

    # Kontenjan
    if toplanan["kontenjan"]:
        toplam = 0
        for v in toplanan["kontenjan"]:
            m = re.search(r'(\d+)', v)
            if m:
                val = int(m.group(1))
                if 1 <= val <= 1000 and not (2015 <= val <= 2035):
                    toplam += val
        if toplam > 0:
            result["kontenjan"] = str(toplam)

    return result


# ─── ANA FONKSİYON ───────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Türkçe büyük harf + PDF tablo newline sorununu çöz.
    pdfplumber tablo hücrelerini satır başıyla ayırır, bu yüzden
    'inşaat\nmühendisliği' gibi bölünmüş kelimeler kalıpla eşleşmez.
    Tüm boşluk karakterlerini tek boşluğa indirgeriz."""
    tr_map = {'İ': 'i', 'I': 'ı', 'Ğ': 'ğ', 'Ü': 'ü', 'Ş': 'ş', 'Ö': 'ö', 'Ç': 'ç'}
    for big, small in tr_map.items():
        text = text.replace(big, small)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text

def parse_pdf_text(text: str) -> dict:
    t = _normalize(text)
    result = {
        "mezuniyet": "",
        "kpss_sart": "",
        "kpss_puan": "",
        "yas_siniri": "",
        "kontenjan": "",
        "ilan_tarihi": "",
        "basvuru_sekli": "",
        "tecrube": "",
        "mezuniyet_seviyesi": "",
        "sinav_tarihi": "",
    }

    # Bölüm
    result["mezuniyet"] = _bolum_cıkar(t)

    # Şartlar listesi
    sartlar = []

    # Akademik unvan (en kritik — en başa)
    unvan = _akademik_unvan(t)
    if unvan:
        sartlar.append(unvan)

    # KPSS
    kpss_str, kpss_puan = _kpss_cıkar(t)
    sartlar.append(kpss_str)
    result["kpss_puan"] = kpss_puan

    # Yabancı dil
    yd = _yabanci_dil(t)
    if yd:
        sartlar.append(yd)

    # ALES
    ales = _ales(t)
    if ales:
        sartlar.append(ales)

    # Diğer
    sartlar.extend(_diger(t))

    result["kpss_sart"] = " | ".join(sartlar)

    # Yaş sınırı
    result["yas_siniri"] = _yas_siniri(t)

    # Kontenjan
    result["kontenjan"] = _kontenjan(t)

    # İlan tarihi
    result["ilan_tarihi"] = _ilan_tarihi(t)

    # Başvuru şekli
    result["basvuru_sekli"] = _basvuru_sekli(t)

    # Tecrübe şartı
    result["tecrube"] = _tecrube(t)

    # Mezuniyet seviyesi
    result["mezuniyet_seviyesi"] = _mezuniyet_seviyesi(t)

    # Sınav tarihi
    result["sinav_tarihi"] = _sinav_tarihi(t)

    return result
