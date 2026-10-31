from django.urls import path

from . import views

app_name = "logistics"
urlpatterns = [
    path("", views.board, name="board"),
    path("meter/<int:pk>/", views.meter, name="meter"),
    path("preview/", views.preview, name="preview"),
]
