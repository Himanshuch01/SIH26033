from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import DeliverySlot
from .services import dispatch_slot


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


@login_required
@require_POST
def dispatch_slot_view(request, pk):
    if not request.user.is_staff:
        messages.error(request, "Only staff can dispatch trucks.")
        return redirect("logistics:board")
    slot = get_object_or_404(DeliverySlot, pk=pk)
    if slot.status == "open":
        dispatch_slot(slot)
        messages.success(request, f"Truck for {slot.route} dispatched.")
    else:
        messages.info(request, "This truck is already dispatched or cancelled.")
    return redirect("logistics:board")
