"""Import real Agmarknet / data.gov.in price rows.

CSV columns (header names are matched case-insensitively):
    commodity, market, date (YYYY-MM-DD or DD/MM/YYYY), modal_price   [₹ per quintal]

Usage:  python manage.py import_prices prices.csv
Crops are matched by name (case-insensitive); unknown commodities are skipped and listed.
"""
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from market.models import Crop
from pricing.models import MandiPrice


def parse_date(s):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(s)


class Command(BaseCommand):
    help = "Import daily mandi modal prices from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file")
        parser.add_argument("--source", default="agmarknet")

    def handle(self, *args, **opts):
        crops = {c.name.lower(): c for c in Crop.objects.all()}
        made, skipped = 0, set()
        try:
            fh = open(opts["csv_file"], newline="", encoding="utf-8-sig")
        except OSError as e:
            raise CommandError(e)
        with fh:
            for row in csv.DictReader(fh):
                row = {k.strip().lower(): (v or "").strip() for k, v in row.items()}
                crop = crops.get(row.get("commodity", "").lower())
                if not crop:
                    skipped.add(row.get("commodity", "?"))
                    continue
                try:
                    MandiPrice.objects.create(
                        crop=crop, market=row["market"], date=parse_date(row["date"]),
                        modal_price=Decimal(row["modal_price"]), source=opts["source"],
                    )
                    made += 1
                except (KeyError, ValueError, InvalidOperation):
                    continue
        self.stdout.write(self.style.SUCCESS(f"Imported {made} rows."))
        if skipped:
            self.stdout.write(f"Skipped unknown commodities: {', '.join(sorted(skipped))}")
