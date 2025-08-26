import sqlite3
from typing import Optional, Dict, Any, List, Tuple

DB_PATH = "data/ads_performance.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def _date_bounds(conn, platform: Optional[str]) -> Tuple[str, str]:
    where = "" if not platform or platform == "all" else "WHERE platform = ?"
    params = [] if not platform or platform == "all" else [platform]
    cur = conn.execute(f"SELECT MIN(date), MAX(date) FROM v_all_metrics_daily {where}", params)
    row = cur.fetchone()
    return row[0], row[1]

def summary(conn, start: Optional[str], end: Optional[str], platform: str) -> Dict[str, Any]:
    if not start or not end:
        s, e = _date_bounds(conn, platform)
        start = start or s
        end = end or e

    sql = """
    SELECT
      SUM(impressions),
      SUM(clicks),
      SUM(spend_usd),
      SUM(conversions),
      SUM(revenue_usd)
    FROM v_all_metrics_daily
    WHERE date BETWEEN ? AND ?
      AND (? = 'all' OR platform = ?);
    """
    row = conn.execute(sql, [start, end, platform, platform]).fetchone()
    impressions, clicks, spend, conversions, revenue = [x or 0 for x in row]

    cpc  = (spend / clicks) if clicks else 0
    cpa  = (spend / conversions) if conversions else None
    roas = (revenue / spend) if spend else 0

    return {
        "start": start, "end": end, "platform": platform,
        "impressions": int(impressions),
        "clicks": int(clicks),
        "spend_usd": round(spend, 2),
        "conversions": int(conversions),
        "revenue_usd": round(revenue, 2),
        "cpc": round(cpc, 4),
        "cpa": round(cpa, 4) if cpa is not None else None,
        "roas": round(roas, 4),
    }

def timeseries(conn, start: Optional[str], end: Optional[str], platform: str) -> List[Dict[str, Any]]:
    if not start or not end:
        s, e = _date_bounds(conn, platform)
        start = start or s
        end = end or e

    sql = """
    SELECT date,
           SUM(impressions) AS impressions,
           SUM(clicks)      AS clicks,
           SUM(spend_usd)   AS spend_usd,
           SUM(conversions) AS conversions,
           SUM(revenue_usd) AS revenue_usd
    FROM v_all_metrics_daily
    WHERE date BETWEEN ? AND ?
      AND (? = 'all' OR platform = ?)
    GROUP BY date
    ORDER BY date;
    """
    rows = conn.execute(sql, [start, end, platform, platform]).fetchall()
    out = []
    for r in rows:
        d, imp, clk, sp, conv, rev = r
        cpc  = (sp / clk) if clk else 0
        cpa  = (sp / conv) if conv else None
        roas = (rev / sp) if sp else 0
        out.append({
            "date": d,
            "impressions": int(imp or 0),
            "clicks": int(clk or 0),
            "spend_usd": round(sp or 0, 2),
            "conversions": int(conv or 0),
            "revenue_usd": round(rev or 0, 2),
            "cpc": round(cpc, 4),
            "cpa": round(cpa, 4) if cpa is not None else None,
            "roas": round(roas, 4),
        })
    return out

_SORT_SQL = {
    "roas": "CASE WHEN SUM(spend_usd)>0 THEN SUM(revenue_usd)/SUM(spend_usd) ELSE 0 END",
    "spend": "SUM(spend_usd)",
    "revenue": "SUM(revenue_usd)",
    "conversions": "SUM(conversions)"
}

def top_campaigns(conn, start: Optional[str], end: Optional[str], platform: str, limit: int, sort: str):
    sort_expr = _SORT_SQL.get(sort, _SORT_SQL["roas"])
    if not start or not end:
        s, e = _date_bounds(conn, platform)
        start = start or s
        end = end or e

    sql = f"""
    SELECT campaign_id, campaign_name,
           SUM(spend_usd)   AS spend_usd,
           SUM(revenue_usd) AS revenue_usd,
           SUM(conversions) AS conversions
    FROM v_all_metrics_daily
    WHERE date BETWEEN ? AND ?
      AND (? = 'all' OR platform = ?)
    GROUP BY campaign_id, campaign_name
    ORDER BY {sort_expr} DESC
    LIMIT ?;
    """
    rows = conn.execute(sql, [start, end, platform, platform, limit]).fetchall()
    out = []
    for cid, cname, sp, rev, conv in rows:
        roas = (rev / sp) if sp else 0
        out.append({
            "campaign_id": cid,
            "campaign_name": cname,
            "spend_usd": round(sp or 0, 2),
            "revenue_usd": round(rev or 0, 2),
            "conversions": int(conv or 0),
            "roas": round(roas, 4)
        })
    return out

def bounds(conn, platform: str):
    where = "" if platform == "all" else "WHERE platform = ?"
    params = [] if platform == "all" else [platform]
    cur = conn.execute(f"SELECT MIN(date), MAX(date) FROM v_all_metrics_daily {where}", params)
    mn, mx = cur.fetchone()
    return {"min": mn, "max": mx}
