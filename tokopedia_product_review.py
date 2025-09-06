import os
import json
import asyncio
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from helpers.preprocess import preprocess_text

# ====== CONFIG ======
COOKIES_FILE = "cookies_tokped.json"   # simpan cookies kalau butuh login
OUTPUT_FILE = "tokped_reviews.csv"
PRODUCT_URL = "https://www.tokopedia.com/namatoko/namaproduk"  # ganti link produk tokped
MAX_REVIEWS = 100      # batas review yang mau diambil
BATCH_SIZE = 10        # flush tiap 10 review

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
async def scrape_reviews():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # load cookies kalau ada
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
            print(f"[WARNING] gagal load cookies: {e}")

        page = await context.new_page()
        await page.goto(PRODUCT_URL, wait_until='domcontentloaded', timeout=60000)

        scraped = []
        seen = set()
        total_scraped = 0

        ensure_csv_header(OUTPUT_FILE)
        print(f"[INFO]📝 writing to {OUTPUT_FILE}")

        print(f"[RUNNING] 🔍 Start scraping reviews from product: {PRODUCT_URL}")

        while total_scraped < MAX_REVIEWS:
            # ambil review dari halaman
            reviews = await page.locator('span[data-testid="lblItemUlasan"]').all()

            for r in reviews:
                try:
                    text = await r.inner_text(timeout=30000)
                    clean = preprocess_text(text)

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
                        print(f"[+] PULL {len(reviews)} reviews")

                        # batch save
                        if len(scraped) >= BATCH_SIZE:
                            save_batch(OUTPUT_FILE, scraped)
                            print(f"[INFO] 💾 Flushed {len(scraped)} reviews to {OUTPUT_FILE}")
                            scraped = []
                        if total_scraped >= MAX_REVIEWS:
                            print(f"[INFO] 🔴 Batas maksimal review tercapai: {MAX_REVIEWS}")
                            break
                except Exception as e:
                    print(f"[ERROR] {e}")
                    await page.reload(timeout=60000)

            # scroll down buat load review lebih banyak
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(3)

        # simpan sisa batch
        if scraped:
            save_batch(OUTPUT_FILE, scraped)
            print(f"[INFO] 💾 Flushed last {len(scraped)} reviews to {OUTPUT_FILE}")

        print(f"\n[INFO] ✅ Selesai! Total {len(seen)} reviews saved to {OUTPUT_FILE}")

        await context.close()
        await browser.close()

# Run
if __name__ == "__main__":
    asyncio.run(scrape_reviews())
