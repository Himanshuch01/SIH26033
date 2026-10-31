from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.models import User
from logistics.models import DeliverySlot
from market.models import Listing
from market.services import annotate_listings, listing_breakdown

from .i18n import STRINGS


def home(request):
    listings = list(
        Listing.objects.filter(is_active=True, quantity_kg__gt=0)
        .select_related("crop", "farmer").order_by("-created_at")[:7]
    )
    annotate_listings(listings)
    sample = next((l for l in listings if l.mandi_kg), None)
    slots = list(DeliverySlot.objects.open_slots()[:3])
    for s in slots:
        s.cells = s.meter_cells()
    ctx = {
        "listings": listings,
        "slots": slots,
        "sample": sample,
        "sample_split": listing_breakdown(sample, 10) if sample else None,
        "farmer_count": User.objects.filter(role="farmer").count(),
        "listing_count": Listing.objects.filter(is_active=True).count(),
    }
    return render(request, "core/home.html", ctx)


def set_lang(request, code):
    if code in STRINGS:
        request.session["lang"] = code
    nxt = request.GET.get("next") or reverse("core:home")
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = reverse("core:home")
    return redirect(nxt)
