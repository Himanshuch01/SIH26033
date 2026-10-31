from django.contrib import admin

from .models import MandiPrice


@admin.register(MandiPrice)
class MandiPriceAdmin(admin.ModelAdmin):
    list_display = ("crop", "market", "date", "modal_price", "source")
    list_filter = ("crop", "market", "source")
    date_hierarchy = "date"
