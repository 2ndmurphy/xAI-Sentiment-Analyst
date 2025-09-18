# from playwright.async_api import async_playwright

# async def scrape_tweets(username: str, limit: int = 10):
#     tweets = []
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         page = await browser.new_page()
#         await page.goto(f"https://twitter.com/{username}")

#         # contoh dummy (beneran scraping bisa pakai locator/selector)
#         tweets = [f"Tweet ke {i + 1} dari @{username}" for i in range(limit)]
#         await browser.close()
#     return tweets

# import re
# from datetime import datetime
# from playwright.async_api import async_playwright

# async def scrape_tweets(search_query: str, max_tweets: int = 20):
#     """
#     Scrapes tweets from X (Twitter) search results for a given query.
#     Return list of dict (JSON serializable).
#     """
#     tweets = []
#     MULTISPACE_RE = re.compile(r"\s+")

#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         context = await browser.new_context()
#         page = await context.new_page()

#         url = f"https://twitter.com/search?q={search_query}&src=typed_query&f=live"
#         await page.goto(url, wait_until='domcontentloaded', timeout=60000)
#         await page.wait_for_selector('article div[data-testid="tweetText"]', timeout=180000)

#         while len(tweets) < max_tweets:
#             elements = await page.locator('div[data-testid="tweetText"]').all()
#             for el in elements:
#                 if len(tweets) >= max_tweets:
#                     break
#                 try:
#                     text = await el.inner_text()
#                     tweets.append({
#                         "timestamp": datetime.now().isoformat(),
#                         "text": MULTISPACE_RE.sub(" ", text).strip()
#                     })
#                 except Exception as e:
#                     print(f"[ERROR] {e}")

#             # scroll biar load tweet baru
#             await page.mouse.wheel(0, 2000)
#             await page.wait_for_timeout(2000)

#         await browser.close()

#     return tweets

import json
import os
import re
import pandas as pd
from datetime import datetime
from urllib.parse import quote_plus
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# optional: import your csv helpers if you still want to save batches
# from helpers.csv_config import ensure_csv_header, save_batch

# config (gunakan yg sama seperti project lo)
COOKIES_FILE = "cookies.json"
OUTPUT_FILE = "dataset_tweets.csv"
BATCH_SIZE = 10
DEFAULT_MAX = 100

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
# PREPROCESS TEXT
# =========================
def preprocess_text(text):
    """
    Preprocess tweet text by stripping extra spaces and newlines.
    """
    MULTISPACE_RE = re.compile(r"\s+")

    new_text = []
    for t in text.split(" "):
        t = '' if t.startswith('@') and len(t) > 1 else t
        t = '' if t.startswith('https') else t
        t = MULTISPACE_RE.sub(" ", t).strip()
        if t:
            new_text.append(t)

    return " ".join(new_text)


async def _load_and_set_cookies(context, cookies_file=COOKIES_FILE):
    """
    Returns True if cookies loaded+set, False otherwise.
    (This is your loader, slightly hardened.)
    """
    try:
        with open(cookies_file, "r", encoding="utf-8") as f:
            raw_cookies = json.load(f)

        cookies = []
        for c in raw_cookies:
            cookie = {
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c.get("path", "/"),
                "secure": c.get("secure", False),
                "httpOnly": c.get("httpOnly", False),
            }

            # handle expiration
            if "expirationDate" in c and c["expirationDate"] is not None:
                cookie["expires"] = int(c["expirationDate"])
            else:
                cookie["expires"] = -1  # session cookie

            # fix sameSite
            same_site = str(c.get("sameSite", "")).capitalize()
            if same_site == "No_restriction":
                cookie["sameSite"] = "None"
            elif same_site in ["Lax", "Strict", "None"]:
                cookie["sameSite"] = same_site
            else:
                cookie["sameSite"] = "Lax"

            cookies.append(cookie)

        await context.add_cookies(cookies)
    except Exception as e:
        print(f"🔴[WARNING] gagal load cookies: {e}")


async def _is_logged_in(page):
    """
    Heuristik sederhana: cek apakah ada tanda UI logged-in.
    Ini gak 100% akurat (X berubah-ubah), tapi cukup membantu.
    """
    try:
        # Cek beberapa selector yang biasanya ada saat logged-in
        if await page.locator('a[aria-label="Home"]').count() > 0:
            return True
        if await page.locator('div[data-testid="SideNav_AccountSwitcher_Button"]').count() > 0:
            return True
        # jika tombol "Log in" muncul, berarti bukan login
        if await page.locator('text="Log in"').count() > 0 or await page.locator('text="Sign in"').count() > 0:
            return False
    except Exception:
        pass
    # fallback: jika tidak ketemu tombol login, anggap kemungkinan logged-in (best-effort)
    return True


