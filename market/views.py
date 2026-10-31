from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from logistics.models import DeliverySlot
from pricing import services as price_services

from . import cart as cart_api
from .forms import AddToCartForm, BidForm, CheckoutForm, ListingForm, RequirementForm
from .models import Bid, Crop, Listing, Order, OrderItem, Requirement
from .services import annotate_listings, listing_breakdown, order_breakdown, split


def role_required(role):
    def deco(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.role != role:
                messages.error(request, f"That page is only for {'farmers' if role == 'farmer' else 'buyers'}.")
                return redirect("market:dashboard")
            return view(request, *args, **kwargs)
        return wrapper
    return deco


# ------------------------------------------------------------------ listings
class ListingListView(ListView):
    model = Listing
    template_name = "market/listing_list.html"
    paginate_by = 12
    SORTS = {"new": "-created_at", "price": "price_per_kg", "-price": "-price_per_kg", "stock": "-quantity_kg"}

    def get_queryset(self):
        g = self.request.GET
        qs = Listing.objects.filter(is_active=True, quantity_kg__gt=0).select_related("crop", "farmer")
        if g.get("crop", "").isdigit():
            qs = qs.filter(crop_id=g["crop"])
        if g.get("grade") in ("A", "B", "C"):
            qs = qs.filter(grade=g["grade"])
        if g.get("q"):
            qs = qs.filter(Q(district__icontains=g["q"]) | Q(village__icontains=g["q"]) | Q(variety__icontains=g["q"]))
        return qs.order_by(self.SORTS.get(g.get("sort"), "-created_at"))

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["listings"] = annotate_listings(list(ctx["page_obj"]))
        ctx["crops"] = Crop.objects.all()
        ctx["f"] = self.request.GET
        keep = self.request.GET.copy()
        keep.pop("page", None)
        ctx["qs"] = keep.urlencode()
        return ctx


class ListingDetailView(DetailView):
    model = Listing
    template_name = "market/listing_detail.html"

    def get_queryset(self):
        return Listing.objects.select_related("crop", "farmer")

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        l = self.object
        annotate_listings([l])
        try:
            kg = Decimal(self.request.GET.get("kg", "10"))
        except InvalidOperation:
            kg = Decimal(10)
        kg = min(max(kg, Decimal(1)), l.quantity_kg) if l.quantity_kg >= 1 else Decimal(1)
        ctx.update(kg=kg, split=listing_breakdown(l, kg) if l.mandi_kg else None,
                   fc=price_services.forecast(l.crop_id))
        return ctx


@role_required("farmer")
def listing_create(request):
    form = ListingForm(request.POST or None, request.FILES or None,
                       initial={"village": request.user.village, "district": request.user.district})
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.farmer = request.user
        obj.save()
        messages.success(request, f"Listed {obj.crop} as Grade {obj.grade}.")
        return redirect(obj)
    return render(request, "market/listing_form.html", {"form": form, "editing": False})


@role_required("farmer")
def listing_update(request, pk):
    obj = get_object_or_404(Listing, pk=pk, farmer=request.user)
    form = ListingForm(request.POST or None, request.FILES or None, instance=obj, editing=True)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, "Listing updated.")
        return redirect(obj)
    return render(request, "market/listing_form.html", {"form": form, "editing": True, "obj": obj})


# ------------------------------------------------------------------ cart + checkout
@role_required("buyer")
@require_POST
def cart_add(request, pk):
    l = get_object_or_404(Listing, pk=pk, is_active=True)
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a quantity in kilograms.")
        return redirect(l)
    qty = form.cleaned_data["qty"]
    if qty < l.min_order_kg:
        messages.error(request, f"Minimum order for this listing is {l.min_order_kg:g} kg.")
        return redirect(l)
    if qty > l.quantity_kg:
        messages.error(request, f"Only {l.quantity_kg:g} kg in stock.")
        return redirect(l)
    cart_api.add(request, l, qty)
    messages.success(request, f"{qty:g} kg {l.crop} added to your cart.")
    return redirect("market:cart")


