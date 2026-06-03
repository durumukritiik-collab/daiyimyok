"""
Kullanım:
  python check_match.py
  python check_match.py --bolum Psikoloji --kpss-puan 78 --kpss-turu P3 --yas 29 --mezuniyet Lisans
  python check_match.py --bolum Psikoloji --kpss-puan 78 --kpss-turu P3 --yas 29 --mezuniyet Lisans --min-skor 60
  python check_match.py --bolum Hukuk --kpss-puan 85 --kpss-turu P1 --yas 32 --mezuniyet Lisans --tecrube 2
"""

import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")

from matcher import UserProfile, find_matches

MEZUNIYET_SEVIYELERI = ["Ortaöğretim/Lise", "Önlisans", "Lisans", "Yüksek Lisans", "Doktora"]
KPSS_TURLERI = ["P1", "P2", "P3", "P10", "P86", "P87", "P93", "P94"]


def parse_args():
    p = argparse.ArgumentParser(description="Kamu ilanı uygunluk motoru")
    p.add_argument("--bolum", help="Mezun olduğunuz bölüm (ör: Psikoloji)")
    p.add_argument("--kpss-puan", type=float, help="KPSS puanınız (ör: 78.5)")
    p.add_argument("--kpss-turu", help="KPSS puan türü (ör: P3)")
    p.add_argument("--yas", type=int, help="Yaşınız")
    p.add_argument("--mezuniyet",
                   choices=MEZUNIYET_SEVIYELERI,
                   help="Mezuniyet seviyeniz")
    p.add_argument("--tecrube", type=int, default=0, help="Mesleki tecrübe (yıl, varsayılan: 0)")
    p.add_argument("--min-skor", type=int, default=50,
                   help="Minimum uygunluk skoru 0-100 (varsayılan: 50)")
    p.add_argument("--limit", type=int, default=20, help="Gösterilecek max ilan sayısı")
    return p.parse_args()


def ask(prompt: str, default: str = "") -> str:
    val = input(prompt).strip()
    return val if val else default


def interactive_profile() -> tuple[UserProfile, int, int]:
    print("\n" + "═" * 55)
    print("  Kamu Kariyer Radarı — Uygunluk Kontrolü")
    print("═" * 55)
    print("  Boş bırakırsanız varsayılan değer kullanılır.\n")

    bolum = ask("  Bölümünüz (ör: Psikoloji): ")
    kpss_puan = float(ask("  KPSS puanınız (ör: 78.5): ", "0") or "0")
    kpss_turu = ask("  KPSS puan türü (ör: P3): ", "").upper()
    yas = int(ask("  Yaşınız: ", "25") or "25")

    print(f"  Mezuniyet seviyeleri: {', '.join(MEZUNIYET_SEVIYELERI)}")
    mezuniyet = ask("  Mezuniyet seviyeniz: ", "Lisans")

    tecrube = int(ask("  Mesleki tecrübe (yıl, 0=tecrübesiz): ", "0") or "0")
    min_skor = int(ask("  Min. uygunluk skoru (0-100, varsayılan 50): ", "50") or "50")
    limit = int(ask("  Kaç sonuç gösterilsin? (varsayılan 20): ", "20") or "20")

    profile = UserProfile(
        bolum=bolum,
        kpss_puan=kpss_puan,
        kpss_turu=kpss_turu,
        yas=yas,
        mezuniyet_seviyesi=mezuniyet,
        tecrube_yil=tecrube,
    )
    return profile, min_skor, limit


def skor_cubugu(pct: int, width: int = 20) -> str:
    filled = round(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct}%"


def label_renk(label: str) -> str:
    renk = {
        "Mükemmel": "\033[92m",   # Yeşil
        "Uygun":    "\033[32m",   # Koyu yeşil
        "Kısmi":    "\033[93m",   # Sarı
        "Uyumsuz":  "\033[91m",   # Kırmızı
    }
    sifirla = "\033[0m"
    return renk.get(label, "") + label + sifirla


def print_results(results, profile: UserProfile, limit: int):
    print("\n" + "═" * 65)
    print(f"  Profil: {profile.bolum} | KPSS {profile.kpss_turu} {profile.kpss_puan:.0f} | "
          f"Yaş {profile.yas} | {profile.mezuniyet_seviyesi}"
          + (f" | {profile.tecrube_yil} yıl tecrübe" if profile.tecrube_yil else ""))
    print(f"  Toplam {len(results)} ilan bulundu, ilk {min(limit, len(results))} gösteriliyor")
    print("═" * 65 + "\n")

    for i, r in enumerate(results[:limit], 1):
        job = r.job
        org = job.get("organization") or ""
        title = job.get("title") or ""
        deadline = job.get("application_deadline") or ""
        url = job.get("url") or ""
        kontenjan = job.get("kontenjan") or ""
        sinav = job.get("sinav_tarihi") or ""

        print(f"  #{i:02d}  {skor_cubugu(r.pct)}  {label_renk(r.label)}")
        print(f"  Kurum   : {org}")
        print(f"  İlan    : {title[:80]}")
        if kontenjan:
            print(f"  Kontenjan: {kontenjan} kişi")
        if deadline:
            print(f"  Son başvuru: {deadline}")
        if sinav:
            print(f"  Sınav tarihi: {sinav}")
        if url:
            print(f"  URL     : {url}")

        print("  " + "─" * 60)
        for reason in r.reasons:
            print(f"    {reason}")

        print()

    # Özet istatistik
    mukemmel = sum(1 for r in results if r.pct >= 85)
    uygun     = sum(1 for r in results if 70 <= r.pct < 85)
    kismi     = sum(1 for r in results if 50 <= r.pct < 70)

    print("═" * 65)
    print(f"  Özet: {mukemmel} Mükemmel  {uygun} Uygun  {kismi} Kısmi")
    print("═" * 65 + "\n")


def main():
    args = parse_args()

    if args.bolum:
        profile = UserProfile(
            bolum=args.bolum,
            kpss_puan=args.kpss_puan or 0,
            kpss_turu=(args.kpss_turu or "").upper(),
            yas=args.yas or 25,
            mezuniyet_seviyesi=args.mezuniyet or "Lisans",
            tecrube_yil=args.tecrube,
        )
        min_skor = args.min_skor
        limit = args.limit
    else:
        profile, min_skor, limit = interactive_profile()

    print(f"\n  İlanlar taranıyor (min skor: {min_skor})...")
    results = find_matches(profile, min_score=min_skor)
    print_results(results, profile, limit)


if __name__ == "__main__":
    main()
