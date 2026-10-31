from django.contrib import admin

from .models import Bid, Crop, Listing, Order, OrderItem, Requirement


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ("name", "name_hi", "name_pa", "category")
    search_fields = ("name",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("crop", "farmer", "grade", "quantity_kg", "price_per_kg", "district", "is_active")
    list_filter = ("grade", "crop", "district", "is_active")
    search_fields = ("farmer__username", "village")


class ItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "slot", "status", "created_at")
    list_filter = ("status",)
    inlines = [ItemInline]


class BidInline(admin.TabularInline):
    model = Bid
    extra = 0


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ("crop", "buyer", "quantity_kg_per_week", "status", "created_at")
    list_filter = ("status", "crop")
    inlines = [BidInline]
