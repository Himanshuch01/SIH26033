def dispatch_slot(slot):
    """Locks logistics cost per kg on all non-cancelled orders and marks slot dispatched."""
    from market.models import Order

    per_kg = slot.cost_per_kg()
    Order.objects.filter(slot=slot).exclude(status="cancelled").update(
        logistics_per_kg_locked=per_kg, status="dispatched"
    )
    slot.status = "dispatched"
    slot.save(update_fields=["status"])
    return per_kg
