import sqlite3
import hashlib
import re
from datetime import datetime, date

try:
    from supabase_client import sb_upsert, sb_exists, sb_update
    _SB_OK = True
except Exception:
    _SB_OK = False

DB_PATH = "kamu_radar.db"

# Türkçe ay adları → rakam
_AY = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}


def _parse_deadline(text: str) -> str | None:
    """Son başvuru tarihini DATE stringe çevirir (YYYY-MM-DD). Başaramazsa None."""
    if not text:
        return None
    text = text.strip().lower()

    # "1 Temmuz - 10 Temmuz" → son tarihi al (en sağdaki)
    # "15 Haziran 2026", "15 haziran" gibi
    parts = re.split(r"[-–]", text)
    son = parts[-1].strip()

    m = re.search(r"(\d{1,2})\s+([a-zşığüöç]+)\s*(\d{4})?", son)
    if not m:
        return None
    gun = int(m.group(1))
    ay_str = m.group(2)
    yil = int(m.group(3)) if m.group(3) else date.today().year

    ay = _AY.get(ay_str)
    if not ay:
        return None

    try:
        return date(yil, ay, gun).isoformat()
    except ValueError:
        return None


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            organization TEXT,
            city TEXT,
            employment_type TEXT,
            application_deadline TEXT,
            url TEXT,
            hash TEXT UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            positions TEXT DEFAULT "",
            mezuniyet TEXT DEFAULT "",
            kpss_sart TEXT DEFAULT "",
            kpss_puan TEXT DEFAULT "",
            yas_siniri TEXT DEFAULT "",
            kontenjan TEXT DEFAULT "",
            ilan_tarihi TEXT DEFAULT "",
            basvuru_sekli TEXT DEFAULT "",
            tecrube TEXT DEFAULT "",
            mezuniyet_seviyesi TEXT DEFAULT "",
            sinav_tarihi TEXT DEFAULT "",
            pdf_text TEXT DEFAULT "",
            arama_etiketleri TEXT DEFAULT "",
            pozisyonlar_json TEXT DEFAULT "",
            deadline_date TEXT DEFAULT "",
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_chat_id TEXT NOT NULL,
            keywords TEXT,
            cities TEXT,
            institution_types TEXT,
            notification_enabled INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS notifications_sent (
            job_hash TEXT,
            profile_id INTEGER,
            sent_at TEXT,
            PRIMARY KEY (job_hash, profile_id)
        );
    """)
    conn.commit()
    conn.close()


def make_hash(title: str, organization: str, deadline: str) -> str:
    raw = f"{title}|{organization}|{deadline}".lower().strip()
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def is_duplicate(hash_val: str) -> bool:
    if _SB_OK:
        try:
            return sb_exists("jobs", hash_val)
        except Exception:
            pass
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM jobs WHERE hash = ?", (hash_val,))
    result = c.fetchone()
    conn.close()
    return result is not None


def _to_sb(job: dict) -> dict:
    return {
        "id":                   job["hash"],
        "hash":                 job["hash"],
        "source":               job.get("source", ""),
        "title":                job.get("title", ""),
        "organization":         job.get("organization", ""),
        "city":                 job.get("city", ""),
        "employment_type":      job.get("employment_type", ""),
        "application_deadline": job.get("application_deadline", ""),
        "url":                  job.get("url", ""),
        "positions":            job.get("positions", ""),
        "mezuniyet":            job.get("mezuniyet", ""),
        "kpss_sart":            job.get("kpss_sart", ""),
        "kpss_puan":            job.get("kpss_puan", ""),
        "yas_siniri":           job.get("yas_siniri", ""),
        "kontenjan":            job.get("kontenjan", ""),
        "ilan_tarihi":          job.get("ilan_tarihi", ""),
        "basvuru_sekli":        job.get("basvuru_sekli", ""),
        "tecrube":              job.get("tecrube", ""),
        "mezuniyet_seviyesi":   job.get("mezuniyet_seviyesi", ""),
        "sinav_tarihi":         job.get("sinav_tarihi", ""),
        "pdf_text":             job.get("pdf_text", ""),
        "arama_etiketleri":     job.get("arama_etiketleri", ""),
        "pozisyonlar_json":     job.get("pozisyonlar_json", ""),
        "deadline_date":        job.get("deadline_date") or _parse_deadline(job.get("application_deadline", "")),
        "is_active":            job.get("is_active", 1),
        "created_at":           datetime.now().isoformat(),
    }


def insert_job(job: dict) -> bool:
    """True = yeni ilan eklendi, False = duplicate."""
    if is_duplicate(job["hash"]):
        return False

    deadline_date = _parse_deadline(job.get("application_deadline", ""))

    # SQLite
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO jobs (id, source, title, organization, city,
                              employment_type, application_deadline, url, hash,
                              positions, deadline_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job["hash"],
            job.get("source", ""),
            job.get("title", ""),
            job.get("organization", ""),
            job.get("city", ""),
            job.get("employment_type", ""),
            job.get("application_deadline", ""),
            job.get("url", ""),
            job["hash"],
            job.get("positions", ""),
            deadline_date,
            datetime.now().isoformat(),
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    finally:
        if conn:
            conn.close()

    # Supabase
    if _SB_OK:
        sb_data = _to_sb({**job, "deadline_date": deadline_date})
        try:
            sb_upsert("jobs", sb_data)
        except Exception as e:
            print(f"  [Supabase] insert hata: {e}")

    return True


def update_job_fields(job_id: str, fields: dict) -> None:
    """PDF analizinden gelen alanları güncelle (SQLite + Supabase)."""
    conn = get_connection()
    c = conn.cursor()
    set_parts = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    c.execute(f"UPDATE jobs SET {set_parts} WHERE id = ?", values)
    conn.commit()
    conn.close()

    if _SB_OK:
        try:
            sb_update("jobs", {"id": job_id}, fields)
        except Exception as e:
            print(f"  [Supabase] update hata: {e}")


def get_all_profiles():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM profiles WHERE notification_enabled = 1")
    rows = c.fetchall()
    conn.close()
    return rows


def mark_notified(job_hash: str, profile_id: int):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO notifications_sent (job_hash, profile_id, sent_at)
            VALUES (?, ?, ?)
        """, (job_hash, profile_id, datetime.now().isoformat()))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


def already_notified(job_hash: str, profile_id: int) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM notifications_sent WHERE job_hash = ? AND profile_id = ?",
              (job_hash, profile_id))
    result = c.fetchone()
    conn.close()
    return result is not None


def get_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM jobs")
    total = c.fetchone()[0]
    c.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source")
    by_source = c.fetchall()
    conn.close()
    return total, by_source
