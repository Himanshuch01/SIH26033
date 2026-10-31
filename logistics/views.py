from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404, render

from .models import DeliverySlot


def board(request):
    slots = list(DeliverySlot.objects.open_slots())
    for s in slots:
        s.cells = s.meter_cells()
    return render(request, "logistics/board.html", {"slots": slots})


def meter(request, pk):
    """HTMX polling fragment: the live truck meter."""
    slot = get_object_or_404(DeliverySlot, pk=pk)
    slot.cells = slot.meter_cells()
    return render(request, "logistics/_meter.html", {"slot": slot})


def preview(request):
    """HTMX fragment on checkout: what this truck costs per kg *with your order added*."""
    slot = DeliverySlot.objects.filter(pk=request.GET.get("slot") or 0).first()
    try:
        extra = Decimal(request.GET.get("kg", "0"))
    except InvalidOperation:
        extra = Decimal(0)
    ctx = {"slot": slot, "extra": extra}
    if slot:
        slot.cells = slot.meter_cells(extra)
        ctx.update(now_cost=slot.cost_per_kg(), with_cost=slot.cost_per_kg(extra),
                   fits=extra <= slot.kg_left)
    return render(request, "logistics/_preview.html", ctx)
