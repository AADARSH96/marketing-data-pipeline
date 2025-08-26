#!/usr/bin/env python3
import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from utils.google_generator import generate_google_ads_daily
from utils.meta_generator import generate_meta_ads_daily
from utils.db_helpers import init_db, insert_dataframe

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic Google & Meta ads data into SQLite.")
    parser.add_argument("--db", type=str, default="data/ads_performance.db", help="SQLite DB path")
    parser.add_argument("--start", type=str, default="2024-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=180, help="Number of days to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--no-demo", action="store_true", help="Skip running demo queries")
    args = parser.parse_args()

    # Generate dataframes
    google_df = generate_google_ads_daily(args.start, args.days, args.seed)
    meta_core_df, meta_actions_df = generate_meta_ads_daily(args.start, args.days, args.seed)

    # Ensure data folder
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)

    # Init DB + write tables
    conn = init_db(args.db)
    insert_dataframe(conn, "google_ads_daily", google_df)
    insert_dataframe(conn, "meta_ads_daily", meta_core_df)
    if not meta_actions_df.empty:
        insert_dataframe(conn, "meta_ads_actions_daily", meta_actions_df)

    print(f"\nSaved to SQLite: {args.db}")
    print(f"Rows → google_ads_daily: {len(google_df):,} | meta_ads_daily: {len(meta_core_df):,} | meta_ads_actions_daily: {len(meta_actions_df):,}")

    conn.close()

if __name__ == "__main__":
    main()
