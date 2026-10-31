from datetime import date
from decimal import Decimal

from django import forms
from django.urls import reverse_lazy

from logistics.models import DeliverySlot

from .models import Bid, Listing, Requirement


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ["crop", "variety", "quantity_kg", "min_order_kg", "price_per_kg",
                  "freshness", "uniformity", "blemish", "harvest_date",
                  "village", "district", "description", "photo", "is_active"]
        widgets = {
            "harvest_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "freshness": forms.RadioSelect, "uniformity": forms.RadioSelect, "blemish": forms.RadioSelect,
            "description": forms.Textarea(attrs={"rows": 3}),
            "crop": forms.Select(attrs={
                "hx-get": reverse_lazy("pricing:hint"), "hx-target": "#price-hint",
                "hx-trigger": "change, load",
            }),
        }

    def __init__(self, *args, editing=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not editing:
            del self.fields["is_active"]
        else:
            self.fields["is_active"].label = "Show this listing in the market"

    def clean(self):
        data = super().clean()
        qty, mn = data.get("quantity_kg"), data.get("min_order_kg")
        if qty and mn and mn > qty:
            self.add_error("min_order_kg", "Minimum order cannot be more than your stock.")
        if data.get("harvest_date") and data["harvest_date"] > date.today():
            self.add_error("harvest_date", "Harvest date cannot be in the future.")
        return data


class AddToCartForm(forms.Form):
    qty = forms.DecimalField(min_value=Decimal("1"), max_digits=8, decimal_places=1)


class CheckoutForm(forms.Form):
    slot = forms.ModelChoiceField(queryset=DeliverySlot.objects.none(), label="Delivery truck", empty_label="Choose a truck")
    address = forms.CharField(label="Delivery address", widget=forms.Textarea(attrs={"rows": 3}))
    note = forms.CharField(label="Note for the driver", max_length=200, required=False)

    def __init__(self, *args, total_kg=Decimal(0), **kwargs):
        super().__init__(*args, **kwargs)
        self.total_kg = total_kg
        self.fields["slot"].queryset = DeliverySlot.objects.open_slots()
        self.fields["slot"].label_from_instance = lambda s: f"{s.route} - {s.dispatch_date:%a %d %b}"
        self.fields["slot"].widget.attrs.update({
            "hx-get": reverse_lazy("logistics:preview"), "hx-target": "#slot-preview",
            "hx-trigger": "change, load", "hx-vals": f'{{"kg": "{total_kg}"}}',
        })

    def clean_slot(self):
        slot = self.cleaned_data["slot"]
        if slot.kg_left < self.total_kg:
            raise forms.ValidationError(f"Only {slot.kg_left:.0f} kg of space is left on this truck. Pick another one.")
        return slot


class RequirementForm(forms.ModelForm):
    class Meta:
        model = Requirement
        fields = ["crop", "quantity_kg_per_week", "max_price_per_kg", "min_grade", "town", "weeks", "note"]


class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = ["listing", "quantity_kg_per_week", "price_per_kg", "note"]

    def __init__(self, *args, requirement=None, farmer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.requirement = requirement
        self.fields["listing"].queryset = Listing.objects.filter(farmer=farmer, crop=requirement.crop, is_active=True)
        self.fields["listing"].label = "Which of your listings will this come from?"
        self.fields["listing"].required = False

    def clean_price_per_kg(self):
        price, cap = self.cleaned_data["price_per_kg"], self.requirement.max_price_per_kg
        if cap and price > cap:
            raise forms.ValidationError(f"The buyer's limit is ₹{cap}/kg.")
        return price
