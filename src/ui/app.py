import os
from datetime import date
import requests
import pandas as pd
import streamlit as st

# ========= BASIC CONFIG =========
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
ENDPOINTS = {
    "health": f"{API_BASE_URL}/health",
    "summary": f"{API_BASE_URL}/metrics/summary",
    "timeseries": f"{API_BASE_URL}/metrics/timeseries",
    "top_campaigns": f"{API_BASE_URL}/metrics/top-campaigns",
}

# ========= HELPERS =========
def _fmt_money(x):
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return x

def _fmt_int(x):
    try:
        return f"{int(x):,}"
    except Exception:
        return x

@st.cache_data(ttl=60)
def api_get(url, params=None):
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def check_api():
    try:
        data = api_get(ENDPOINTS["health"])
        return True, data
    except Exception as e:
        return False, str(e)

def get_summary(start, end, platform):
    params = {"start": start.isoformat(), "end": end.isoformat(), "platform": platform}
    return api_get(ENDPOINTS["summary"], params=params)

def get_timeseries(start, end, platform, interval="day"):
    params = {"start": start.isoformat(), "end": end.isoformat(),
              "platform": platform, "interval": interval}
    return api_get(ENDPOINTS["timeseries"], params=params)

def get_top_campaigns(start, end, platform, limit=10):
    params = {"start": start.isoformat(), "end": end.isoformat(),
              "platform": platform, "limit": limit}
    return api_get(ENDPOINTS["top_campaigns"], params=params)

# ========= UI =========
st.set_page_config(page_title="Ads Metrics", page_icon="📊", layout="wide")
st.title("📊 Ads Metrics)")

ok, health = check_api()
if not ok:
    st.error(f"API not reachable at {API_BASE_URL}\n\nDetails: {health}")
    st.stop()

with st.sidebar:
    st.header("Filters")
    platform = st.selectbox("Platform", ["all", "google", "meta"], index=0)

    # ✅ Wide, fixed bounds so you can always pick proper dates
    MIN_PICK = date(2020, 1, 1)
    MAX_PICK = date.today()

    start_default = max(MIN_PICK, date(MAX_PICK.year, MAX_PICK.month, 1))

    date_range = st.date_input(
        "Date range",
        value=(start_default, MAX_PICK),
        min_value=MIN_PICK,
        max_value=MAX_PICK
    )

    # 🔑 handle both tuple and single-date return
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
    else:
        start = end = date_range

    interval = st.selectbox("Time interval", ["day", "week", "month"], index=0)
    limit = st.number_input("Top campaigns limit", min_value=1, max_value=100, value=10, step=1)

if start > end:
    st.warning("Start date must be before end date.")
    st.stop()

# ===== Summary (compact cards, 2 rows of 4) =====
try:
    summary = get_summary(start, end, platform)

    items = [
        ("Total Impressions", _fmt_int(summary.get("impressions"))),
        ("Total Clicks", _fmt_int(summary.get("clicks"))),
        ("Total Spend (USD)", _fmt_money(summary.get("spend_usd"))),
        ("Total Conversions", _fmt_int(summary.get("conversions"))),
        ("Total Revenue (USD)", _fmt_money(summary.get("revenue_usd"))),
        ("Average CPC", _fmt_money(summary.get("cpc"))),
        ("Average CPA", _fmt_money(summary.get("cpa")) if summary.get("cpa") is not None else "—"),
        ("Return on Ad Spend (ROAS)", f"{summary.get('roas'):.2f}x" if isinstance(summary.get("roas"), (int, float)) else summary.get("roas")),
    ]

    st.markdown("""
    <style>
      .small-card {
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #ddd;
        background: #fafafa;
        text-align: center;
        margin: 4px;
      }
      .small-card .label {font-size:0.8rem; color:#555; margin-bottom:4px;}
      .small-card .value {font-size:1.1rem; font-weight:600;}
    </style>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    for col, (label, val) in zip(cols, items[:4]):
        with col:
            st.markdown(f"""
            <div class="small-card">
              <div class="label">{label}</div>
              <div class="value">{val}</div>
            </div>
            """, unsafe_allow_html=True)

    cols = st.columns(4)
    for col, (label, val) in zip(cols, items[4:]):
        with col:
            st.markdown(f"""
            <div class="small-card">
              <div class="label">{label}</div>
              <div class="value">{val}</div>
            </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Failed to load summary: {e}")

st.divider()

import plotly.express as px

st.subheader("📈 Performance Over Time")

try:
    ts = get_timeseries(start, end, platform, interval=interval)
    df_ts = pd.DataFrame(ts)

    if not df_ts.empty:
        if "date" in df_ts.columns:
            df_ts["date"] = pd.to_datetime(df_ts["date"], errors="coerce")
            df_ts = df_ts.sort_values("date")

        # Engagement chart
        st.markdown("**User Engagement (Impressions & Clicks)**")
        cols = [c for c in ["impressions", "clicks"] if c in df_ts.columns]
        if cols:
            fig = px.line(df_ts, x="date", y=cols, title="Impressions vs Clicks Over Time")
            st.plotly_chart(fig, use_container_width=True)

        # Conversions chart
        if "conversions" in df_ts.columns:
            st.markdown("**Conversions**")
            fig = px.line(df_ts, x="date", y="conversions", title="Conversions Over Time")
            st.plotly_chart(fig, use_container_width=True)

        # Spend vs Revenue chart
        money_cols = [c for c in ["spend_usd", "revenue_usd"] if c in df_ts.columns]
        if money_cols:
            st.markdown("**Spend vs Revenue (USD)**")
            fig = px.area(df_ts, x="date", y=money_cols, title="Spend vs Revenue")
            st.plotly_chart(fig, use_container_width=True)

        # Table
        st.markdown("**Raw Timeseries Data**")
        st.dataframe(df_ts, use_container_width=True)

    else:
        st.info("No timeseries data for the selected filters.")
except Exception as e:
    st.error(f"Failed to load timeseries: {e}")


st.divider()

st.subheader("🏆 Top Campaigns")

try:
    top = get_top_campaigns(start, end, platform, limit=limit)
    df_top = pd.DataFrame(top)
    if not df_top.empty:
        st.markdown("**Campaign Performance Table**")

        money_cols = [c for c in ["spend_usd", "revenue_usd", "cpc", "cpa"] if c in df_top.columns]
        int_cols = [c for c in ["impressions", "clicks", "conversions"] if c in df_top.columns]
        fmt_df = df_top.copy()
        for c in money_cols:
            fmt_df[c] = fmt_df[c].apply(_fmt_money)
        for c in int_cols:
            fmt_df[c] = fmt_df[c].apply(_fmt_int)
        if "roas" in fmt_df.columns:
            fmt_df["roas"] = fmt_df["roas"].apply(lambda x: f"{x:.2f}x" if isinstance(x, (int, float)) else x)

        st.dataframe(fmt_df, use_container_width=True)
    else:
        st.info("No campaign rows for the selected filters.")
except Exception as e:
    st.error(f"Failed to load top campaigns: {e}")


st.caption(f"API: {API_BASE_URL}")
