import sqlite3
from typing import Dict
import pandas as pd

DDL = {
"google_ads_daily": """
CREATE TABLE IF NOT EXISTS google_ads_daily (
  segments_date TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  campaign_name TEXT NOT NULL,
  ad_group_id TEXT NOT NULL,
  ad_group_name TEXT NOT NULL,
  ad_id TEXT NOT NULL,
  impressions INTEGER NOT NULL,
  clicks INTEGER NOT NULL,
  cost_micros INTEGER NOT NULL,
  conversions INTEGER NOT NULL,
  conversions_value REAL NOT NULL
);""",
"meta_ads_daily": """
CREATE TABLE IF NOT EXISTS meta_ads_daily (
  date_start TEXT NOT NULL,
  date_stop  TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  campaign_name TEXT NOT NULL,
  adset_id TEXT NOT NULL,
  adset_name TEXT NOT NULL,
  ad_id TEXT NOT NULL,
  impressions INTEGER NOT NULL,
  clicks INTEGER NOT NULL,
  spend REAL NOT NULL
);""",
"meta_ads_actions_daily": """
CREATE TABLE IF NOT EXISTS meta_ads_actions_daily (
  date_start TEXT NOT NULL,
  ad_id TEXT NOT NULL,
  action_type TEXT NOT NULL,
  value INTEGER NOT NULL,
  action_value REAL NOT NULL
);"""
}



def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for ddl in DDL.values():
        cur.execute(ddl)
    conn.commit()
    return conn

def insert_dataframe(conn: sqlite3.Connection, table: str, df: pd.DataFrame):
    if df.empty:
        return
    placeholders = ",".join(["?"] * df.shape[1])
    cols = ",".join(df.columns)
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    conn.executemany(sql, df.itertuples(index=False, name=None))
    conn.commit()


