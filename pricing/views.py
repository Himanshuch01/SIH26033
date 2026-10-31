from datetime import timedelta
from decimal import Decimal

from django.db.models import Max
from django.shortcuts import render

from market.models import GRADE_MULT, Crop

from . import services
from .models import MandiPrice


def insights(request):
    crops = list(Crop.objects.filter(prices__isnull=False).distinct().order_by("name"))
    crop = None
    if request.GET.get("crop", "").isdigit():
        crop = next((c for c in crops if c.pk == int(request.GET["crop"])), None)
    crop = crop or (crops[0] if crops else None)
    fc = services.forecast(crop.pk) if crop else None
    markets = []
    if crop:
        last = MandiPrice.objects.filter(crop=crop).aggregate(m=Max("date"))["m"]
        rows = MandiPrice.objects.filter(crop=crop, date__gte=last - timedelta(days=6)).order_by("market", "-date")
        seen = set()
        for r in rows:
            if r.market not in seen:
                seen.add(r.market)
                markets.append(r)
    return render(request, "pricing/insights.html", {"crops": crops, "crop": crop, "fc": fc, "markets": markets})


def price_hint(request):
    """HTMX fragment shown beside the 'crop' dropdown on the listing form."""
    crop = Crop.objects.filter(pk=request.GET.get("crop") or 0).first()
    ctx = {"crop": crop}
    if crop:
        q = services.current_price_map().get(crop.pk)
        if q:
            per_kg = q / 100
            ctx.update(quintal=q, per_kg=per_kg,
                       bands=[(g, (per_kg * m).quantize(Decimal("0.01"))) for g, m in GRADE_MULT.items()])
    return render(request, "pricing/_hint.html", ctx)
