import re
import os
import json
import asyncio
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from helpers.preprocess import preprocess_text

# ====== CONFIG ======
COOKIES_FILE = "cookies.json"
OUTPUT_FILE = "tweets_sentiment.csv"
SEARCH_QUERIES = ["trending"]
MAX_TWEETS = 100      # simpan tweet ketika sudah mencapai maksimal
BATCH_SIZE = 10      # flush/simpan tiap 10 tweet yang sudah diekstrak

# =========================
# CSV HELPERS
# =========================
def ensure_csv_header(csv_path):
    """
    Ensure the CSV file has the correct header.
    
    Parameter:
        csv_path: Path to the CSV file
    """
    if not os.path.exists(csv_path):
        df = pd.DataFrame(columns=["timestamp", "raw", "clean"])
        df.to_csv(csv_path, index=False, encoding="utf-8")

def save_batch(csv_path, batch):
    """
    Save a batch of tweets to the CSV file.
    """
    if not batch:
        return

    df = pd.DataFrame(batch)
    df.to_csv(csv_path, index=False, mode='a', header=False, encoding="utf-8")

# ====== SCRAPER ======
async def scrape_search(search_query):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # load cookies untuk auto login
        try:
            with open(COOKIES_FILE, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            # sanitize sameSite biar valid
            for c in cookies:
                if "sameSite" in c:
                    if c["sameSite"] not in ["Strict", "Lax", "None"]:
                        c["sameSite"] = "Lax"
                else:
                    c["sameSite"] = "Lax"
            await context.add_cookies(cookies)
        except Exception as e:
            print(f"[WARNING] gagal load cookies: {e}")

        page = await context.new_page()

        # buka halaman search langsung ke tab Latest
        url = f"https://x.com/search?q={search_query}&src=typed_query&f=live"
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_selector('article div[data-testid="tweetText"]', timeout=120000)

        scraped = []
        seen = set()
        total_scraped = 0

        ensure_csv_header(OUTPUT_FILE)
        print(f"[INFO]📝 writing to {OUTPUT_FILE}")

        print(f"[RUNNING] 🔍 Start scraping search query: {search_query} (CTRL+C to stop)")

        while total_scraped < MAX_TWEETS:
            # ambil tweet yang sudah ada di viewport
            tweets = await page.locator('div[data-testid="tweetText"]').all()

            for t in tweets:
                try:
                    text = await t.inner_text(timeout=120000)
                    clean = preprocess_text(text)

                    # Jika preprocess_text() return tuple, ekstrak elemen pertama
                    if isinstance(clean, tuple):
                        clean_str = clean[0]
                    else:
                        clean_str = clean
                    if clean_str not in seen and clean_str.strip():
                        seen.add(clean_str)
                        scraped.append({
                            "timestamp": datetime.now().isoformat(),
                            "raw": text,
                            "clean": clean_str
                        })
                        total_scraped += 1
                        print(f"[+] PULL {len(tweets)} tweets")
                        
                        # batch save
                        if len(scraped) >= BATCH_SIZE:
                            save_batch(OUTPUT_FILE, scraped)
                            print(f"[INFO] 💾 Flushed {len(scraped)} tweets to {OUTPUT_FILE}")
                            scraped = []
                        if total_scraped >= MAX_TWEETS:
                            print(f"[INFO] 🔴 Batas maksimal tweets tercapai: {MAX_TWEETS}")
                            break
                except Exception as e:
                    print(f"[ERROR] {e}")
                    await page.reload(timeout=60000) # reload page kalau error timeout

            # scroll down
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(3)
        
        # simpan sisa batch kalau ada
        if scraped:
            save_batch(OUTPUT_FILE, scraped)
            print(f"[INFO] 💾 Flushed last {len(scraped)} tweets to {OUTPUT_FILE}")

        print(f"\n[INFO] ✅ Selesai! Total {len(seen)} tweets saved to {OUTPUT_FILE}")

        await context.close()
        await browser.close()

async def process_queries():
    for query in SEARCH_QUERIES:
        print(f"\n[INFO] Memulai scraping untuk topik: '{query}'")
        await scrape_search(query)


if __name__ == "__main__":
    try:
        asyncio.run(process_queries())
    except KeyboardInterrupt as k:
        print(f"[INFO] 🔴 Stopped by user {k}")
