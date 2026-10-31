"""Fill the database with realistic demo data so every screen has something to show.

    python manage.py seed_demo          # create (safe to run twice)
    python manage.py seed_demo --reset  # wipe demo data first

Mandi prices here are SAMPLE data (seasonal pattern + noise) so the forecast has
history to learn from. Replace with real Agmarknet rows using `import_prices`.
"""
import math
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from logistics.models import DeliverySlot
from market.models import Bid, Crop, Listing, Order, OrderItem, Requirement
from pricing.models import MandiPrice

# name, hindi, punjabi, category, swatch, base ₹/quintal, seasonal amplitude, peak day-of-year
CROPS = [
    ("Tomato", "टमाटर", "ਟਮਾਟਰ", "veg", "#c8402f", 2000, 0.45, 215),
    ("Potato", "आलू", "ਆਲੂ", "veg", "#b58b52", 1500, 0.25, 150),
    ("Onion", "प्याज़", "ਪਿਆਜ਼", "veg", "#a8567a", 1800, 0.35, 285),
    ("Cauliflower", "फूलगोभी", "ਫੁੱਲ ਗੋਭੀ", "veg", "#cfd5a8", 1700, 0.40, 255),
    ("Cabbage", "पत्तागोभी", "ਬੰਦ ਗੋਭੀ", "veg", "#7fae6a", 1100, 0.35, 240),
    ("Spinach", "पालक", "ਪਾਲਕ", "veg", "#2f6b3a", 1900, 0.30, 190),
    ("Carrot", "गाजर", "ਗਾਜਰ", "veg", "#e0802b", 1600, 0.30, 230),
    ("Green Peas", "मटर", "ਮਟਰ", "veg", "#5d9b3c", 4600, 0.35, 330),
    ("Wheat", "गेहूँ", "ਕਣਕ", "grain", "#c9a24d", 2425, 0.07, 180),
    ("Maize", "मक्का", "ਮੱਕੀ", "grain", "#e1b73a", 2200, 0.10, 120),
    ("Kinnow", "किन्नू", "ਕਿੰਨੂ", "fruit", "#e8932c", 2800, 0.25, 90),
    ("Moong", "मूँग", "ਮੂੰਗੀ", "pulse", "#6f8f3a", 7800, 0.08, 200),
]
MARKETS = ["Ludhiana", "Khanna", "Jalandhar", "Amritsar", "Patiala"]

