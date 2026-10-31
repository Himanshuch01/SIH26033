from django.contrib import admin

from .models import DeliverySlot


@admin.action(description="Dispatch selected trucks (locks logistics cost per kg on their orders)")
def dispatch(modeladmin, request, queryset):
    from market.models import Order

    for slot in queryset.filter(status="open"):
        per_kg = slot.cost_per_kg()
        Order.objects.filter(slot=slot).exclude(status="cancelled").update(
            logistics_per_kg_locked=per_kg, status="dispatched")
        slot.status = "dispatched"
        slot.save(update_fields=["status"])


@admin.register(DeliverySlot)
class DeliverySlotAdmin(admin.ModelAdmin):
    list_display = ("route", "dispatch_date", "capacity_kg", "filled", "cost_now", "status")
    list_filter = ("status", "dispatch_date")
    actions = [dispatch]

    @admin.display(description="Booked (kg)")
    def filled(self, obj):
        return int(obj.filled_kg)

    @admin.display(description="₹/kg now")
    def cost_now(self, obj):
        return obj.cost_per_kg()
