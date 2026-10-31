from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.urls import reverse

GRADE_MULT = {"A": Decimal("1.10"), "B": Decimal("1.00"), "C": Decimal("0.88")}


def grade_from_scores(freshness, uniformity, blemish):
    """Rule-based grade: three checks scored 1-3. 8-9 -> A, 6-7 -> B, 3-5 -> C."""
    total = freshness + uniformity + blemish
    return "A" if total >= 8 else "B" if total >= 6 else "C"


class Crop(models.Model):
    CATEGORY = [("veg", "Vegetable"), ("fruit", "Fruit"), ("grain", "Grain"), ("pulse", "Pulse")]
    name = models.CharField(max_length=60, unique=True)
    name_hi = models.CharField(max_length=60, blank=True)
    name_pa = models.CharField(max_length=60, blank=True)
    category = models.CharField(max_length=6, choices=CATEGORY, default="veg")
    swatch = models.CharField("Swatch colour", max_length=7, default="#2b7a4b")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def local_name(self, lang="en"):
        return (getattr(self, f"name_{lang}", "") if lang != "en" else "") or self.name


class Listing(models.Model):
    SCORE = [(1, "Poor"), (2, "Fair"), (3, "Good")]

    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings")
    crop = models.ForeignKey(Crop, on_delete=models.PROTECT, related_name="listings")
    variety = models.CharField(max_length=60, blank=True, help_text="e.g. Hybrid, Desi, Pusa Ruby")
    quantity_kg = models.DecimalField("Stock (kg)", max_digits=8, decimal_places=1, validators=[MinValueValidator(1)])
    min_order_kg = models.DecimalField("Minimum order (kg)", max_digits=6, decimal_places=1, default=5)
    price_per_kg = models.DecimalField("Your price (₹/kg)", max_digits=7, decimal_places=2, validators=[MinValueValidator(1)])

    # grading checklist
    freshness = models.PositiveSmallIntegerField(choices=SCORE, default=3, help_text="Grains / pulses: dryness")
    uniformity = models.PositiveSmallIntegerField("Size uniformity", choices=SCORE, default=3)
    blemish = models.PositiveSmallIntegerField("Clean of damage and spots", choices=SCORE, default=3)
    grade = models.CharField(max_length=1, editable=False, default="B")

    harvest_date = models.DateField()
    village = models.CharField(max_length=80)
    district = models.CharField(max_length=60)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="listings/", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.grade = grade_from_scores(self.freshness, self.uniformity, self.blemish)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.crop} ({self.grade}) by {self.farmer}"

    def get_absolute_url(self):
        return reverse("market:listing_detail", args=[self.pk])

    @property
    def grade_multiplier(self):
        return GRADE_MULT[self.grade]


class Order(models.Model):
    STATUS = [("placed", "Placed"), ("dispatched", "On the truck"), ("delivered", "Delivered"), ("cancelled", "Cancelled")]

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    slot = models.ForeignKey("logistics.DeliverySlot", on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=12, choices=STATUS, default="placed")
    address = models.TextField()
    note = models.CharField(max_length=200, blank=True)
    logistics_per_kg_locked = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk}"

    def get_absolute_url(self):
        return reverse("market:order_detail", args=[self.pk])

    @property
    def can_cancel(self):
        return self.status == "placed"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="order_items")
    quantity_kg = models.DecimalField(max_digits=8, decimal_places=1)
    price_per_kg = models.DecimalField(max_digits=7, decimal_places=2)       # snapshot at purchase
    mandi_ref_kg = models.DecimalField(max_digits=7, decimal_places=2, default=0)  # snapshot of mandi ₹/kg
    grade = models.CharField(max_length=1, default="B")

    @property
    def line_total(self):
        return self.quantity_kg * self.price_per_kg


class Requirement(models.Model):
    """A bulk buyer posts a standing weekly need; farmers bid to fill it."""

    STATUS = [("open", "Open"), ("filled", "Filled"), ("closed", "Closed")]
    GRADES = [("A", "Grade A only"), ("B", "Grade B or better"), ("C", "Any grade")]

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="requirements")
    crop = models.ForeignKey(Crop, on_delete=models.PROTECT)
    quantity_kg_per_week = models.DecimalField("Needed per week (kg)", max_digits=8, decimal_places=1, validators=[MinValueValidator(10)])
    max_price_per_kg = models.DecimalField("Highest price you'll pay (₹/kg)", max_digits=7, decimal_places=2, null=True, blank=True)
    min_grade = models.CharField(max_length=1, choices=GRADES, default="B")
    town = models.CharField("Delivery town", max_length=80)
    weeks = models.PositiveSmallIntegerField("For how many weeks", default=4)
    note = models.CharField(max_length=240, blank=True)
    status = models.CharField(max_length=8, choices=STATUS, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.buyer} needs {self.quantity_kg_per_week} kg {self.crop}/wk"

    def get_absolute_url(self):
        return reverse("market:requirement_detail", args=[self.pk])

    @property
    def committed_kg(self):
        return self.bids.filter(status="accepted").aggregate(s=Sum("quantity_kg_per_week"))["s"] or Decimal(0)

    @property
    def remaining_kg(self):
        return max(self.quantity_kg_per_week - self.committed_kg, Decimal(0))

    @property
    def committed_pct(self):
        return min(float(self.committed_kg / self.quantity_kg_per_week) * 100, 100)


class Bid(models.Model):
    STATUS = [("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Declined")]

    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE, related_name="bids")
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bids")
    listing = models.ForeignKey(Listing, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_kg_per_week = models.DecimalField("I can supply per week (kg)", max_digits=8, decimal_places=1, validators=[MinValueValidator(1)])
    price_per_kg = models.DecimalField("My price (₹/kg)", max_digits=7, decimal_places=2, validators=[MinValueValidator(1)])
    note = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price_per_kg"]
        unique_together = ("requirement", "farmer")

    def __str__(self):
        return f"{self.farmer} bids {self.quantity_kg_per_week} kg @ ₹{self.price_per_kg}"