FARMERS = [  # username, name, FPO, village, district
    ("gurpreet", "Gurpreet Singh", "Sidhwan Kisan FPO", "Sidhwan Bet", "Ludhiana"),
    ("harjinder", "Harjinder Kaur", "", "Doraha", "Ludhiana"),
    ("balwinder", "Balwinder Singh", "Machhiwara Growers Collective", "Machhiwara", "Ludhiana"),
    ("jaswant", "Jaswant Singh", "", "Samrala", "Ludhiana"),
    ("manpreet", "Manpreet Kaur", "Raikot Women Farmers FPO", "Raikot", "Ludhiana"),
    ("sukhdev", "Sukhdev Singh", "", "Nakodar", "Jalandhar"),
    ("amarjit", "Amarjit Singh", "Phillaur Veg Producers", "Phillaur", "Jalandhar"),
    ("rajwant", "Rajwant Kaur", "", "Banga", "Shahid Bhagat Singh Nagar"),
]
BUYERS = [
    ("sai_mess", "Ramesh Kumar", "Sai Boys Hostel Mess", "Phagwara", "Kapurthala"),
    ("langar_seva", "Baljit Singh", "Gurdwara Langar Seva Committee", "Jalandhar", "Jalandhar"),
    ("rasoi", "Anita Sharma", "Hotel Rasoi Kitchen", "Ludhiana", "Ludhiana"),
    ("greenbasket", "Vikram Arora", "Green Basket Kirana", "Ludhiana", "Ludhiana"),
]
# farmer, crop, variety, stock, min, price, (fresh, size, clean), days since harvest, description
LISTINGS = [
    ("gurpreet", "Tomato", "Hybrid", 420, 10, 24, (3, 3, 3), 1, "Picked this morning, firm red fruit. Sorted by hand into one size."),
    ("gurpreet", "Cauliflower", "Snowball", 300, 10, 30, (3, 2, 3), 1, "Tight white curds, trimmed leaves."),
    ("harjinder", "Spinach", "Desi palak", 120, 5, 28, (3, 2, 2), 0, "Cut at dawn from our own tube-well plot."),
    ("harjinder", "Carrot", "Red desi", 260, 10, 26, (2, 2, 3), 2, "Sweet winter carrots, washed."),
    ("balwinder", "Potato", "Pukhraj", 900, 25, 17, (3, 3, 2), 3, "Cold-store free, dug last week. Good for chips and sabzi."),
    ("balwinder", "Onion", "Red Nashik type", 640, 25, 22, (2, 2, 2), 5, "Dry, well-cured. Keeps for weeks."),
    ("jaswant", "Wheat", "PBW 826", 1500, 50, 27, (3, 3, 3), 40, "Clean grain, moisture under 12%. Bags of 50 kg."),
    ("jaswant", "Maize", "Yellow hybrid", 700, 50, 24, (2, 2, 2), 30, "Sun-dried cobs shelled by machine."),
    ("manpreet", "Green Peas", "Arkel", 180, 5, 60, (3, 3, 2), 1, "Plump pods, hand picked by our FPO's women group."),
    ("manpreet", "Cabbage", "Round head", 380, 10, 14, (2, 3, 3), 2, "Heavy compact heads."),
    ("sukhdev", "Kinnow", "Punjab Kinnow", 800, 20, 32, (3, 2, 2), 4, "Juicy, thin skin. Selling from our own orchard."),
    ("sukhdev", "Tomato", "Desi", 150, 5, 20, (2, 1, 2), 3, "Soft ripe tomatoes, best for chutney or gravy. Priced to move."),
    ("amarjit", "Potato", "Kufri Jyoti", 500, 25, 15, (2, 2, 1), 4, "Mixed sizes with some skin marks. Fine for mess kitchens."),
    ("amarjit", "Cauliflower", "Pusa Snowball", 220, 10, 24, (2, 2, 2), 2, "Medium curds."),
    ("rajwant", "Moong", "SML 668", 400, 20, 88, (3, 3, 3), 25, "Whole green moong, hand cleaned."),
    ("rajwant", "Spinach", "Palak", 90, 5, 22, (2, 1, 2), 1, "Small-lot tender leaves."),
]


