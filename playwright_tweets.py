import re
import os
import json
import asyncio
import pandas as pd
from datetime import datetime
from emoji import demojize as unemojify
from playwright.async_api import async_playwright

# ====== CONFIG ======
COOKIES_FILE = "cookies.json"
OUTPUT_FILE = "tweets_sentiment.csv"
SEARCH_QUERIES = ["trading", "AI", "Lebih hemat"]
MAX_TWEETS = 100      # simpan tweet ketika sudah mencapai maksimal
BATCH_SIZE = 10      # flush/simpan tiap 10 tweet yang sudah diekstrak

# ====== PREPROCESS ======
def preprocess_tweet(text: str) -> str:
    text = text.lower()
    text = re.sub(r"@\w+", "USER", text)
    text = re.sub(r"https?:\/\/[^\s]+", "HTTPURL", text)
    text = re.sub(r"[(\<\>\)\{\}:\!\?\-\_\=]", "", text)
    text = re.sub(r"[^\w\s.,!?]", "", text)
    text = re.sub(r"\b\d+\b", "NUM", text)
    text = re.sub(r"\s+", " ", text)
    text = unemojify(text.strip())
    return text

# =========================
# CSV HELPERS
# =========================
def ensure_csv_header(csv_path):
    if not os.path.exists(csv_path):
        df = pd.DataFrame(columns=["timestamp", "raw", "clean"])
        df.to_csv(csv_path, index=False, encoding="utf-8")

def save_batch(csv_path, batch):
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
        # url = f"https://x.com/home"
        url = f"https://x.com/search?q={search_query}&src=typed_query&f=live"
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_selector('article div[data-testid="tweetText"]')

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
                    text = await t.inner_text(timeout=60000)
                    clean = preprocess_tweet(text)
                    if clean not in seen and clean.strip():
                        seen.add(clean)
                        scraped.append({
                            "timestamp": datetime.now().isoformat(),
                            "raw": text,
                            "clean": clean
                        })
                        total_scraped += 1
                        print(f"[+] PULL {len(tweets)} tweets")
                        
                        # batch save
                        if len(scraped) >= BATCH_SIZE:
                            save_batch(OUTPUT_FILE, scraped)
                            print(f"💾 Flushed {len(scraped)} tweets to {OUTPUT_FILE}")
                            scraped = []
                        if total_scraped >= MAX_TWEETS:
                            print(f"[INFO] 🔴 Batas maksimal tweets tercapai: {MAX_TWEETS}")
                            break
                except Exception as e:
                    print(f"[ERROR] {e}")

            # scroll down
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(2)
        
        # simpan sisa batch kalau ada
        if scraped:
            save_batch(OUTPUT_FILE, scraped)
            print(f"💾 Flushed last {len(scraped)} tweets to {OUTPUT_FILE}")

        print(f"\n✅ Selesai! Total {len(seen)} tweets saved to {OUTPUT_FILE}")

        await context.close()
        await browser.close()

async def process_queries():
    for query in SEARCH_QUERIES:
        print(f"\n[INFO] Memulai scraping untuk topik: {query}")
        await scrape_search(query)


if __name__ == "__main__":
    try:
        asyncio.run(process_queries())
    except KeyboardInterrupt as k:
        print(f"[INFO] 🔴 Stopped by user {k}")
