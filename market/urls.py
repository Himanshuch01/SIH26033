from django.urls import path

from . import views

app_name = "market"
urlpatterns = [
    path("", views.ListingListView.as_view(), name="listing_list"),
    path("listing/new/", views.listing_create, name="listing_create"),
    path("listing/<int:pk>/", views.ListingDetailView.as_view(), name="listing_detail"),
    path("listing/<int:pk>/edit/", views.listing_update, name="listing_update"),
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/cancel/", views.order_cancel, name="order_cancel"),
    path("requirements/", views.requirement_list, name="requirement_list"),
    path("requirements/new/", views.requirement_create, name="requirement_create"),
    path("requirements/<int:pk>/", views.requirement_detail, name="requirement_detail"),
    path("bids/<int:pk>/<str:action>/", views.bid_decide, name="bid_decide"),
    path("desk/", views.dashboard, name="dashboard"),
]
