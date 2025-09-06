import os
import json
import asyncio
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from helpers.preprocess import preprocess_text

# ====== CONFIG ======
COOKIES_FILE = "cookies.json"      # file cookies hasil export dari browser
OUTPUT_FILE = "dataset_tweets.csv" # file output yang menyimpan hasil scrape
SEARCH_QUERIES = ["samsung"]       # topik yang ingin di scrape
MAX_TWEETS = 100                   # simpan tweet ketika sudah mencapai maksimal
BATCH_SIZE = 10                    # flush/simpan tiap 10 tweet yang sudah diekstrak

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

# =========================
# SCRAPING SECTION
# =========================
async def _load_and_set_cookies(context):
    """
    Loads cookies from a file and sets them in the browser context.

    This function attempts to read cookies from the configured file, sanitizes their properties,
    and adds them to the provided Playwright browser context for authentication.

    Args:
        context: The Playwright browser context to which cookies will be added.
    """
    try:
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        for c in cookies:
            if "sameSite" in c:
                if c["sameSite"] not in ["Strict", "Lax", "None"]:
                    c["sameSite"] = "Lax"
            else:
                c["sameSite"] = "Lax"
        await context.add_cookies(cookies)
    except Exception as e:
        print(f"🔴[WARNING] gagal load cookies: {e}")

async def _extract_and_save_tweets(page, seen, scraped, total_scraped):
    """
    Extracts tweets from the page and saves them in batches to a CSV file.

    This function scrolls through the page, collects tweet texts, and saves them in batches until the maximum number of tweets is reached.

    Args:
        page: The Playwright page object to extract tweets from.
        seen: A set to keep track of unique tweets.
        scraped: A list to accumulate tweets before batch saving.
        total_scraped: The current count of tweets scraped.

    Returns:
        tuple: Updated scraped list, seen set, and total_scraped count.
    """
    while total_scraped < MAX_TWEETS:
        tweets = await page.locator('div[data-testid="tweetText"]').all()
        for t in tweets:
            try:
                text = await t.inner_text()
                seen.add(text)
                scraped.append({
                    "timestamp": datetime.now().isoformat(),
                    "text": text,
                })
                total_scraped += 1
                print(f"[+] Mengambil {len(tweets)} data tweets")
                if len(scraped) >= BATCH_SIZE:
                    save_batch(OUTPUT_FILE, scraped)
                    print(f"💾[INFO] Flushed {len(scraped)} tweets ke {OUTPUT_FILE}")
                    scraped.clear()
                if total_scraped >= MAX_TWEETS:
                    print(f"🔴[INFO] Batas maksimal tweets tercapai: {MAX_TWEETS}")
                    break
            except (asyncio.TimeoutError, Exception) as e:
                print(f"[ERROR] {type(e).__name__}: {e}")
                if isinstance(e, asyncio.TimeoutError):
                    await page.reload(timeout=60000)
                else:
                    raise
        await page.mouse.wheel(0, 2000)
        await asyncio.sleep(3)
    return scraped, seen, total_scraped

async def scrape_search(search_query):
    """
    Scrapes tweets from X (Twitter) search results for a given query and saves them to a CSV file.

    This function automates a browser session, loads authentication cookies, navigates to the search page, and collects tweets in batches until a maximum is reached.

    Args:
        search_query: The search term to use for scraping tweets.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        await _load_and_set_cookies(context)
        
        page = await context.new_page()
        url = f"https://x.com/search?q={search_query}&src=typed_query&f=live"
        
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_selector('article div[data-testid="tweetText"]', timeout=120000)
        
        scraped = []
        seen = set()
        total_scraped = 0
        
        ensure_csv_header(OUTPUT_FILE)
        
        print(f"📝[INFO] Membuat file output {OUTPUT_FILE}")
        print(f"🔍[RUNNING] Memulai scraping dengan query: {search_query} (CTRL+C to stop)")
        
        scraped, seen, total_scraped = await _extract_and_save_tweets(page, seen, scraped, total_scraped)
        
        # simpan sisa batch kalau ada
        if scraped:
            save_batch(OUTPUT_FILE, scraped)
            print(f"💾[INFO] Flushed {len(scraped)} tweets terakhir ke {OUTPUT_FILE}")

        print(f"\n✅[INFO] Selesai! Total {len(seen)} tweets tersimpan di {OUTPUT_FILE}")
        
        await context.close()
        await browser.close()

async def process_queries():
    """
    Processes all search queries and initiates scraping for each one.

    This function iterates through the configured list of search queries and calls the scraping routine for each.

    """
    for query in SEARCH_QUERIES:
        print(f"\n[INFO] Memulai scraping untuk topik: '{query}'")
        await scrape_search(query)

if __name__ == "__main__":
    try:
        asyncio.run(process_queries())
    except KeyboardInterrupt as k:
        print(f"[INFO] 🔴 Stopped by user {k}")
