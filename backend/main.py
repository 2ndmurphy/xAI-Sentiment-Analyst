# import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from services.sentiment import SentimentAnalyzer
from services.scraper import scrape_search

load_dotenv()
app = FastAPI(title="Tweet Scraper & Sentiment API")

# Izin untuk aplikasi Streamlit front-end origin selama development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    query: str
    limit: int = 10


class AnalyzeRequest(BaseModel):
    texts: List[str]


# MODEL = "services/model/xlm-roberta-base"
analyzer = SentimentAnalyzer()


@app.get("/")
async def root():
    return {"message": "Welcome to the Tweet Scraper API"}


@app.post("/scrape")
async def scrape(req: ScrapeRequest):
    try:
        tweets = await scrape_search(
            req.query, max_tweets=req.limit, headless=True, save_csv=False
        )
        return {"query": req.query, "count": len(tweets), "tweets": tweets}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    try:
        results = analyzer.predict_batch(req.texts, batch_size=32)
        return {"count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test_analyzer")
async def test_analyzer():
    texts = ["I love this!", "I hate that!"]
    results = analyzer.predict_batch(texts)
    return {"count": len(results), "results": results}
