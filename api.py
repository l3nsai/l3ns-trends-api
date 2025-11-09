from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pytrends.request import TrendReq
import pandas as pd

app = FastAPI()

# CORS: allow your GPT and tools to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pytrends = TrendReq(hl="en-US", tz=360)


@app.get("/")
def home():
    return {"message": "L3NS.ai Trends API is live"}


@app.post("/trends")
def get_trends(data: dict):
    """
    Single keyword mode.
    Uses Google Trends normalization for this term only:
    100 = this term's own peak in past 12 months.
    Also returns monthly interest for this term alone.
    """
    keyword = data.get("keyword")
    if not keyword:
        return {"error": "Keyword missing"}

    pytrends.build_payload([keyword], cat=0, timeframe="today 12-m", geo="", gprop="")
    interest = pytrends.interest_over_time()

    if interest.empty or keyword not in interest.columns:
        return {
            "keyword": keyword,
            "peak_score_12m_worldwide": 0,
            "monthly_interest": [],
            "related_queries_top_10": [],
        }

    # Remove helper columns if present
    value_series = interest[keyword]

    # Peak over the 12m window
    peak = int(value_series.max())

    # Monthly averages (0-100, still within same normalization)
    monthly = (
        value_series
        .resample("M")
        .mean()
        .round()
        .astype(int)
    )

    monthly_interest = [
        {"month": ts.strftime("%Y-%m"), "score": int(val)}
        for ts, val in monthly.items()
    ]

    # Related queries
    related = pytrends.related_queries().get(keyword, {})
    top_related = related.get("top")
    queries = top_related["query"].head(10).tolist() if top_related is not None else []

    return {
        "keyword": keyword,
        "peak_score_12m_worldwide": peak,
        "monthly_interest": monthly_interest,
        "related_queries_top_10": queries,
    }


@app.post("/multi-trends")
def get_multi_trends(data: dict):
    """
    Multi keyword comparison mode.

    Input:
      { "keywords": ["protein powder", "adjustable dumbbells", ...] }

    Behavior:
      - Queries all keywords TOGETHER in a single Google Trends payload.
      - Google Trends normalization:
          100 = highest interest point across ALL provided keywords
                in the last 12 months worldwide.
          Other values are relative to that.
      - Returns for each keyword:
          - peak_score_12m_worldwide (relative, correct)
          - monthly_interest: list of {month: "YYYY-MM", score: int}
          - top 10 related queries
    """
    keywords = data.get("keywords")
    if not keywords or not isinstance(keywords, list):
        return {"error": "keywords must be a non-empty list"}

    # Deduplicate + clean
    keywords = [k.strip() for k in keywords if isinstance(k, str) and k.strip()]
    keywords = list(dict.fromkeys(keywords))  # keep order, remove dups

    if not keywords:
        return {"error": "keywords must be a non-empty list"}

    pytrends.build_payload(keywords, cat=0, timeframe="today 12-m", geo="", gprop="")
    interest = pytrends.interest_over_time()

    if interest.empty:
        return {"results": []}

    # Filter to value columns only (exclude isPartial)
    value_cols
