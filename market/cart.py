"""Session-based shopping cart: {listing_id: kg}. No cart table needed."""
from decimal import Decimal

from .models import Listing


def _raw(request):
    return request.session.setdefault("cart", {})


def add(request, listing, qty):
    _raw(request)[str(listing.pk)] = str(qty)
    request.session.modified = True


def remove(request, listing_id):
    _raw(request).pop(str(listing_id), None)
    request.session.modified = True


def clear(request):
    request.session["cart"] = {}
    request.session.modified = True


def lines(request):
    raw = _raw(request)
    found = Listing.objects.filter(pk__in=[int(k) for k in raw], is_active=True).select_related("crop", "farmer")
    out, total_kg, subtotal = [], Decimal(0), Decimal(0)
    for l in found:
        qty = Decimal(raw[str(l.pk)])
        out.append({"listing": l, "qty": qty, "amount": qty * l.price_per_kg})
        total_kg += qty
        subtotal += qty * l.price_per_kg
    return out, total_kg, subtotal
