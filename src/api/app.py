#!/usr/bin/env python3
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional, Literal
from .dal import get_conn, summary as q_summary, timeseries as q_timeseries, top_campaigns as q_top_campaigns
from .dal import bounds as q_bounds   # <--- add this import

app = FastAPI(title="Ads Metrics API", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "ok"}

class SummaryResponse(BaseModel):
    start: str
    end: str
    platform: Literal["google", "meta", "all"]
    impressions: int
    clicks: int
    spend_usd: float
    conversions: int
    revenue_usd: float
    cpc: float
    cpa: Optional[float] = None
    roas: float

@app.get("/metrics/summary", response_model=SummaryResponse)
def metrics_summary(
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str]   = Query(None, description="YYYY-MM-DD"),
    platform: Literal["google", "meta", "all"] = "all"
):
    with get_conn() as conn:
        return q_summary(conn, start, end, platform)

@app.get("/metrics/timeseries")
def metrics_timeseries(
    start: Optional[str] = Query(None),
    end: Optional[str]   = Query(None),
    platform: Literal["google", "meta", "all"] = "all"
):
    with get_conn() as conn:
        return q_timeseries(conn, start, end, platform)

@app.get("/metrics/top-campaigns")
def metrics_top_campaigns(
    start: Optional[str] = Query(None),
    end: Optional[str]   = Query(None),
    platform: Literal["google", "meta", "all"] = "all",
    limit: int = Query(10, ge=1, le=100),
    sort: Literal["roas", "spend", "revenue", "conversions"] = "roas"
):
    with get_conn() as conn:
        return q_top_campaigns(conn, start, end, platform, limit, sort)

@app.get("/metrics/bounds")
def metrics_bounds(platform: Literal["google", "meta", "all"] = "all"):
    with get_conn() as conn:
        return q_bounds(conn, platform)