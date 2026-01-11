from django.contrib import admin
from .models import Service

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'base_price', 'price_strategy')
    list_filter = ('gym', 'price_strategy')
