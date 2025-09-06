import os
import json
import asyncio
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from helpers.preprocess import preprocess_text

# ====== CONFIG ======
COOKIES_FILE = "cookies.json"
OUTPUT_FILE = "dataset_tweets.csv"
SEARCH_QUERIES = ["samsung"]
MAX_TWEETS = 100       # simpan tweet ketika sudah mencapai maksimal
BATCH_SIZE = 10        # flush/simpan tiap 10 tweet yang sudah diekstrak

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
        df = pd.DataFrame(columns=["timestamp", "text"])
        df.to_csv(csv_path, index=False, encoding="utf-8")

def save_batch(csv_path, batch):
    """
    Save a batch of tweets to the CSV file.
    """
    if not batch:
        return

    df = pd.DataFrame(batch)
    df.to_csv(csv_path, index=False, mode='a', header=False, encoding="utf-8")

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
            print(f"🔴[WARNING] gagal load cookies: {e}")

        page = await context.new_page()

        # buka halaman search langsung ke tab Latest
        url = f"https://x.com/search?q={search_query}&src=typed_query&f=live"
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_selector('article div[data-testid="tweetText"]', timeout=120000)

        scraped = []
        seen = set()
        total_scraped = 0

        ensure_csv_header(OUTPUT_FILE)
        print(f"📝[INFO] membuat file output {OUTPUT_FILE}")

        print(f"🔍[RUNNING] Memulai scraping dengan query: {search_query} (CTRL+C to stop)")

        while total_scraped < MAX_TWEETS:
            # ambil tweet yang sudah ada di viewport
            tweets = await page.locator('div[data-testid="tweetText"]').all()

            for t in tweets:
                try:
                    text = await t.inner_text(timeout=0)
                    # clean = preprocess_text(text)

                    # Jika preprocess_text() return tuple, ekstrak elemen pertama
                    # if isinstance(clean, tuple):
                    #     clean_str = clean[0]
                    # else:
                    #     clean_str = clean
                    # if clean_str not in seen and clean_str.strip():
                    seen.add(text)
                    scraped.append({
                        # "timestamp": datetime.now().isoformat(),
                        # "raw": text,
                        # "clean": clean_str
                        "timestamp": datetime.now().isoformat(),
                        "text": text,
                    })
                    total_scraped += 1
                    print(f"[+] Mengambil {len(tweets)} data tweets")
                        
                    # batch save
                    if len(scraped) >= BATCH_SIZE:
                        save_batch(OUTPUT_FILE, scraped)
                        print(f"💾[INFO] Flushed {len(scraped)} tweets ke {OUTPUT_FILE}")
                        scraped = []
                    if total_scraped >= MAX_TWEETS:
                        print(f"🔴[INFO] Batas maksimal tweets tercapai: {MAX_TWEETS}")
                        break
                except (asyncio.TimeoutError, Exception) as e:
                    print(f"[ERROR] {type(e).__name__}: {e}")
                    # Only reload on timeout errors, otherwise re-raise
                    if isinstance(e, asyncio.TimeoutError):
                        await page.reload(timeout=60000) # reload page jika error timeout
                    else:
                        raise

            # scroll down
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(3)