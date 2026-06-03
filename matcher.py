import re
import sqlite3
from dataclasses import dataclass, field

DB_PATH = "kamu_radar.db"

MEZUNIYET_HIYERARSI = {
    "Ortaöğretim/Lise": 1,
    "Önlisans": 2,
    "Lisans": 3,
    "Yüksek Lisans": 4,
    "Doktora": 5,
}

# Kullanıcı bölümü → DB'de aranacak anahtar kelimeler
BOLUM_ESLEME = {
    "psikoloji":          ["psikoloji"],
    "hukuk":              ["hukuk"],
    "tıp":                ["tıp", "tabip"],
    "hemşirelik":         ["hemşirelik"],
    "mühendislik":        ["mühendislik"],
    "mimarlık":           ["mimarlık"],
    "iktisat":            ["iktisat", "iİBF", "ekonomi"],
    "işletme":            ["işletme"],
    "muhasebe":           ["muhasebe", "maliye"],
    "kamu yönetimi":      ["kamu yönetim"],
    "sosyoloji":          ["sosyoloji"],
    "sosyal hizmet":      ["sosyal hizmet", "sosyal çalışma"],
    "istatistik":         ["istatistik"],
    "iletişim":           ["iletişim"],
    "eğitim":             ["eğitim", "PDR", "öğretmen"],
    "bilgisayar":         ["bilgisayar", "bilişim"],
    "veterinerlik":       ["veteriner"],
    "ziraat":             ["ziraat"],
    "ekonometri":         ["ekonometri"],
    "biyoloji":           ["biyoloji"],
    "matematik":          ["matematik"],
    "fizik":              ["fizik"],
    "kimya":              ["kimya"],
    "coğrafya":           ["coğrafya"],
    "tarih":              ["tarih"],
    "felsefe":            ["felsefe"],
    "eczacılık":          ["eczacılık"],
    "fizyoterapi":        ["fizyoterapi"],
}


@dataclass
class UserProfile:
    bolum: str               # "Psikoloji"
    kpss_puan: float         # 78.0
    kpss_turu: str           # "P3"
    yas: int                 # 29
    mezuniyet_seviyesi: str  # "Lisans"
    tecrube_yil: int = 0     # 0 = tecrübesiz


@dataclass
class MatchResult:
    job: dict
    score: int
    max_score: int
    reasons: list = field(default_factory=list)

    @property
    def pct(self) -> int:
        return round(self.score / self.max_score * 100)

    @property
    def label(self) -> str:
        p = self.pct
        if p >= 85:
            return "Mükemmel"
        if p >= 70:
            return "Uygun"
        if p >= 50:
            return "Kısmi"
        return "Uyumsuz"


# ─── KRİTER FONKSİYONLARI ────────────────────────────────────────────

def _bolum_uyumu(job_mezuniyet: str, user_bolum: str) -> tuple[bool, bool, str]:
    """(uygun_mu, kesin_mi, açıklama)"""
    if not job_mezuniyet or job_mezuniyet.strip() == "":
        return True, False, "⚠️  Bölüm şartı PDF'den okunamadı"

    jm = job_mezuniyet.lower()

    if "herhangi lisans" in jm:
        return True, True, "✅ Herhangi lisans mezunu kabul"

    ub = user_bolum.lower().strip()
    # Önce doğrudan eşleşme
    if ub in jm:
        return True, True, f"✅ Bölüm uyuyor ({job_mezuniyet})"

    # Alternatif anahtar kelimeler
    ekstralar = BOLUM_ESLEME.get(ub, [])
    for k in ekstralar:
        if k.lower() in jm:
            return True, True, f"✅ Bölüm uyuyor ({job_mezuniyet})"

    return False, True, f"❌ Bölüm uyuşmuyor (aranan: {job_mezuniyet})"


def _kpss_uyumu(kpss_sart: str, kpss_puan_str: str,
                user_puan: float, user_turu: str) -> tuple[bool, bool, str]:
    """(uygun_mu, kesin_mi, açıklama)"""
    if not kpss_sart:
        return True, False, "⚠️  KPSS şartı PDF'den okunamadı"

    # Akademik unvan şartı (⛔) — Profesör/Doçent/Dr. Öğr. Üyesi gerektirenler
    if "⛔" in kpss_sart:
        unvan = kpss_sart.split("|")[0].strip()
        return False, True, f"❌ {unvan}"

    sart_lower = kpss_sart.lower()
    if "kpss şartı yok" in sart_lower:
        return True, True, "✅ KPSS şartı yok"

    # Puan türü
    job_turu = ""
    m = re.search(r'\bP(\d+)\b', kpss_sart, re.IGNORECASE)
    if m:
        job_turu = f"P{m.group(1)}"

    if job_turu and user_turu and job_turu.upper() != user_turu.upper():
        return False, True, (
            f"❌ KPSS puan türü uyuşmuyor (aranan: {job_turu}, sizin: {user_turu})"
        )

    # Min puan
    min_puan = 0.0
    if kpss_puan_str:
        try:
            min_puan = float(kpss_puan_str)
        except ValueError:
            pass

    if min_puan > 0:
        if user_puan >= min_puan:
            return True, True, f"✅ KPSS puanı yeterli ({user_puan:.0f} ≥ {min_puan:.0f})"
        else:
            return False, True, (
                f"❌ KPSS puanı yetersiz (aranan: {min_puan:.0f}, sizin: {user_puan:.0f})"
            )

    # KPSS gerekli ama skor bilinmiyor
    return True, False, f"⚠️  KPSS gerekli, min puan belirtilmemiş ({kpss_sart})"


