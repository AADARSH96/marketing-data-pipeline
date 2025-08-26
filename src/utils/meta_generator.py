import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple, Dict

META_CAMPAIGNS = [
    {"campaign_id": "11100001", "campaign_name": "Brand_Awareness_Q1"},
    {"campaign_id": "11100002", "campaign_name": "Conversion_Retargeting"},
    {"campaign_id": "11100003", "campaign_name": "LeadGen_Lookalike"},
    {"campaign_id": "11100004", "campaign_name": "Holiday_Sale_2024"},
    {"campaign_id": "11100005", "campaign_name": "Product_Launch_Traffic"},
]
ADSETS_PER_CAMPAIGN = (2, 4)
ADS_PER_ADSET       = (2, 4)

META_ACTION_TYPES = ["purchase", "lead", "add_to_cart"]

def daterange(start: str, days: int):
    sd = datetime.strptime(start, "%Y-%m-%d")
    for n in range(days):
        yield sd + timedelta(days=n)

def weekly_mult(d: datetime) -> float:
    return {0:1.02, 1:1.06, 2:1.10, 3:1.08, 4:1.03, 5:0.88, 6:0.90}[d.weekday()]

def monthly_trend(d: datetime) -> float:
    return 0.96 + 0.035 * d.month

def midmonth_boost(d: datetime) -> float:
    return 1.15 if 10 <= d.day <= 20 else 1.0

def promo_boost_meta(campaign_name: str, d: datetime) -> float:
    if "Holiday_Sale" in campaign_name and d.month in (11, 12):
        return 1.30
    if "Product_Launch" in campaign_name and (d - datetime(2024,1,1)).days < 14:
        return 1.20
    return 1.0

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def _structure(rng: np.random.Generator) -> List[Tuple[str, str, str, str, str]]:
    rows = []
    for camp in META_CAMPAIGNS:
        c_id, c_name = camp["campaign_id"], camp["campaign_name"]
        n_adsets = rng.integers(ADSETS_PER_CAMPAIGN[0], ADSETS_PER_CAMPAIGN[1] + 1)
        for i in range(1, n_adsets + 1):
            adset_id = f"{c_id}-{i:02d}"
            adset_name = f"{c_name}_AS_{i:02d}"
            n_ads = rng.integers(ADS_PER_ADSET[0], ADS_PER_ADSET[1] + 1)
            for j in range(1, n_ads + 1):
                ad_id = f"{adset_id}-{j:02d}"
                rows.append((c_id, c_name, adset_id, adset_name, ad_id))
    return rows

def generate_meta_ads_daily(start_date: str, days: int, seed: int):
    rng = np.random.default_rng(seed)
    structure = _structure(rng)
    core_rows: List[Dict] = []
    action_rows: List[Dict] = []

    for d in daterange(start_date, days):
        wmul = weekly_mult(d) * monthly_trend(d) * midmonth_boost(d)
        for (campaign_id, campaign_name, adset_id, adset_name, ad_id) in structure:

            if "Retarget" in campaign_name or "Conversion" in campaign_name:
                base_ctr, base_cvr = 0.020, 0.045
                spend = rng.uniform(600, 1600)
            elif "LeadGen" in campaign_name:
                base_ctr, base_cvr = 0.018, 0.025
                spend = rng.uniform(450, 1200)
            elif "Holiday_Sale" in campaign_name:
                base_ctr, base_cvr = 0.022, 0.040
                spend = rng.uniform(700, 1700)
            elif "Product_Launch" in campaign_name:
                base_ctr, base_cvr = 0.017, 0.015
                spend = rng.uniform(500, 1300)
            else:  # Awareness/default
                base_ctr, base_cvr = 0.012, 0.008
                spend = rng.uniform(350, 900)

            spend *= wmul * promo_boost_meta(campaign_name, d) * rng.uniform(0.9, 1.1)
            spend = float(spend)

            cpm = rng.uniform(5, 18)
            impressions = int((spend / cpm) * 1000)
            ctr = clamp01(base_ctr * rng.uniform(0.7, 1.3))
            clicks = int(impressions * ctr)
            clicks = min(clicks, impressions)

            day_idx = (d - datetime.strptime(start_date, "%Y-%m-%d")).days
            if day_idx > 90:
                fat = 0.95 ** ((day_idx - 90) / 30)
                clicks = int(clicks * fat)

            core_rows.append({
                "date_start": d.strftime("%Y-%m-%d"),
                "date_stop": d.strftime("%Y-%m-%d"),
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "adset_id": adset_id,
                "adset_name": adset_name,
                "ad_id": ad_id,
                "impressions": int(impressions),
                "clicks": int(clicks),
                "spend": round(spend, 2),
            })

            total_conversions = int(min(clicks, clicks * clamp01(base_cvr * rng.uniform(0.7, 1.3))))
            if total_conversions > 0:
                mix = rng.multinomial(total_conversions, [0.55, 0.25, 0.20])  # purchase/lead/atc
                for atype, count in zip(META_ACTION_TYPES, mix):
                    if count == 0:
                        continue
                    if atype == "purchase":
                        action_value = float(count * rng.uniform(60, 180))
                    elif atype == "lead":
                        action_value = float(count * rng.uniform(5, 25))
                    else:  # add_to_cart
                        action_value = float(count * rng.uniform(3, 12))
                    action_rows.append({
                        "date_start": d.strftime("%Y-%m-%d"),
                        "ad_id": ad_id,
                        "action_type": atype,
                        "value": int(count),
                        "action_value": round(action_value, 2)
                    })

    meta_core_df = pd.DataFrame(core_rows)
    meta_actions_df = pd.DataFrame(action_rows)
    return meta_core_df, meta_actions_df
