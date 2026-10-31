"""Tiny label dictionary for the English / Hindi / Punjabi toggle.

Deliberately not Django's gettext machinery: a dict is easy to explain in a viva
and lets a farmer-facing screen switch language instantly from the session.
"""

LANGS = [("en", "EN"), ("hi", "हिं"), ("pa", "ਪੰਜਾਬੀ")]

STRINGS = {
    "en": {
        "tagline": "Farm gate to front door, with the arithmetic shown.",
        "nav_market": "Market", "nav_requirements": "Requirement board", "nav_trucks": "Trucks",
        "nav_prices": "Mandi prices", "nav_dashboard": "My desk", "nav_cart": "Cart",
        "login": "Log in", "logout": "Log out", "register": "Create account",
        "fresh_listings": "Fresh on the ledger", "trucks_filling": "Trucks filling now",
        "crop": "Crop", "grade": "Grade", "farmer": "Farmer", "village": "Village",
        "qty": "Stock (kg)", "price": "Price / kg", "mandi": "Mandi / kg", "trend": "12 wk",
        "add_to_cart": "Add to cart", "sell_produce": "List produce", "post_need": "Post a requirement",
        "farmer_gets": "Farmer receives", "platform_fee": "Platform fee", "shared_truck": "Shared truck",
        "you_pay": "You pay", "typical_chain": "Typical mandi-chain price", "you_save": "You save",
    },
    "hi": {
        "tagline": "खेत से घर तक, हिसाब के साथ।",
        "nav_market": "बाज़ार", "nav_requirements": "माँग पटल", "nav_trucks": "ट्रक",
        "nav_prices": "मंडी भाव", "nav_dashboard": "मेरा खाता", "nav_cart": "टोकरी",
        "login": "लॉग इन", "logout": "लॉग आउट", "register": "खाता बनाएँ",
        "fresh_listings": "ताज़ा सूची", "trucks_filling": "भर रहे ट्रक",
        "crop": "फ़सल", "grade": "ग्रेड", "farmer": "किसान", "village": "गाँव",
        "qty": "स्टॉक (किलो)", "price": "भाव / किलो", "mandi": "मंडी / किलो", "trend": "12 हफ़्ते",
        "add_to_cart": "टोकरी में डालें", "sell_produce": "उपज बेचें", "post_need": "माँग डालें",
        "farmer_gets": "किसान को मिला", "platform_fee": "प्लेटफ़ॉर्म शुल्क", "shared_truck": "साझा ट्रक",
        "you_pay": "आप देंगे", "typical_chain": "आम मंडी-शृंखला भाव", "you_save": "आपकी बचत",
    },
    "pa": {
        "tagline": "ਖੇਤ ਤੋਂ ਘਰ ਤੱਕ, ਪੂਰੇ ਹਿਸਾਬ ਨਾਲ।",
        "nav_market": "ਬਾਜ਼ਾਰ", "nav_requirements": "ਮੰਗ ਬੋਰਡ", "nav_trucks": "ਟਰੱਕ",
        "nav_prices": "ਮੰਡੀ ਭਾਅ", "nav_dashboard": "ਮੇਰਾ ਖਾਤਾ", "nav_cart": "ਟੋਕਰੀ",
        "login": "ਲਾਗਇਨ", "logout": "ਲਾਗਆਊਟ", "register": "ਖਾਤਾ ਬਣਾਓ",
        "fresh_listings": "ਤਾਜ਼ਾ ਸੂਚੀ", "trucks_filling": "ਭਰ ਰਹੇ ਟਰੱਕ",
        "crop": "ਫ਼ਸਲ", "grade": "ਗਰੇਡ", "farmer": "ਕਿਸਾਨ", "village": "ਪਿੰਡ",
        "qty": "ਸਟਾਕ (ਕਿੱਲੋ)", "price": "ਭਾਅ / ਕਿੱਲੋ", "mandi": "ਮੰਡੀ / ਕਿੱਲੋ", "trend": "12 ਹਫ਼ਤੇ",
        "add_to_cart": "ਟੋਕਰੀ ਵਿੱਚ ਪਾਓ", "sell_produce": "ਫ਼ਸਲ ਵੇਚੋ", "post_need": "ਮੰਗ ਪਾਓ",
        "farmer_gets": "ਕਿਸਾਨ ਨੂੰ ਮਿਲਿਆ", "platform_fee": "ਪਲੇਟਫਾਰਮ ਫ਼ੀਸ", "shared_truck": "ਸਾਂਝਾ ਟਰੱਕ",
        "you_pay": "ਤੁਸੀਂ ਦਿਓਗੇ", "typical_chain": "ਆਮ ਮੰਡੀ-ਲੜੀ ਭਾਅ", "you_save": "ਤੁਹਾਡੀ ਬੱਚਤ",
    },
}
