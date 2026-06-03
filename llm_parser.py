"""
DayımYok — Groq destekli kamu ilan analiz motoru.

Groq'a sistem promptu ile iş danışmanı kimliği verilir.
İki görev:
  1. groq_analiz()      — tam yapılandırılmış ilan analizi (JSON)
  2. groq_etiket_cıkar() — arama etiketleri (virgülle ayrılmış liste)
"""

import os, re, json, time, requests, warnings
warnings.filterwarnings("ignore")

GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"
MODEL_HIZLI = "llama-3.1-8b-instant"    # alan çıkarımı — 14400/gün
MODEL_AKIL  = "llama-3.3-70b-versatile" # derin analiz — 1000/gün

# Sistem promptu dosyadan yükle
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "groq_system_prompt.txt")
try:
    with open(_PROMPT_PATH, encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    SYSTEM_PROMPT = "Sen Türkiye kamu iş ilanlarını analiz eden bir kariyer asistanısın."


def _api_key() -> str:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("GROQ_API_KEY .env dosyasında bulunamadı")
    return key


def _groq_call(user_msg: str, model: str, max_tokens: int = 800) -> str:
    """Groq API'ye istek at, ham yanıtı döndür. Rate limit'te bekle."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    for deneme in range(3):
        try:
            r = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {_api_key()}",
                         "Content-Type": "application/json"},
                json=payload, timeout=30, verify=False,
            )
            if r.status_code == 429:
                bekle = 30 * (2 ** deneme)
                print(f"  [Groq] Rate limit — {bekle}sn bekleniyor ({deneme+1}/3)...")
                time.sleep(bekle)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if "429" not in str(e):
                print(f"  [Groq] Hata: {e}")
                return ""
    return ""


# ─── 1) ARAMA ETİKETLERİ ─────────────────────────────────────────────

ETIKET_SORU = """Bu ilanın PDF metninden arama etiketleri çıkar.

İŞ ARAYANLARIN ARAYABİLECEĞİ TÜM KELİMELERİ listele:
- Tüm bölüm/alan adları (spesifik: "gıda mühendisliği" değil "mühendislik")
- Tüm pozisyon/unvan adları
- Kurumun faaliyet alanı
- Önemli anahtar kelimeler

SADECE virgülle ayrılmış liste döndür. Başka hiçbir şey yazma.

PDF METNİ:
{metin}"""


def groq_etiket_cıkar(pdf_text: str) -> str:
    """PDF'den arama etiketleri çıkar. Sadece metinde gerçekten geçenler."""
    if not pdf_text or len(pdf_text) < 100:
        return ""

    yanit = _groq_call(
        ETIKET_SORU.format(metin=pdf_text[:8000]),
        model=MODEL_AKIL,
        max_tokens=400,
    )
    if not yanit:
        return ""

    # İlk satırı al
    yanit = yanit.split("\n")[0].strip().lower()

    # Doğrulama: sadece metinde geçen etiketleri tut
    metin_lower = pdf_text.lower()
    etiketler = [e.strip() for e in yanit.split(",") if len(e.strip()) > 2]
    gecerli = [e for e in etiketler if e in metin_lower]

    return ", ".join(gecerli)


# ─── 2) KAPSAMLI İLAN ANALİZİ ────────────────────────────────────────

ANALIZ_SORU = """Aşağıdaki kamu ilanı PDF metnini analiz et.

İş arayanlar için şu bilgileri çıkar ve JSON olarak döndür:

{{
  "pozisyonlar": [
    {{
      "unvan": "pozisyon adı",
      "bolum": "spesifik bölüm/alan adı (virgülle ayır)",
      "mezuniyet_seviyesi": "Lise/Önlisans/Lisans/Yüksek Lisans/Doktora",
      "kpss_turu": "P3 gibi, yoksa boş",
      "kpss_min": "sayı, yoksa boş",
      "yas_max": "sayı, yoksa boş",
      "kontenjan": "sayı",
      "akademik_unvan_gerekli": true/false
    }}
  ],
  "toplam_kontenjan": "sayı",
  "son_basvuru": "tarih",
  "sinav_tarihi": "tarih veya boş",
  "basvuru_sekli": "e-Devlet/Kariyer Kapısı/Şahsen/Posta",
  "tecrube_sart": "var/yok",
  "ozet": "iş arayana 1 cümle özet"
}}

PDF METNİ:
{metin}"""


def groq_analiz(pdf_text: str) -> dict:
    """İlanı tam analiz et — tüm pozisyonlar dahil."""
    if not pdf_text or len(pdf_text) < 100:
        return {}

    yanit = _groq_call(
        ANALIZ_SORU.format(metin=pdf_text[:10000]),
        model=MODEL_AKIL,
        max_tokens=1000,
    )
    if not yanit:
        return {}

    try:
        m = re.search(r'\{.*\}', yanit, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    return {}


# ─── 3) BASIT ALAN DOLDURMA (hızlı model) ────────────────────────────

DOLDUR_SORU = """Bu kamu ilanından şu alanları çıkar. SADECE JSON döndür.

{{
  "mezuniyet": "bölüm adları virgülle (spesifik yaz)",
  "mezuniyet_seviyesi": "Lise/Önlisans/Lisans/Yüksek Lisans/Doktora",
  "kpss_puan": "minimum sayı, yoksa boş",
  "yas_siniri": "max yaş sayısı, yoksa boş",
  "kontenjan": "toplam kişi sayısı, yoksa boş"
}}

PDF METNİ:
{metin}"""

_BOZUK = ["örnek:", "boş string", "virgülle ayır", "sadece:", "ör:"]


def llm_parse(pdf_text: str) -> dict:
    """Boş alanlar için hızlı model ile doldur."""
    yanit = _groq_call(
        DOLDUR_SORU.format(metin=pdf_text[:5000]),
        model=MODEL_HIZLI,
        max_tokens=200,
    )
    if not yanit:
        return {}
    try:
        m = re.search(r'\{.*\}', yanit, re.DOTALL)
        if not m:
            return {}
        sonuc = json.loads(m.group(0))
        gecerli = ["mezuniyet", "mezuniyet_seviyesi", "kpss_puan", "yas_siniri", "kontenjan"]
        return {k: str(v).strip() for k, v in sonuc.items()
                if k in gecerli and v
                and not any(b in str(v).lower() for b in _BOZUK)
                and len(str(v)) < 200}
    except Exception:
        return {}


def llm_parse_if_needed(mevcut: dict, pdf_text: str) -> dict:
    """Mezuniyet boşsa doldur."""
    if mevcut.get("mezuniyet"):
        return mevcut
    print(f"  [Groq] mezuniyet boş → dolduruluyor...")
    time.sleep(2)
    llm = llm_parse(pdf_text)
    if not llm:
        return mevcut
    guncellenmis = mevcut.copy()
    for alan, deger in llm.items():
        if deger and not mevcut.get(alan):
            guncellenmis[alan] = deger
            print(f"  [Groq] + {alan}: '{deger}'")
    return guncellenmis
