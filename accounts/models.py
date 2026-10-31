from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user: one table, a `role` decides what the person can do."""

    class Role(models.TextChoices):
        FARMER = "farmer", "Farmer / FPO"
        BUYER = "buyer", "Buyer (household, mess, shop, restaurant)"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.BUYER)
    phone = models.CharField(max_length=15, blank=True)
    village = models.CharField("Village / town", max_length=80, blank=True)
    district = models.CharField(max_length=60, blank=True)
    org_name = models.CharField("FPO or business name", max_length=120, blank=True)

    @property
    def is_farmer(self):
        return self.role == self.Role.FARMER

    @property
    def is_buyer(self):
        return self.role == self.Role.BUYER

    @property
    def display_name(self):
        return self.org_name or self.get_full_name() or self.username

    def __str__(self):
        return self.display_name
