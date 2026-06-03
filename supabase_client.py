"""
Supabase REST API istemcisi — requests tabanlı, SSL verify=False.
"""
import os, requests, warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

load_dotenv()

_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

_HEADERS = {
    "apikey": _KEY,
    "Authorization": f"Bearer {_KEY}",
    "Content-Type": "application/json",
}


def _rest(table: str) -> str:
    return f"{_URL}/rest/v1/{table}"


def sb_exists(table: str, hash_val: str) -> bool:
    r = requests.get(
        _rest(table),
        headers={**_HEADERS, "Prefer": "count=exact"},
        params={"hash": f"eq.{hash_val}", "select": "id"},
        verify=False, timeout=10,
    )
    r.raise_for_status()
    total = int(r.headers.get("content-range", "0/0").split("/")[-1])
    return total > 0


def sb_upsert(table: str, data: dict) -> bool:
    """Varsa güncelle, yoksa ekle. True = başarı."""
    r = requests.post(
        _rest(table),
        headers={**_HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
        json=data,
        verify=False, timeout=15,
    )
    if r.status_code in (200, 201, 204):
        return True
    print(f"  [Supabase] upsert hata {r.status_code}: {r.text[:200]}")
    return False


def sb_update(table: str, match: dict, data: dict) -> bool:
    params = {k: f"eq.{v}" for k, v in match.items()}
    r = requests.patch(
        _rest(table),
        headers={**_HEADERS, "Prefer": "return=minimal"},
        params=params,
        json=data,
        verify=False, timeout=15,
    )
    if r.status_code in (200, 204):
        return True
    print(f"  [Supabase] update hata {r.status_code}: {r.text[:200]}")
    return False


def sb_fetch(table: str, params: dict = None) -> list:
    r = requests.get(
        _rest(table),
        headers={**_HEADERS, "Prefer": ""},
        params=params,
        verify=False, timeout=15,
    )
    r.raise_for_status()
    return r.json()


def sb_ping() -> bool:
    """Bağlantı testi."""
    try:
        r = requests.get(
            _rest("jobs"),
            headers={**_HEADERS, "Prefer": "count=exact"},
            params={"select": "id", "limit": "1"},
            verify=False, timeout=8,
        )
        return r.status_code in (200, 206)
    except Exception as e:
        print(f"  [Supabase] bağlantı hatası: {e}")
        return False
