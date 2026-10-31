"""Explainable price analytics.

Method (kept simple on purpose so it can be defended in a viva):
  1. Daily mandi prices are averaged into weekly prices.
  2. A seasonal index per calendar month = (average price in that month) / (overall average).
  3. Forecast for week k = current price x (index of that week's month / index of this month).
  4. 4-week and 12-week moving averages give the short-term momentum.
  5. If the 4-week-ahead forecast is >= 4% higher -> "Hold", <= -4% -> "Sell now", else "Steady".
"""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from statistics import mean

from django.db.models import Max

from .models import MandiPrice

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def weekly_series(crop_ids=None, weeks=52):
    """{crop_id: [(monday_date, avg_modal_price), ...]} using ONE query."""
    qs = MandiPrice.objects.all()
    last = qs.aggregate(m=Max("date"))["m"]
    if not last:
        return {}
    qs = qs.filter(date__gte=last - timedelta(weeks=weeks))
    if crop_ids is not None:
        qs = qs.filter(crop_id__in=list(crop_ids))
    buckets = defaultdict(lambda: defaultdict(list))
    for cid, d, p in qs.values_list("crop_id", "date", "modal_price"):
        buckets[cid][d - timedelta(days=d.weekday())].append(float(p))
    return {cid: sorted((d, sum(v) / len(v)) for d, v in wk.items()) for cid, wk in buckets.items()}


def current_price_map():
    """{crop_id: Decimal ₹ per quintal} - latest weekly average."""
    out = {}
    for cid, pts in weekly_series(weeks=3).items():
        out[cid] = Decimal(str(round(pts[-1][1], 2)))
    return out


def recent_series_map(weeks=12):
    return {cid: [p for _, p in pts] for cid, pts in weekly_series(weeks=weeks).items()}


def forecast(crop_id, horizon=6):
    series = weekly_series([crop_id], weeks=160).get(crop_id, [])
    if len(series) < 20:
        return None
    dates = [d for d, _ in series]
    prices = [p for _, p in series]
    current = mean(prices[-2:])
    ma4, ma12 = mean(prices[-4:]), mean(prices[-12:])
    overall = mean(prices)

    by_month = defaultdict(list)
    for d, p in series:
        by_month[d.month].append(p)
    idx = {m: mean(v) / overall for m, v in by_month.items()}
    cur_idx = idx.get(dates[-1].month, 1.0)

    fc = []
    for k in range(1, horizon + 1):
        d = dates[-1] + timedelta(weeks=k)
        fc.append((d, current * idx.get(d.month, cur_idx) / cur_idx))

    expected = fc[3][1]
    change = (expected / current - 1) * 100
    momentum = (ma4 / ma12 - 1) * 100
    best_m = max(idx, key=idx.get)
    low_m = min(idx, key=idx.get)
    peak_week = max(fc, key=lambda x: x[1])

    if change >= 4:
        advice, headline = "hold", "Hold stock if you can store it"
        why = f"Seasonal pattern points to about {change:.1f}% higher prices within 4 weeks."
    elif change <= -4:
        advice, headline = "sell", "Sell now"
        why = f"Seasonal pattern points to about {abs(change):.1f}% lower prices within 4 weeks."
    else:
        advice, headline = "steady", "Prices look steady"
        why = f"Expected move over 4 weeks is only {change:+.1f}%, so sell when your stock is ready."

    reasons = [
        why,
        f"Current weekly price is ₹{current:,.0f}/quintal; the 4-week average is ₹{ma4:,.0f} and the 12-week average is ₹{ma12:,.0f} "
        f"(momentum {momentum:+.1f}%).",
        f"Historically {MONTHS[best_m-1]} has the highest prices ({idx[best_m]*100-100:+.0f}% vs average) and "
        f"{MONTHS[low_m-1]} the lowest ({idx[low_m]*100-100:+.0f}%).",
    ]
    return {
        "current": current, "ma4": ma4, "ma12": ma12, "momentum": momentum,
        "change_pct": change, "expected_4w": expected, "advice": advice, "headline": headline,
        "reasons": reasons, "history": series[-52:], "forecast": fc,
        "season": [(MONTHS[m - 1], round(idx[m] * 100)) for m in sorted(idx)],
        "best_month": MONTHS[best_m - 1], "low_month": MONTHS[low_m - 1],
        "peak_week": peak_week, "n_weeks": len(series),
    }
