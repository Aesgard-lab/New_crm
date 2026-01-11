from django.contrib import admin
from .models import Franchise, Gym


@admin.register(Franchise)
class FranchiseAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Gym)
class GymAdmin(admin.ModelAdmin):
    list_display = ("name", "franchise", "is_active", "created_at")
    list_filter = ("is_active", "franchise")
    search_fields = ("name",)