@login_required
def cart_view(request):
    lines, total_kg, subtotal = cart_api.lines(request)
    return render(request, "market/cart.html", {"lines": lines, "total_kg": total_kg, "subtotal": subtotal})


@role_required("buyer")
@require_POST
def cart_remove(request, pk):
    cart_api.remove(request, pk)
    return redirect("market:cart")


class StockError(Exception):
    pass


@role_required("buyer")
def checkout(request):
    lines, total_kg, subtotal = cart_api.lines(request)
    if not lines:
        messages.info(request, "Your cart is empty.")
        return redirect("market:listing_list")
    form = CheckoutForm(request.POST or None, total_kg=total_kg,
                        initial={"address": ", ".join(x for x in [request.user.village, request.user.district] if x)})
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                slot = DeliverySlot.objects.select_for_update().get(pk=form.cleaned_data["slot"].pk)
                if slot.kg_left < total_kg:
                    raise StockError("That truck filled up while you were checking out. Pick another one.")
                stock = {l.pk: l for l in Listing.objects.select_for_update().filter(pk__in=[x["listing"].pk for x in lines])}
                prices = price_services.current_price_map()
                order = Order.objects.create(buyer=request.user, slot=slot,
                                             address=form.cleaned_data["address"], note=form.cleaned_data["note"])
                for line in lines:
                    l = stock[line["listing"].pk]
                    if not l.is_active or l.quantity_kg < line["qty"]:
                        raise StockError(f"{l.crop} from {l.farmer} no longer has {line['qty']:g} kg.")
                    quintal = prices.get(l.crop_id)
                    OrderItem.objects.create(order=order, listing=l, quantity_kg=line["qty"], price_per_kg=l.price_per_kg,
                                             mandi_ref_kg=(quintal / 100) if quintal else 0, grade=l.grade)
                    l.quantity_kg -= line["qty"]
                    l.save(update_fields=["quantity_kg"])
        except StockError as e:
            messages.error(request, str(e))
            return redirect("market:cart")
        cart_api.clear(request)
        messages.success(request, f"Order #{order.pk} placed on the {order.slot.route} truck.")
        return redirect(order)
    return render(request, "market/checkout.html", {"form": form, "lines": lines, "total_kg": total_kg, "subtotal": subtotal})


# ------------------------------------------------------------------ orders
@login_required
def order_list(request):
    if request.user.is_farmer:
        items = (OrderItem.objects.filter(listing__farmer=request.user)
                 .select_related("order__buyer", "order__slot", "listing__crop").order_by("-order__created_at"))
        return render(request, "market/order_list.html", {"items": items, "farmer_view": True})
    orders = request.user.orders.select_related("slot").prefetch_related("items__listing__crop")
    return render(request, "market/order_list.html", {"orders": orders, "farmer_view": False})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("buyer", "slot"), pk=pk)
    user = request.user
    is_owner = order.buyer_id == user.pk
    my_items = order.items.filter(listing__farmer=user).select_related("listing__crop") if user.is_farmer else []
    if not (is_owner or user.is_staff or my_items):
        messages.error(request, "That order isn't yours.")
        return redirect("market:dashboard")
    if is_owner or user.is_staff:
        return render(request, "market/order_detail.html", {"order": order, "b": order_breakdown(order)})
    return render(request, "market/order_detail.html", {"order": order, "farmer_items": my_items, "farmer_view": True})


@role_required("buyer")
@require_POST
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    if not order.can_cancel:
        messages.error(request, "This order is already on the truck and can't be cancelled.")
        return redirect(order)
    with transaction.atomic():
        for item in order.items.select_related("listing"):
            item.listing.quantity_kg += item.quantity_kg
            item.listing.save(update_fields=["quantity_kg"])
        order.status = "cancelled"
        order.save(update_fields=["status"])
    messages.success(request, "Order cancelled and the stock returned to the farmers.")
    return redirect(order)