def _yas_uyumu(yas_siniri_str: str, user_yas: int) -> tuple[bool, bool, str]:
    if not yas_siniri_str:
        return True, False, "⚠️  Yaş sınırı belirtilmemiş"
    try:
        limit = int(yas_siniri_str)
        if user_yas <= limit:
            return True, True, f"✅ Yaş uygun ({user_yas} ≤ {limit})"
        return False, True, f"❌ Yaş sınırı aşılmış (max {limit}, sizin: {user_yas})"
    except ValueError:
        return True, False, "⚠️  Yaş sınırı okunamadı"


def _mezuniyet_uyumu(job_seviye: str, user_seviye: str) -> tuple[bool, bool, str]:
    if not job_seviye:
        return True, False, "⚠️  Mezuniyet seviyesi belirtilmemiş"
    job_lvl = MEZUNIYET_HIYERARSI.get(job_seviye, 0)
    user_lvl = MEZUNIYET_HIYERARSI.get(user_seviye, 0)
    if user_lvl == 0:
        return True, False, f"⚠️  Mezuniyet seviyesi doğrulanamadı ({job_seviye})"
    if user_lvl >= job_lvl:
        return True, True, f"✅ Mezuniyet seviyesi uygun ({user_seviye} ≥ {job_seviye})"
    return False, True, f"❌ Mezuniyet yetersiz (aranan: {job_seviye}, sizin: {user_seviye})"


def _tecrube_uyumu(job_tecrube: str, user_yil: int) -> tuple[bool, bool, str]:
    if not job_tecrube:
        return True, True, "✅ Tecrübe şartı yok"
    m = re.search(r'(\d+)', job_tecrube)
    if m:
        aranan = int(m.group(1))
        if user_yil >= aranan:
            return True, True, f"✅ Tecrübe yeterli ({user_yil} yıl ≥ {aranan} yıl)"
        return False, True, f"❌ Tecrübe yetersiz (aranan: {aranan} yıl, sizin: {user_yil} yıl)"
    return True, False, f"⚠️  Tecrübe şartı var ama miktar belirsiz ({job_tecrube})"


# ─── SKORLAMA ────────────────────────────────────────────────────────

# Kriter → (ağırlık, DB alanları)
KRITERLER = [
    ("bolum",      35, "mezuniyet",          ""),
    ("kpss",       30, "kpss_sart",          "kpss_puan"),
    ("yas",        15, "yas_siniri",          ""),
    ("mezuniyet",  12, "mezuniyet_seviyesi",  ""),
    ("tecrube",     8, "tecrube",             ""),
]


def score_job(job: dict, profile: UserProfile) -> MatchResult:
    """
    Belirsiz (⚠️) kriterler yarım puan alır — bu sayede PDF'i okunamamış
    ilanlar düşük skorla kalır ve "kesin uyumlu" ilanlar öne geçer.
    """
    score = 0
    reasons = []

    ok, kesin, msg = _bolum_uyumu(job.get("mezuniyet", ""), profile.bolum)
    reasons.append(msg)
    if ok:
        score += 35 if kesin else 17

    ok, kesin, msg = _kpss_uyumu(
        job.get("kpss_sart", ""),
        job.get("kpss_puan", ""),
        profile.kpss_puan,
        profile.kpss_turu,
    )
    reasons.append(msg)
    if ok:
        score += 30 if kesin else 15

    ok, kesin, msg = _yas_uyumu(job.get("yas_siniri", ""), profile.yas)
    reasons.append(msg)
    if ok:
        score += 15 if kesin else 7

    ok, kesin, msg = _mezuniyet_uyumu(
        job.get("mezuniyet_seviyesi", ""), profile.mezuniyet_seviyesi
    )
    reasons.append(msg)
    if ok:
        score += 12 if kesin else 6

    ok, kesin, msg = _tecrube_uyumu(job.get("tecrube", ""), profile.tecrube_yil)
    reasons.append(msg)
    if ok:
        score += 8 if kesin else 4

    return MatchResult(job=job, score=score, max_score=100, reasons=reasons)


# ─── DB SORGUSU ──────────────────────────────────────────────────────

def find_matches(profile: UserProfile, min_score: int = 50) -> list[MatchResult]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT id, title, organization, employment_type, application_deadline,
               url, source, positions,
               mezuniyet, kpss_sart, kpss_puan, yas_siniri,
               tecrube, mezuniyet_seviyesi, sinav_tarihi, kontenjan
        FROM jobs
        ORDER BY created_at DESC
    """)
    rows = c.fetchall()
    conn.close()

    results = []
    for row in rows:
        job = dict(row)
        result = score_job(job, profile)
        if result.score >= min_score:
            results.append(result)

    results.sort(key=lambda r: r.score, reverse=True)
    return results
