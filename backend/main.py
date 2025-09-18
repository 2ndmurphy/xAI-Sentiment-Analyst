from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.scraper import scrape_search

app = FastAPI()

class ScrapeRequest(BaseModel):
    query: str
    limit: int = 10

@app.get("/")
async def root():
    return {"message": "Welcome to the Tweet Scraper API"}

@app.post("/scrape")
async def scrape(req: ScrapeRequest):
    try:
        tweets = await scrape_search(req.query, max_tweets=req.limit, headless=True, save_csv=False)
        return {"query": req.query, "count": len(tweets), "tweets": tweets}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
