#!/usr/bin/env python3
import sqlite3
from pathlib import Path
import argparse

VIEWS_SQL = [
    # --- Google standardized metrics
    """
    CREATE VIEW IF NOT EXISTS v_google_metrics_daily AS
    SELECT
      segments_date            AS date,
      'google'                 AS platform,
      campaign_id, campaign_name,
      ad_group_id, ad_group_name,
      ad_id,
      impressions,
      clicks,
      (cost_micros / 1000000.0) AS spend_usd,
      conversions              AS conversions,
      conversions_value        AS revenue_usd,
      CASE WHEN clicks > 0 THEN (cost_micros / 1000000.0)/clicks ELSE 0 END AS cpc,
      CASE WHEN conversions > 0 THEN (cost_micros / 1000000.0)/conversions ELSE NULL END AS cpa,
      CASE WHEN (cost_micros/1000000.0) > 0 THEN conversions_value / (cost_micros/1000000.0) ELSE 0 END AS roas
    FROM google_ads_daily;
    """,
    # --- Meta standardized metrics (join purchases from actions)
    """
    CREATE VIEW IF NOT EXISTS v_meta_metrics_daily AS
    WITH purchases AS (
      SELECT date_start AS date, ad_id,
             SUM(value)        AS purchase_count,
             SUM(action_value) AS purchase_revenue
      FROM meta_ads_actions_daily
      WHERE action_type = 'purchase'
      GROUP BY 1,2
    )
    SELECT
      m.date_start           AS date,
      'meta'                 AS platform,
      m.campaign_id, m.campaign_name,
      m.adset_id   AS ad_group_id,
      m.adset_name AS ad_group_name,
      m.ad_id,
      m.impressions,
      m.clicks,
      m.spend      AS spend_usd,
      COALESCE(p.purchase_count, 0)    AS conversions,
      COALESCE(p.purchase_revenue, 0)  AS revenue_usd,
      CASE WHEN m.clicks > 0 THEN m.spend/m.clicks ELSE 0 END AS cpc,
      CASE WHEN COALESCE(p.purchase_count,0) > 0 THEN m.spend/COALESCE(p.purchase_count,0) ELSE NULL END AS cpa,
      CASE WHEN m.spend > 0 THEN COALESCE(p.purchase_revenue,0)/m.spend ELSE 0 END AS roas
    FROM meta_ads_daily m
    LEFT JOIN purchases p
      ON p.date = m.date_start AND p.ad_id = m.ad_id;
    """,
    # --- Unified view (google + meta)
    """
    CREATE VIEW IF NOT EXISTS v_all_metrics_daily AS
    SELECT * FROM v_google_metrics_daily
    UNION ALL
    SELECT * FROM v_meta_metrics_daily;
    """
]

# Materialized rollups (drop/rebuild each run for simplicity)
ROLLUPS_DROP = [
    "DROP TABLE IF EXISTS rollup_daily_platform;",
    "DROP TABLE IF EXISTS rollup_daily_platform_campaign;"
]

ROLLUPS_CREATE = [
    """
    CREATE TABLE rollup_daily_platform AS
    SELECT date, platform,
           SUM(impressions)   AS impressions,
           SUM(clicks)        AS clicks,
           SUM(spend_usd)     AS spend_usd,
           SUM(conversions)   AS conversions,
           SUM(revenue_usd)   AS revenue_usd
    FROM v_all_metrics_daily
    GROUP BY date, platform;
    """,
    """
    CREATE TABLE rollup_daily_platform_campaign AS
    SELECT date, platform, campaign_id, campaign_name,
           SUM(impressions)   AS impressions,
           SUM(clicks)        AS clicks,
           SUM(spend_usd)     AS spend_usd,
           SUM(conversions)   AS conversions,
           SUM(revenue_usd)   AS revenue_usd
    FROM v_all_metrics_daily
    GROUP BY date, platform, campaign_id, campaign_name;
    """
]

def main():
    parser = argparse.ArgumentParser(description="Build standardized views and rollups.")
    parser.add_argument("--db", default="data/ads_performance.db")
    args = parser.parse_args()

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    # Create views
    for sql in VIEWS_SQL:
        cur.execute(sql)

    # Rebuild rollups
    for sql in ROLLUPS_DROP:
        cur.execute(sql)
    for sql in ROLLUPS_CREATE:
        cur.execute(sql)

    conn.commit()
    conn.close()
    print("Views + rollups built successfully.")

if __name__ == "__main__":
    main()
