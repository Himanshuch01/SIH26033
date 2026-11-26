from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from logistics.models import DeliverySlot
from market.models import Bid, Listing, Order, Requirement, grade_from_scores
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
        r.min_grade = "B"
        r.save()
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

    def test_cart_badge_only_active_in_stock(self):
        self.client.login(username="rasoi", password="demo123")
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.context["cart_count"], 0)

        l = Listing.objects.filter(quantity_kg__gt=10, is_active=True).first()
        self.client.post(reverse("market:cart_add", args=[l.pk]), {"qty": "5"})
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.context["cart_count"], 1)

        l.is_active = False
        l.save(update_fields=["is_active"])
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.context["cart_count"], 0)

        l.is_active = True
        l.quantity_kg = 0
        l.save(update_fields=["is_active", "quantity_kg"])
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.context["cart_count"], 0)

    def test_order_lifecycle_and_permissions(self):
        slot = DeliverySlot.objects.open_slots().first()
        self.client.login(username="gurpreet", password="demo123")
        resp = self.client.post(reverse("logistics:dispatch", args=[slot.pk]))
        slot.refresh_from_db()
        self.assertEqual(slot.status, "open")

        admin_user = User.objects.create_superuser(username="adminuser", password="adminpassword", email="admin@example.com")
        self.client.login(username="adminuser", password="adminpassword")
        resp = self.client.post(reverse("logistics:dispatch", args=[slot.pk]))
        self.assertEqual(resp.status_code, 302)
        slot.refresh_from_db()
        self.assertEqual(slot.status, "dispatched")

        order = Order.objects.filter(slot=slot).exclude(status="cancelled").first()
        if not order:
            buyer = User.objects.get(username="rasoi")
            order = Order.objects.create(buyer=buyer, slot=slot, address="Test address", status="dispatched")
        else:
            self.assertEqual(order.status, "dispatched")

        # Another buyer cannot mark delivered
        self.client.login(username="greenbasket", password="demo123")
        resp = self.client.post(reverse("market:order_delivered", args=[order.pk]))
        self.assertEqual(resp.status_code, 404)
        order.refresh_from_db()
        self.assertNotEqual(order.status, "delivered")

        # Owner buyer can confirm delivery
        self.client.login(username=order.buyer.username, password="demo123")
        resp = self.client.post(reverse("market:order_delivered", args=[order.pk]))
        self.assertEqual(resp.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, "delivered")

    def test_bid_withdrawal_and_permissions(self):
        r = Requirement.objects.get(crop__name="Wheat")
        r.status = "open"
        r.save()
        farmer = User.objects.get(username="harjinder")
        r.bids.filter(farmer=farmer).delete()

        bid = Bid.objects.create(requirement=r, farmer=farmer, quantity_kg_per_week=50, price_per_kg=25, status="pending")

        # Another farmer cannot withdraw
        self.client.login(username="gurpreet", password="demo123")
        resp = self.client.post(reverse("market:bid_withdraw", args=[bid.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Bid.objects.filter(pk=bid.pk).exists())

        # Cannot withdraw accepted bid
        bid.status = "accepted"
        bid.save(update_fields=["status"])
        self.client.login(username="harjinder", password="demo123")
        resp = self.client.post(reverse("market:bid_withdraw", args=[bid.pk]))
        self.assertTrue(Bid.objects.filter(pk=bid.pk).exists())

        # Can withdraw pending bid
        bid.status = "pending"
        bid.save(update_fields=["status"])
        resp = self.client.post(reverse("market:bid_withdraw", args=[bid.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Bid.objects.filter(pk=bid.pk).exists())

        # Farmer can bid again after withdrawal
        resp = self.client.get(r.get_absolute_url())
        self.assertContains(resp, "Submit bid")

    def test_requirement_min_grade_enforcement(self):
        from market.forms import BidForm
        r = Requirement.objects.get(crop__name="Spinach")
        r.min_grade = "A"
        r.save()
        harjinder = User.objects.get(username="harjinder")
        l = Listing.objects.get(farmer=harjinder, crop__name="Spinach")
        self.assertEqual(l.grade, "B")

        form = BidForm(requirement=r, farmer=harjinder)
        self.assertNotIn(l, form.fields["listing"].queryset)
        self.assertIn("You have no active Grade A or better listings", form.fields["listing"].help_text)

        invalid_form = BidForm({"listing": l.pk, "quantity_kg_per_week": "50", "price_per_kg": "28"}, requirement=r, farmer=harjinder)
        self.assertFalse(invalid_form.is_valid())

        r.min_grade = "B"
        r.save()
        form_b = BidForm(requirement=r, farmer=harjinder)
        self.assertIn(l, form_b.fields["listing"].queryset)

    def test_home_page_no_negative_savings(self):
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        self.assertNotIn("-₹", content)
        self.assertNotIn("(-", content)

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
