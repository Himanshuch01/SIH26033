from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from logistics.models import DeliverySlot
from market.models import Listing, Order, Requirement, grade_from_scores
from market.services import split
from pricing import services as price_services


class GradeAndMoneyTests(TestCase):
    def test_grade_rubric(self):
        self.assertEqual(grade_from_scores(3, 3, 2), "A")
        self.assertEqual(grade_from_scores(2, 2, 2), "B")
        self.assertEqual(grade_from_scores(1, 2, 1), "C")

    def test_split_adds_up(self):
        s = split(Decimal("1000"), 50, Decimal("4.00"), Decimal("1800"))
        self.assertEqual(s["fee"], Decimal("20.00"))
        self.assertEqual(s["total"], Decimal("1220.00"))
        self.assertEqual(s["saving"], Decimal("580.00"))

    def test_truck_cost_falls_as_it_fills(self):
        slot = DeliverySlot(route="A to B", dispatch_date="2030-01-01", capacity_kg=1000, vehicle_cost=3000, min_fill_pct=30)
        self.assertEqual(slot.cost_per_kg(0), Decimal("10.00"))   # floor at 30% -> 3000/300
        self.assertEqual(slot.cost_per_kg(1000), Decimal("3.00"))  # full truck


class FlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_public_pages(self):
        for name in ["core:home", "market:listing_list", "market:requirement_list", "logistics:board",
                     "pricing:insights", "accounts:login", "accounts:register"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        l = Listing.objects.first()
        self.assertEqual(self.client.get(l.get_absolute_url()).status_code, 200)
        r = Requirement.objects.first()
        self.assertEqual(self.client.get(r.get_absolute_url()).status_code, 200)

    def test_language_toggle(self):
        self.client.get(reverse("core:set_lang", args=["hi"]))
        self.assertIn("खेत से घर तक", self.client.get(reverse("core:home")).content.decode())

    def test_forecast(self):
        crop = Listing.objects.first().crop
        fc = price_services.forecast(crop.pk)
        self.assertIn(fc["advice"], {"hold", "sell", "steady"})
        self.assertEqual(len(fc["forecast"]), 6)

    def test_buyer_can_order_and_stock_drops(self):
        self.client.login(username="greenbasket", password="demo123")
        l = Listing.objects.filter(farmer__username="gurpreet", crop__name="Tomato").first()
        before = l.quantity_kg
        self.assertEqual(self.client.post(reverse("market:cart_add", args=[l.pk]), {"qty": "20"}).status_code, 302)
        slot = DeliverySlot.objects.open_slots().first()
        resp = self.client.post(reverse("market:checkout"), {"slot": slot.pk, "address": "Ludhiana", "note": ""})
        self.assertEqual(resp.status_code, 302)
        order = Order.objects.filter(buyer__username="greenbasket").latest("pk")
        l.refresh_from_db()
        self.assertEqual(l.quantity_kg, before - 20)
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 200)
        # cancel restores stock
        self.client.post(reverse("market:order_cancel", args=[order.pk]))
        l.refresh_from_db()
        self.assertEqual(l.quantity_kg, before)

    def test_min_order_enforced(self):
        self.client.login(username="rasoi", password="demo123")
        l = Listing.objects.first()
        self.client.post(reverse("market:cart_add", args=[l.pk]), {"qty": "1"})
        self.assertNotIn(str(l.pk), self.client.session.get("cart", {}))

    def test_farmer_cannot_buy_and_dashboards_render(self):
        self.client.login(username="gurpreet", password="demo123")
        l = Listing.objects.first()
        self.client.post(reverse("market:cart_add", args=[l.pk]), {"qty": "20"})
        self.assertFalse(self.client.session.get("cart"))
        for name in ["market:dashboard", "market:order_list"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.client.logout()
        self.client.login(username="rasoi", password="demo123")
        for name in ["market:dashboard", "market:order_list", "market:cart"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        o = Order.objects.filter(buyer__username="rasoi").first()
        self.assertEqual(self.client.get(o.get_absolute_url()).status_code, 200)

    def test_bid_and_accept(self):
        r = Requirement.objects.get(crop__name="Spinach")
        self.client.login(username="harjinder", password="demo123")
        l = Listing.objects.get(farmer__username="harjinder", crop__name="Spinach")
        resp = self.client.post(r.get_absolute_url(), {"listing": l.pk, "quantity_kg_per_week": "60", "price_per_kg": "28", "note": ""})
        self.assertEqual(resp.status_code, 302)
        bid = r.bids.get()
        self.client.logout()
        self.client.login(username="rasoi", password="demo123")
        self.client.post(reverse("market:bid_decide", args=[bid.pk, "accept"]))
        r.refresh_from_db()
        self.assertEqual(r.status, "filled")

    def test_htmx_fragments(self):
        slot = DeliverySlot.objects.open_slots().first()
        self.assertContains(self.client.get(reverse("logistics:preview"), {"slot": slot.pk, "kg": "100"}), "per kg" if False else "Delivery is")
        self.assertEqual(self.client.get(reverse("pricing:hint"), {"crop": Listing.objects.first().crop_id}).status_code, 200)
        self.assertEqual(self.client.get(reverse("logistics:meter", args=[slot.pk])).status_code, 200)

    def test_register_creates_farmer(self):
        resp = self.client.post(reverse("accounts:register"), {
            "username": "newfarmer", "first_name": "Test", "role": "farmer", "phone": "", "village": "X",
            "district": "Y", "org_name": "", "password1": "Str0ngPass!9", "password2": "Str0ngPass!9"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.get(username="newfarmer").is_farmer)
