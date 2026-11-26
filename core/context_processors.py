from .i18n import LANGS, STRINGS


def site(request):
    """Runs for every template: language labels `t`, current `lang`, and cart size."""
    lang = request.session.get("lang", "en")
    if lang not in STRINGS:
        lang = "en"
    labels = {**STRINGS["en"], **STRINGS[lang]}
    cart = request.session.get("cart", {})
    cart_count = 0
    if cart:
        from market.models import Listing

        pks = [int(k) for k in cart.keys() if str(k).isdigit()]
        if pks:
            cart_count = Listing.objects.filter(pk__in=pks, is_active=True, quantity_kg__gt=0).count()
    return {"t": labels, "lang": lang, "LANGS": LANGS, "cart_count": cart_count}
