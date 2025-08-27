# Marketing Data Pipeline — Metrics API & Simple UI

A tiny, production-lean FastAPI service that aggregates **paid ads metrics** (Google, Meta) from a database and exposes them as **clean API endpoints**, plus a **minimal Streamlit UI** to visualize the results (no CORS, no static hosting, no fancy frameworks).

## ✨ What you get

- **FastAPI** app with ready-to-call endpoints:
  - `GET /metrics/summary` — totals + derived KPIs
  - `GET /metrics/timeseries` — daily/weekly/monthly series
  - `GET /metrics/top-campaigns` — leaderboards
  - `GET /metrics/bounds` — min/max data dates (optional)
  - `GET /health` — health check
- **SQLite/Postgres-friendly** data access layer (DAL)
- **Simple UI** (`app.py` Streamlit) that calls the API and renders:
  - **8 compact metric cards** (two rows of 4)
  - **Timeseries charts with legends** (Plotly)
  - **Campaign performance table**

---

## 🧭 Architecture at a glance

```
client (Streamlit UI)  ──▶  FastAPI  ──▶  DAL/SQL  ──▶  DB (ads_raw, ads_daily)
                                 ▲
                                 └── derived metrics (CPC, CPA, ROAS)
```

- The **DAL** runs a few focused SQL queries:
  - **summary**: totals across a date window + platform filter
  - **timeseries**: aggregates by date with an interval bucket (day/week/month)
  - **top_campaigns**: aggregates by campaign within the window
  - **bounds**: min/max dates available in the dataset
- The **API layer** validates parameters, calls DAL functions, computes **derived KPIs**, and returns JSON.
- The **UI** calls the API and displays metrics, charts, and tables.

---

## 📂 Project layout

```
marketing-data-pipeline/
├─ app.py                 # Streamlit UI (simple client using the API)
├─ src/
│  ├─ api/
│  │  └─ main.py          # FastAPI app (endpoints live here)
│  └─ dal/
│     ├─ __init__.py
│     ├─ db.py            # get_conn(), engine, connection helpers
│     ├─ queries.py       # summary(), timeseries(), top_campaigns(), bounds()
│     └─ schema.sql       # optional DDL for reference
├─ requirements.txt
└─ README.md
```

> If your file names differ slightly (e.g., `dal.py`, `app.py` under `src/api`, etc.), the concepts are the same—adjust paths accordingly.

---

## 🗃️ Data model (typical)

Your raw table can be as simple as:

| column         | type         | notes                                  |
|----------------|--------------|----------------------------------------|
| `date`         | DATE         | event/attribution date                  |
| `platform`     | TEXT         | `google` or `meta`                      |
| `campaign`     | TEXT         | campaign name/id                        |
| `impressions`  | BIGINT       | daily impressions                       |
| `clicks`       | BIGINT       | daily clicks                            |
| `conversions`  | BIGINT       | daily conversions                       |
| `spend_usd`    | NUMERIC(12,2)| daily ad spend                          |
| `revenue_usd`  | NUMERIC(12,2)| attributed revenue                      |

**Recommended indexes**
- `(date)`
- `(platform, campaign)`
- `(platform, date)`

---

## 📊 Metrics definitions

- **CPC (Cost per Click)** = `spend_usd / clicks`
- **CPA (Cost per Acquisition)** = `spend_usd / conversions`
- **ROAS (Return on Ad Spend)** = `revenue_usd / spend_usd`

These are computed in the API layer before returning JSON.

---

## 🚀 Getting started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the API

```bash
uvicorn src.api.main:app --reload --port 8000
```

Now you can open:
- [http://localhost:8000/docs](http://localhost:8000/docs) → Swagger API docs
- [http://localhost:8000/metrics/summary](http://localhost:8000/metrics/summary)

### 3. Run the UI

```bash
streamlit run app.py
```

The UI will connect to `http://localhost:8000` by default (override with `API_BASE_URL` env var).

---

## 📈 Example workflow

1. API aggregates raw ad data in your DB (Google + Meta).
2. UI fetches from endpoints.
3. Metrics are displayed as:
   - Compact KPI cards
   - Line/area charts with legends
   - Campaign performance leaderboard

---

## 🛠️ Notes

- Database schema is minimal — you can adapt to BigQuery, Postgres, or SQLite.
- Streamlit app is deliberately simple, no extra CORS/static hosting.
- Replace test data with your ETL output to go live.

---

## 📜 License

MIT — free to use, modify, and adapt.
