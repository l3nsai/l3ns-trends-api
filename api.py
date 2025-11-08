from fastapi import FastAPI
from pytrends.request import TrendReq

app = FastAPI()
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

    if interest.empty:
        return {
            "keyword": keyword,
            "peak_score_12m_worldwide": 0,
            "related_queries_top_10": []
        }

    score = int(interest[keyword].max())
    related = pytrends.related_queries().get(keyword, {})
    top_related = related.get("top")
    queries = top_related["query"].head(10).tolist() if top_related is not None else []

    return {
        "keyword": keyword,
        "peak_score_12m_worldwide": score,
        "related_queries_top_10": queries
    }
