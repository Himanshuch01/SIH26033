from django.urls import path

from . import views

app_name = "pricing"
urlpatterns = [
    path("", views.insights, name="insights"),
    path("hint/", views.price_hint, name="hint"),
]
