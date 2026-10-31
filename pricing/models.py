from django.db import models


class MandiPrice(models.Model):
    """One daily modal price (₹ per quintal) for one crop in one mandi.

    Load real data from Agmarknet / data.gov.in with `manage.py import_prices file.csv`.
    """

    crop = models.ForeignKey("market.Crop", on_delete=models.CASCADE, related_name="prices")
    market = models.CharField(max_length=80)
    date = models.DateField(db_index=True)
    modal_price = models.DecimalField("Modal price (₹/quintal)", max_digits=9, decimal_places=2)
    source = models.CharField(max_length=30, default="sample")

    class Meta:
        ordering = ["-date"]
        indexes = [models.Index(fields=["crop", "date"])]

    def __str__(self):
        return f"{self.crop} @ {self.market} {self.date}: ₹{self.modal_price}/q"
