from decimal import ROUND_HALF_UP, Decimal

from django.db import models
from django.db.models import Sum
from django.utils import timezone

CELLS = 20  # segments in the truck meter


class SlotManager(models.Manager):
    def open_slots(self):
        return self.filter(status="open", dispatch_date__gte=timezone.localdate()).order_by("dispatch_date")


class DeliverySlot(models.Model):
    """A shared truck going along one route on one day.

    Every order placed on the slot adds its kilograms; the fixed vehicle cost is
    divided over all kilograms, so cost per kg falls as the truck fills.
    """

    STATUS = [("open", "Open"), ("dispatched", "Dispatched"), ("cancelled", "Cancelled")]

    route = models.CharField(max_length=120, help_text="e.g. Samrala → Ludhiana city")
    dispatch_date = models.DateField()
    capacity_kg = models.PositiveIntegerField(default=1200)
    vehicle_cost = models.DecimalField("Fixed vehicle cost (₹)", max_digits=8, decimal_places=2, default=3600)
    min_fill_pct = models.PositiveSmallIntegerField(
        default=30, help_text="Cost per kg is never calculated as if the truck were emptier than this."
    )
    status = models.CharField(max_length=12, choices=STATUS, default="open")

    objects = SlotManager()

    class Meta:
        ordering = ["dispatch_date", "route"]

    def __str__(self):
        return f"{self.route} on {self.dispatch_date:%d %b}"

    # ---- numbers -------------------------------------------------------
    @property
    def filled_kg(self):
        from market.models import OrderItem

        if self.pk is None:
            return Decimal(0)
        total = (
            OrderItem.objects.filter(order__slot=self)
            .exclude(order__status="cancelled")
            .aggregate(s=Sum("quantity_kg"))["s"]
        )
        return Decimal(total or 0)

    @property
    def kg_left(self):
        return max(Decimal(self.capacity_kg) - self.filled_kg, Decimal(0))

    @property
    def fill_pct(self):
        return min(float(self.filled_kg) / self.capacity_kg * 100, 100) if self.capacity_kg else 0

    def cost_per_kg(self, extra_kg=0):
        floor = Decimal(self.capacity_kg) * self.min_fill_pct / 100
        effective = max(self.filled_kg + Decimal(extra_kg), floor, Decimal(1))
        return (self.vehicle_cost / effective).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def full_truck_cost_per_kg(self):
        return (self.vehicle_cost / Decimal(self.capacity_kg)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def meter_cells(self, extra_kg=0):
        """['f','f','e','o',...]  f = already booked, e = your order, o = empty."""
        done = round(float(self.filled_kg) / self.capacity_kg * CELLS)
        yours = round(float(extra_kg) / self.capacity_kg * CELLS) if extra_kg else 0
        done = min(done, CELLS)
        yours = min(yours, CELLS - done)
        return ["f"] * done + ["e"] * yours + ["o"] * (CELLS - done - yours)
