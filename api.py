from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pytrends.request import TrendReq
import pandas as pd

app = FastAPI()

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

    values = interest[keyword]
    peak = int(values.max())

    monthly = (
        values
        .resample("M")
        .mean()
        .round()
        .astype(int)
    )

    monthly_interest = [
        {"month": ts.strftime("%Y-%m"), "score": int(val)}
        for ts, val in monthly.items()
    ]

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
    keywords = data.get("keywords")
    if not keywords or not isinstance(keywords, list):
        return {"error": "keywords must be a non-empty list"}

    keywords = [k.strip() for k in keywords if isinstance(k, str) and k.strip()]
    keywords = list(dict.fromkeys(keywords))

    if not keywords:
        return {"error": "keywords must be a non-empty list"}

    pytrends.build_payload(keywords, cat=0, timeframe="today 12-m", geo="", gprop="")
    interest = pytrends.interest_over_time()

    if interest.empty:
        return {"results": []}

    value_cols = [kw for kw in keywords if kw in interest.columns]
    if not value_cols:
        return {"results": []}

    monthly_df = (
        interest[value_cols]
        .resample("M")
        .mean()
        .round()
        .astype(int)
    )

    related_all = pytrends.related_queries()
    results = []

    for kw in value_cols:
        series = interest[kw]
        peak = int(series.max())

        monthly_interest = [
            {"month": ts.strftime("%Y-%m"), "score": int(val)}
            for ts, val in monthly_df[kw].items()
        ]

        related = related_all.get(kw, {})
        top_related = related.get("top")
        queries = (
            top_related["query"].head(10).tolist()
            if top_related is not None
            else []
        )

        results.append(
            {
                "keyword": kw,
                "peak_score_12m_worldwide": peak,
                "monthly_interest": monthly_interest,
                "related_queries_top_10": queries,
            }
        )

    return {"results": results}