async def scrape_search(search_query: str,
                        max_tweets: int = DEFAULT_MAX,
                        headless: bool = True,
                        save_csv: bool = False,
                        cookies_file: str = COOKIES_FILE):
    """
    Scrape tweets for `search_query`. Returns list[dict].
    Raises RuntimeError on irrecoverable issues (login required / blocked).
    """
    tweets = []
    seen = set()
    batch = []

    url = f"https://x.com/search?q={quote_plus(search_query)}&src=typed_query&f=live"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        # 1) set cookies if ada
        await _load_and_set_cookies(context, cookies_file)

        try:
            # 2) navigate - gunakan networkidle untuk SPA
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # 3) cek apakah login diperlukan
            logged_in = await _is_logged_in(page)

            if not logged_in:
                debug_dir = "debug"
                os.makedirs(debug_dir, exist_ok=True)
                img_path = os.path.join(debug_dir, "login_required.png")
                html_path = os.path.join(debug_dir, "login_required.html")
                await page.screenshot(path=img_path, full_page=True)
                content = await page.content()
                with open(html_path, "w", encoding="utf-8") as fh:
                    fh.write(content)
                raise RuntimeError(
                    "🔒 Login required (cookies missing/expired or wrong domain). "
                    f"Saved debug files: {img_path}, {html_path}"
                )

            # 4) wait for tweet selector to appear (shorter timeout)
            try:
                await page.wait_for_selector('div[data-testid="tweetText"]', timeout=60000)
            except PlaywrightTimeoutError:
                # kemungkinan selector berubah / rate limit / blocked
                debug_dir = "debug"
                os.makedirs(debug_dir, exist_ok=True)
                img_path = os.path.join(debug_dir, "no_tweets_found.png")
                html_path = os.path.join(debug_dir, "no_tweets_found.html")
                await page.screenshot(path=img_path, full_page=True)
                content = await page.content()
                with open(html_path, "w", encoding="utf-8") as fh:
                    fh.write(content)
                raise RuntimeError(
                    "❌ Tidak menemukan elemen tweetText. "
                    f"Saved debug files: {img_path}, {html_path}"
                )

            # 5) extraction loop (guard with seen set)
            idle_rounds = 0
            MAX_IDLE = 3  # stop kalau sudah 3 kali loop tidak ada tweet baru

            while len(tweets) < max_tweets:
                elements = page.locator('div[data-testid="tweetText"]')
                count = await elements.count()
                new_count = 0

                if count == 0:
                    # coba scroll dan tunggu
                    await page.mouse.wheel(0, 2000)
                    await page.wait_for_timeout(1500)
                    count = await elements.count()
                    if count == 0:
                        idle_rounds += 1
                        if idle_rounds >= MAX_IDLE:
                            print("⚠️ [STOP] Tidak ada tweet baru setelah beberapa kali scroll")
                            break
                        continue

                for i in range(count):
                    if len(tweets) >= max_tweets:
                        break
                    try:
                        text = (await elements.nth(i).inner_text(timeout=5000)).strip()
                    except Exception as e:
                        # skip element kalau error inner_text
                        print(f"[SKIP] gagal baca tweet ke-{i}: {e}")
                        continue
                    if not text or text in seen:
                        continue

                    seen.add(text)
                    row = {
                        "timestamp": datetime.now().isoformat(),
                        "text": preprocess_text(text)
                    }
                    tweets.append(row)
                    batch.append(row)
                    new_count += 1

                    print(f"[+] Tweet baru ditangkap (total={len(tweets)})")

                    # flush ke CSV kalau diminta
                    if save_csv and len(batch) >= BATCH_SIZE:
                        ensure_csv_header(OUTPUT_FILE)
                        save_batch(OUTPUT_FILE, batch)
                        print(f"💾 Flushed {len(batch)} tweets ke {OUTPUT_FILE}")
                        batch.clear()

                # scroll to load more
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(1500)

        finally:
            # simpan batch tersisa kalo perlu
            if save_csv and batch:
                ensure_csv_header(OUTPUT_FILE)
                save_batch(OUTPUT_FILE, batch)
                print(f"💾 Flushed sisa {len(batch)} tweets ke {OUTPUT_FILE}")

            try:
                await context.close()
            except Exception:
                pass
            try:
                await browser.close()
            except Exception:
                pass

    return tweets