class Command(BaseCommand):
    help = "Create demo users, crops, mandi prices, listings, trucks, orders and requirements"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **opts):
        rng = random.Random(26033)
        if opts["reset"]:
            for m in (Bid, Requirement, OrderItem, Order, Listing, DeliverySlot, MandiPrice, Crop):
                m.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        crops = {}
        for name, hi, pa, cat, sw, *_ in CROPS:
            crops[name], _ = Crop.objects.update_or_create(
                name=name, defaults=dict(name_hi=hi, name_pa=pa, category=cat, swatch=sw))

        if not MandiPrice.objects.exists():
            today = timezone.localdate()
            rows = []
            for name, _, _, _, _, base, amp, peak in CROPS:
                for market_i, market in enumerate(MARKETS):
                    bias = 1 + (market_i - 2) * 0.012
                    for day in range(0, 3 * 365, 2):
                        d = today - timedelta(days=day)
                        season = math.cos(2 * math.pi * (d.timetuple().tm_yday - peak) / 365)
                        price = base * bias * (1 + amp * season) * (1 + rng.gauss(0, 0.025))
                        rows.append(MandiPrice(crop=crops[name], market=market, date=d, modal_price=round(price, 2)))
            MandiPrice.objects.bulk_create(rows, batch_size=2000)
            self.stdout.write(f"  {len(rows)} sample mandi prices")

        users = {}
        for username, name, org, village, district in FARMERS:
            u, new = User.objects.get_or_create(username=username, defaults=dict(
                first_name=name.split()[0], last_name=name.split()[-1], role="farmer",
                org_name=org, village=village, district=district, phone=f"98{rng.randint(10000000, 99999999)}"))
            if new:
                u.set_password("demo123")
                u.save()
            users[username] = u
        for username, name, org, town, district in BUYERS:
            u, new = User.objects.get_or_create(username=username, defaults=dict(
                first_name=name.split()[0], last_name=name.split()[-1], role="buyer",
                org_name=org, village=town, district=district, phone=f"97{rng.randint(10000000, 99999999)}"))
            if new:
                u.set_password("demo123")
                u.save()
            users[username] = u

        if not Listing.objects.exists():
            today = timezone.localdate()
            for fu, crop, variety, stock, mn, price, (a, b, c), age, desc in LISTINGS:
                f = users[fu]
                Listing.objects.create(farmer=f, crop=crops[crop], variety=variety, quantity_kg=stock, min_order_kg=mn,
                                       price_per_kg=price, freshness=a, uniformity=b, blemish=c,
                                       harvest_date=today - timedelta(days=age), village=f.village,
                                       district=f.district, description=desc)

        if not DeliverySlot.objects.exists():
            today = timezone.localdate()
            for route, days, cap, cost in [
                ("Samrala → Ludhiana city", 2, 1200, 3600), ("Doraha → Phagwara", 3, 1000, 3800),
                ("Nakodar → Jalandhar", 4, 800, 2400), ("Machhiwara → Ludhiana city", 5, 1500, 4200)]:
                DeliverySlot.objects.create(route=route, dispatch_date=today + timedelta(days=days),
                                            capacity_kg=cap, vehicle_cost=cost)

        if not Order.objects.exists():
            slots = list(DeliverySlot.objects.all())
            lst = {(l.farmer.username, l.crop.name): l for l in Listing.objects.select_related("farmer", "crop")}
            from pricing.services import current_price_map
            prices = current_price_map()
            plan = [
                ("rasoi", slots[0], [(("gurpreet", "Tomato"), 120), (("gurpreet", "Cauliflower"), 60)]),
                ("sai_mess", slots[0], [(("balwinder", "Potato"), 250), (("balwinder", "Onion"), 150)]),
                ("langar_seva", slots[2], [(("harjinder", "Carrot"), 80)]),
                ("greenbasket", slots[1], [(("manpreet", "Cabbage"), 90), (("manpreet", "Green Peas"), 30)]),
            ]
            for buyer, slot, items in plan:
                o = Order.objects.create(buyer=users[buyer], slot=slot, address=f"{users[buyer].org_name}, {users[buyer].village}")
                for key, qty in items:
                    l = lst[key]
                    OrderItem.objects.create(order=o, listing=l, quantity_kg=qty, price_per_kg=l.price_per_kg,
                                             mandi_ref_kg=prices[l.crop_id] / 100, grade=l.grade)
                    l.quantity_kg -= qty
                    l.save(update_fields=["quantity_kg"])

        if not Requirement.objects.exists():
            r1 = Requirement.objects.create(buyer=users["sai_mess"], crop=crops["Tomato"], quantity_kg_per_week=200,
                                            max_price_per_kg=26, min_grade="B", town="Phagwara", weeks=8,
                                            note="Delivery before 7 am on Mondays. Crates returned each week.")
            r2 = Requirement.objects.create(buyer=users["langar_seva"], crop=crops["Wheat"], quantity_kg_per_week=500,
                                            max_price_per_kg=28, min_grade="B", town="Jalandhar", weeks=12,
                                            note="Clean grain in 50 kg bags for the community kitchen.")
            r3 = Requirement.objects.create(buyer=users["rasoi"], crop=crops["Spinach"], quantity_kg_per_week=60,
                                            max_price_per_kg=32, min_grade="A", town="Ludhiana", weeks=6)
            Bid.objects.create(requirement=r1, farmer=users["gurpreet"], listing=lst_get(users["gurpreet"], "Tomato"),
                               quantity_kg_per_week=120, price_per_kg=24, note="Can start this Monday.")
            Bid.objects.create(requirement=r1, farmer=users["sukhdev"], listing=lst_get(users["sukhdev"], "Tomato"),
                               quantity_kg_per_week=80, price_per_kg=21, note="Softer fruit, lower price.")
            Bid.objects.create(requirement=r2, farmer=users["jaswant"], listing=lst_get(users["jaswant"], "Wheat"),
                               quantity_kg_per_week=400, price_per_kg=27, status="accepted")

        self.stdout.write(self.style.SUCCESS(
            "Demo data ready. Log in with any of: " + ", ".join(u[0] for u in FARMERS + BUYERS) + "  (password: demo123)"))


def lst_get(farmer, crop_name):
    return Listing.objects.filter(farmer=farmer, crop__name=crop_name).first()
