"""Business logic kept out of views: price context and the 'where did your rupee go' split."""
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

from logistics.models import DeliverySlot
from pricing import services as price_services

from .models import GRADE_MULT

TWO = Decimal("0.01")
DEFAULT_LOGISTICS_PER_KG = Decimal("4.00")


def q2(x):
    return Decimal(x).quantize(TWO, rounding=ROUND_HALF_UP)


def annotate_listings(listings):
    """Attach live mandi price, fair price and a 12-week trend to each listing (2 queries total)."""
    prices = price_services.current_price_map()
    series = price_services.recent_series_map(12)
    for l in listings:
        quintal = prices.get(l.crop_id)
        l.mandi_kg = q2(quintal / 100) if quintal else None
        l.fair_kg = q2(l.mandi_kg * GRADE_MULT[l.grade]) if l.mandi_kg else None
        l.vs_mandi_pct = float((l.price_per_kg / l.mandi_kg - 1) * 100) if l.mandi_kg else None
        l.trend = series.get(l.crop_id, [])
    return listings


def split(farmer_amount, kg, logistics_per_kg, typical_amount=None):
    """Core arithmetic shared by listing pages, cart and orders."""
    farmer = q2(farmer_amount)
    fee = q2(farmer * settings.PLATFORM_FEE_PCT / 100)
    logistics = q2(Decimal(kg) * logistics_per_kg)
    total = farmer + fee + logistics
    out = {
        "kg": Decimal(kg), "farmer": farmer, "fee": fee, "logistics": logistics, "total": total,
        "logistics_per_kg": logistics_per_kg,
        "farmer_pct": float(farmer / total * 100) if total else 0,
        "fee_pct": float(fee / total * 100) if total else 0,
        "logistics_pct": float(logistics / total * 100) if total else 0,
        "fee_rate": settings.PLATFORM_FEE_PCT,
        # In the typical chain the farmer gets at most the mandi price: 1 / (1 + markup)
        "chain_farmer_pct": float(100 / (1 + settings.RETAIL_MARKUP_PCT / 100)),
        "typical": None, "saving": None, "saving_pct": None,
    }
    if typical_amount:
        typical = q2(typical_amount)
        out.update(typical=typical, saving=typical - total, saving_pct=float((typical - total) / typical * 100))
    return out


def listing_breakdown(listing, kg):
    """Per-basket split for a single listing, priced on the next open truck."""
    if not hasattr(listing, "mandi_kg"):
        annotate_listings([listing])
    kg = Decimal(kg)
    slot = DeliverySlot.objects.open_slots().first()
    per_kg = slot.cost_per_kg(kg) if slot else DEFAULT_LOGISTICS_PER_KG
    typical = kg * listing.mandi_kg * (1 + settings.RETAIL_MARKUP_PCT / 100) if listing.mandi_kg else None
    data = split(kg * listing.price_per_kg, kg, per_kg, typical)
    data["slot"] = slot
    return data


def order_breakdown(order):
    items = list(order.items.select_related("listing__crop", "listing__farmer"))
    kg = sum((i.quantity_kg for i in items), Decimal(0))
    farmer_amount = sum((i.line_total for i in items), Decimal(0))
    per_kg = order.logistics_per_kg_locked
    locked = per_kg is not None
    if per_kg is None:
        per_kg = order.slot.cost_per_kg()
    typical = sum((i.quantity_kg * i.mandi_ref_kg * (1 + settings.RETAIL_MARKUP_PCT / 100) for i in items), Decimal(0))
    data = split(farmer_amount, kg, per_kg, typical if typical else None)
    data.update(items=items, locked=locked)
    return data
