"""Custom template filters/tags: rupee formatting, crop names, SVG charts."""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


def _indian(whole: str) -> str:
    if len(whole) <= 3:
        return whole
    head, tail = whole[:-3], whole[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


@register.filter
def inr(value, decimals=0):
    """12345.5 -> ₹12,346 ; with :2 -> ₹12,345.50 (Indian digit grouping)."""
    if value in (None, ""):
        return "—"
    decimals = int(decimals)
    q = Decimal(str(value)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    sign = "-" if q < 0 else ""
    whole, _, frac = f"{abs(q):f}".partition(".")
    return f"{sign}₹{_indian(whole)}" + (f".{frac}" if decimals else "")


@register.filter
def kg(value, decimals=0):
    if value in (None, ""):
        return "—"
    decimals = int(decimals)
    q = Decimal(str(value)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    whole, _, frac = f"{q:f}".partition(".")
    return f"{_indian(whole)}" + (f".{frac}" if decimals else "") + " kg"


@register.filter
def pct(value, decimals=0):
    if value in (None, ""):
        return "—"
    return f"{float(value):.{int(decimals)}f}%"


@register.filter
def cname(crop, lang="en"):
    """Crop name in the visitor's language."""
    return crop.local_name(lang) if crop else ""


@register.filter
def abs_val(value):
    return abs(value)


@register.simple_tag
def sparkline(values, width=92, height=24):
    vals = [float(v) for v in (values or [])]
    if len(vals) < 2:
        return mark_safe('<span class="spark-none">no data</span>')
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = []
    for i, v in enumerate(vals):
        x = 1 + i * (width - 2) / (len(vals) - 1)
        y = height - 2 - ((v - lo) / span) * (height - 4)
        pts.append(f"{x:.1f},{y:.1f}")
    direction = "up" if vals[-1] >= vals[0] else "down"
    last_x, last_y = pts[-1].split(",")
    return format_html(
        '<svg class="spark spark-{}" viewBox="0 0 {} {}" width="{}" height="{}" role="img" aria-label="price trend">'
        '<polyline points="{}" fill="none" stroke-width="1.6" stroke-linejoin="round"/>'
        '<circle cx="{}" cy="{}" r="2.2"/></svg>',
        direction, width, height, width, height, " ".join(pts), last_x, last_y,
    )


@register.simple_tag
def price_chart(history, forecast):
    """Line chart (solid = history, dashed = forecast) drawn as inline SVG, no JS library."""
    hist = [(d, float(p)) for d, p in history]
    fc = [(d, float(p)) for d, p in forecast]
    if len(hist) < 2:
        return ""
    W, H, L, R, T, B = 760, 280, 58, 16, 16, 34
    allp = [p for _, p in hist + fc]
    lo, hi = min(allp), max(allp)
    pad = (hi - lo) * 0.12 or 1
    lo, hi = max(0, lo - pad), hi + pad
    n = len(hist) + len(fc)

    def X(i):
        return L + i * (W - L - R) / (n - 1)

    def Y(p):
        return T + (hi - p) / (hi - lo) * (H - T - B)

    grid = []
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        y = Y(v)
        grid.append(f'<line x1="{L}" x2="{W-R}" y1="{y:.1f}" y2="{y:.1f}" class="c-grid"/>'
                    f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" class="c-lab">{v:,.0f}</text>')
    xl, last_month = [], None
    for i, (d, _) in enumerate(hist + fc):
        if d.month != last_month and (i == 0 or d.day <= 7):
            xl.append(f'<text x="{X(i):.1f}" y="{H-12}" class="c-lab" text-anchor="middle">{d.strftime("%b %y")}</text>')
            last_month = d.month
    h_pts = " ".join(f"{X(i):.1f},{Y(p):.1f}" for i, (_, p) in enumerate(hist))
    f_pts = " ".join(f"{X(len(hist)-1+i):.1f},{Y(p):.1f}" for i, (_, p) in enumerate([hist[-1]] + fc))
    now_x = X(len(hist) - 1)
    svg = (
        f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Weekly mandi price and forecast">'
        + "".join(grid) + "".join(xl)
        + f'<line x1="{now_x:.1f}" x2="{now_x:.1f}" y1="{T}" y2="{H-B}" class="c-now"/>'
        + f'<text x="{now_x-6:.1f}" y="{T+10}" text-anchor="end" class="c-lab">today</text>'
        + f'<polyline points="{h_pts}" class="c-hist" fill="none"/>'
        + (f'<polyline points="{f_pts}" class="c-fc" fill="none"/>' if fc else "")
        + "</svg>"
    )
    return mark_safe(svg)
