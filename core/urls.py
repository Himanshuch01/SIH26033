from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("lang/<str:code>/", views.set_lang, name="set_lang"),
]
