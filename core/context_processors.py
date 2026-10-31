from .i18n import LANGS, STRINGS


def site(request):
    """Runs for every template: language labels `t`, current `lang`, and cart size."""
    lang = request.session.get("lang", "en")
    if lang not in STRINGS:
        lang = "en"
    labels = {**STRINGS["en"], **STRINGS[lang]}
    cart = request.session.get("cart", {})
    return {"t": labels, "lang": lang, "LANGS": LANGS, "cart_count": len(cart)}