# ------------------------------------------------------------------ requirement board
def requirement_list(request):
    qs = Requirement.objects.filter(status="open").select_related("crop", "buyer").annotate(n_bids=Count("bids"))
    if request.GET.get("crop", "").isdigit():
        qs = qs.filter(crop_id=request.GET["crop"])
    return render(request, "market/requirement_list.html",
                  {"reqs": qs, "crops": Crop.objects.all(), "f": request.GET})


def requirement_detail(request, pk):
    req = get_object_or_404(Requirement.objects.select_related("crop", "buyer"), pk=pk)
    user = request.user
    my_bid = req.bids.filter(farmer=user).first() if user.is_authenticated and user.is_farmer else None
    form = None
    if user.is_authenticated and user.is_farmer and not my_bid and req.status == "open":
        form = BidForm(request.POST or None, requirement=req, farmer=user)
        if request.method == "POST" and form.is_valid():
            bid = form.save(commit=False)
            bid.requirement, bid.farmer = req, user
            bid.save()
            messages.success(request, "Your bid is on the board.")
            return redirect(req)
    return render(request, "market/requirement_detail.html", {
        "req": req, "bids": req.bids.select_related("farmer", "listing"), "form": form, "my_bid": my_bid,
        "is_owner": user.is_authenticated and req.buyer_id == user.pk,
    })


@role_required("buyer")
def requirement_create(request):
    form = RequirementForm(request.POST or None, initial={"town": request.user.village})
    if request.method == "POST" and form.is_valid():
        r = form.save(commit=False)
        r.buyer = request.user
        r.save()
        messages.success(request, "Your requirement is on the board. Farmers can bid now.")
        return redirect(r)
    return render(request, "market/requirement_form.html", {"form": form})


@role_required("buyer")
@require_POST
def bid_decide(request, pk, action):
    bid = get_object_or_404(Bid.objects.select_related("requirement"), pk=pk, requirement__buyer=request.user)
    req = bid.requirement
    if action == "accept":
        if bid.quantity_kg_per_week > req.remaining_kg:
            messages.error(request, f"Only {req.remaining_kg:g} kg/week is still unfilled. Ask the farmer to lower the quantity or decline.")
            return redirect(req)
        bid.status = "accepted"
        bid.save(update_fields=["status"])
        if req.remaining_kg <= 0:
            req.status = "filled"
            req.save(update_fields=["status"])
        messages.success(request, f"Accepted {bid.farmer}'s bid for {bid.quantity_kg_per_week:g} kg/week.")
    else:
        bid.status = "rejected"
        bid.save(update_fields=["status"])
    return redirect(req)


# ------------------------------------------------------------------ dashboard
@login_required
def dashboard(request):
    user = request.user
    if user.is_farmer:
        listings = annotate_listings(list(user.listings.select_related("crop")))
        items = list(OrderItem.objects.filter(listing__farmer=user).exclude(order__status="cancelled")
                     .select_related("order__buyer", "listing__crop", "order__slot").order_by("-order__created_at"))
        crop_ids = {l.crop_id for l in listings}
        open_reqs = (Requirement.objects.filter(status="open", crop_id__in=crop_ids).exclude(bids__farmer=user)
                     .select_related("crop", "buyer")[:5])
        return render(request, "market/dashboard_farmer.html", {
            "listings": listings, "items": items[:8],
            "earned": sum((i.line_total for i in items), Decimal(0)),
            "kg_sold": sum((i.quantity_kg for i in items), Decimal(0)),
            "stock_value": sum((l.quantity_kg * l.price_per_kg for l in listings if l.is_active), Decimal(0)),
            "open_reqs": open_reqs, "bids": user.bids.select_related("requirement__crop", "requirement__buyer")[:6],
        })
    return render(request, "market/dashboard_buyer.html", {
        "orders": user.orders.select_related("slot").prefetch_related("items")[:5],
        "reqs": user.requirements.select_related("crop").annotate(n_bids=Count("bids")),
    })
