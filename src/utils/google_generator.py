import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple

GOOGLE_CAMPAIGNS = [
    {"campaign_id": "1234567890", "campaign_name": "Search_Brand_Terms",  "type": "search"},
    {"campaign_id": "1234567891", "campaign_name": "Shopping_Feed_US",    "type": "shopping"},
    {"campaign_id": "1234567892", "campaign_name": "YouTube_Video_Ads",   "type": "video"},
    {"campaign_id": "1234567893", "campaign_name": "Display_Remarketing", "type": "display"},
    {"campaign_id": "1234567894", "campaign_name": "Performance_Max",     "type": "pmax"},
]
ADGROUPS_PER_CAMPAIGN = (2, 4)
ADS_PER_ADGROUP       = (2, 4)

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

def promo_boost_google(campaign_name: str, d: datetime) -> float:
    if "Performance_Max" in campaign_name and (d - datetime(2024,1,1)).days < 21:
        return 1.15
    return 1.0

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def _structure(rng: np.random.Generator) -> List[Tuple[str, str, str, str, str, str]]:
    rows = []
    for camp in GOOGLE_CAMPAIGNS:
        c_id, c_name, c_type = camp["campaign_id"], camp["campaign_name"], camp["type"]
        n_ag = rng.integers(ADGROUPS_PER_CAMPAIGN[0], ADGROUPS_PER_CAMPAIGN[1] + 1)
        for i in range(1, n_ag + 1):
            ag_id = f"{c_id}-{i:02d}"
            ag_name = f"{c_name}_AG_{i:02d}"
            n_ads = rng.integers(ADS_PER_ADGROUP[0], ADS_PER_ADGROUP[1] + 1)
            for j in range(1, n_ads + 1):
                ad_id = f"{ag_id}-{j:02d}"
                rows.append((c_id, c_name, ag_id, ag_name, ad_id, c_type))
    return rows

def generate_google_ads_daily(start_date: str, days: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    structure = _structure(rng)
    out = []

    for d in daterange(start_date, days):
        wmul = weekly_mult(d) * monthly_trend(d) * midmonth_boost(d)
        for (campaign_id, campaign_name, ad_group_id, ad_group_name, ad_id, ctype) in structure:
            # Baselines
            if ctype == "search":
                base_ctr, base_cvr = 0.045, 0.055
                spend = rng.uniform(900, 2200); buy_model = "CPC"
            elif ctype == "shopping":
                base_ctr, base_cvr = 0.035, 0.045
                spend = rng.uniform(700, 2000); buy_model = "CPC"
            elif ctype == "video":
                base_ctr, base_cvr = 0.008, 0.012
                spend = rng.uniform(400, 1100); buy_model = "CPM"
            elif ctype == "display":
                base_ctr, base_cvr = 0.012, 0.018
                spend = rng.uniform(450, 1200); buy_model = "CPM"
            else:  # pmax
                base_ctr, base_cvr = 0.028, 0.030
                spend = rng.uniform(700, 1800); buy_model = "HYBRID"

            spend *= wmul * promo_boost_google(campaign_name, d) * rng.uniform(0.9, 1.1)
            spend = float(spend)

            ctr = clamp01(base_ctr * rng.uniform(0.7, 1.3))
            cvr = clamp01(base_cvr * rng.uniform(0.7, 1.3))

            if buy_model == "CPC":
                cpc = rng.uniform(0.6, 2.2)
                clicks = int(spend / cpc) if spend > 0 else 0
                impressions = int(clicks / max(ctr, 1e-6))
            elif buy_model == "CPM":
                cpm = rng.uniform(4, 20)
                impressions = int((spend / cpm) * 1000)
                clicks = int(impressions * ctr)
            else:  # HYBRID
                cpc = rng.uniform(0.8, 2.0)
                spend_cpm = spend * 0.5
                spend_cpc = spend - spend_cpm
                cpm_eff = rng.uniform(4, 16)
                impr_cpm = int((spend_cpm / cpm_eff) * 1000)
                clicks_cpc = int(spend_cpc / max(cpc, 1e-6))
                impr_from_cpc = int(clicks_cpc / max(ctr, 1e-6))
                impressions = impr_cpm + impr_from_cpc
                clicks = int(impressions * ctr)

            clicks = min(clicks, impressions)
            conversions = int(min(clicks, clicks * cvr))
            conv_value = float(conversions * rng.uniform(80, 180))  # AOV-ish

            # GA uses micros for cost (1 USD = 1,000,000 micros)
            cost_micros = int(round(spend * 1_000_000))

            # Light fatigue after day 90
            day_idx = (d - datetime.strptime(start_date, "%Y-%m-%d")).days
            if day_idx > 90:
                fat = 0.95 ** ((day_idx - 90) / 30)
                clicks = int(clicks * fat)
                conversions = int(conversions * fat)
                conv_value *= fat

            impressions = max(impressions, clicks)

            out.append({
                "segments_date": d.strftime("%Y-%m-%d"),
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "ad_group_id": ad_group_id,
                "ad_group_name": ad_group_name,
                "ad_id": ad_id,
                "impressions": int(impressions),
                "clicks": int(clicks),
                "cost_micros": int(cost_micros),
                "conversions": int(conversions),
                "conversions_value": round(conv_value, 2),
            })

    return pd.DataFrame(out)
