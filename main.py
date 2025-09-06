import asyncio
from helpers.scraper import scrape_search, process_queries

SEARCH_QUERIES = ["samsung"] # tambahkan query lainnya

def main():
  try:
      asyncio.run(process_queries(SEARCH_QUERIES))
  except KeyboardInterrupt as k:
      print(f"[INFO] 🔴 Stopped by user {k}")
  asyncio.run(scrape_search(SEARCH_QUERIES))

# if __name__ == "__main__":
#   main()
