import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

import db
from scrapers import kamuilan, memurlar
from ilan_processor import process_job

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SOURCES = [
    ("Kamu İlan Portalı", kamuilan),
    ("Memurlar.net", memurlar),
]

def match_job(job: dict, keywords: list, cities: list, institution_types: list) -> bool:
    text = f"{job['title']} {job['organization']}".lower()

    if keywords and not any(k.lower() in text for k in keywords):
        return False
    if cities and job.get("city") and not any(c.lower() in job["city"].lower() for c in cities):
        return False

    return True

async def send_telegram(bot: Bot, chat_id: str, message: str):
    try:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
    except Exception as e:
        print(f"Telegram gönderim hatası: {e}")

async def run():
    db.init_db()
    bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

    total_scraped = 0
    total_new = 0
    source_stats = {}

    print(f"\n{'='*50}")
    print(f"Kamu Kariyer Radarı — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    all_new_jobs = []

    for source_name, module in SOURCES:
        print(f"[{source_name}] Taranıyor...")
        jobs = module.scrape()
        print(f"[{source_name}] {len(jobs)} ilan bulundu")

        new_count = 0
        for job in jobs:
            total_scraped += 1
            is_new = db.insert_job(job)
            if is_new:
                new_count += 1
                total_new += 1
                all_new_jobs.append(job)
                # Kamuilan ilanları için otomatik PDF analizi
                if job.get("source") == "kamuilan" and job.get("url"):
                    process_job(
                        job["hash"],  # id = hash
                        job["url"],
                        job.get("title", ""),
                        job.get("organization", ""),
                    )

        source_stats[source_name] = {"total": len(jobs), "new": new_count}
        print(f"[{source_name}] {new_count} yeni ilan eklendi\n")

    # Log özeti
    print(f"{'='*50}")
    print(f"ÖZET — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Toplam taranan: {total_scraped}")
    print(f"Yeni ilan: {total_new}")
    for src, stat in source_stats.items():
        print(f"  {src}: {stat['new']} yeni / {stat['total']} toplam")

    total_db, by_source = db.get_stats()
    print(f"Veritabanı toplamı: {total_db} ilan")
    print(f"{'='*50}\n")

    # Telegram bildirimi
    if bot and TELEGRAM_CHAT_ID and all_new_jobs:
        summary = (
            f"📡 <b>Kamu Kariyer Radarı</b>\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"✅ <b>{total_new} yeni ilan</b> bulundu\n\n"
        )

        # İlk 5 ilanı gönder
        for job in all_new_jobs[:5]:
            summary += (
                f"🏛 <b>{job['organization']}</b>\n"
                f"📌 {job['title']}\n"
                f"🔗 {job['url']}\n\n"
            )

        if total_new > 5:
            summary += f"...ve {total_new - 5} ilan daha."

        await send_telegram(bot, TELEGRAM_CHAT_ID, summary)
        print("Telegram bildirimi gönderildi.")
    elif not all_new_jobs:
        print("Yeni ilan yok, bildirim gönderilmedi.")

if __name__ == "__main__":
    asyncio.run(run())
