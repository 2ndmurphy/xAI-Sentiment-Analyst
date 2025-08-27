import os
import json
import asyncio
import pandas as pd
import main as st
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from helpers.preprocess import preprocess_tweet
from helpers.csv_config import ensure_csv_header, save_batch

# ====== SCRAPER FUNCTION ======
async def scrape_tweets(search_query: str, max_tweets: int, cookies_file: str, output_file: str, batch_size: int, logger, progress_callback=None):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

            # Load cookies for auto-login
            try:
                if os.path.exists(cookies_file):
                    with open(cookies_file, "r", encoding="utf-8") as f:
                        cookies = json.load(f)
                    for c in cookies:
                        if "sameSite" in c:
                            if c["sameSite"] not in ["Strict", "Lax", "None"]:
                                c["sameSite"] = "Lax"
                        else:
                            c["sameSite"] = "Lax"
                    await context.add_cookies(cookies)
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")
                st.warning(f"Failed to load cookies: {e}")

            page = await context.new_page()
            url = f"https://x.com/search?q={search_query}&src=typed_query&f=live"
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_selector('article div[data-testid="tweetText"]', timeout=30000)
            except PlaywrightTimeoutError:
                logger.error("Timeout waiting for tweet selector")
                st.error("Timeout waiting for tweets to load. Check network or query.")
                await browser.close()
                return 0

            scraped = []
            seen = set()
            ensure_csv_header(output_file)

            while len(scraped) < max_tweets:
                try:
                    tweets = await page.locator('div[data-testid="tweetText"]').all()
                    for t in tweets:
                        try:
                            text = await t.inner_text(timeout=5000)
                            clean = preprocess_tweet(text)
                            if clean and clean not in seen:
                                seen.add(clean)
                                scraped.append({
                                    "timestamp": datetime.now().isoformat(),
                                    "raw": text,
                                    "clean": clean
                                })
                                if progress_callback:
                                    progress_callback(len(scraped), max_tweets)
                            if len(scraped) >= batch_size:
                                save_batch(output_file, scraped)
                                scraped = []
                        except Exception as e:
                            logger.warning(f"Error processing tweet: {e}")
                            continue

                    await page.mouse.wheel(0, 2000)
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Error during scraping loop: {e}")
                    break

            if scraped:
                save_batch(output_file, scraped)

            await browser.close()
            return len(seen)
    except Exception as e:
        logger.error(f"Critical error in scrape_tweets: {e}")
        st.error(f"Scraping failed: {str(e)}")
        return 0