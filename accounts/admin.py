from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class FasalUserAdmin(UserAdmin):
    list_display = ("username", "display_name", "role", "village", "district", "is_staff")
    list_filter = ("role", "district", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Fasal Bazaar profile", {"fields": ("role", "phone", "village", "district", "org_name")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Fasal Bazaar profile", {"fields": ("role", "phone", "village", "district", "org_name")}),
    )
