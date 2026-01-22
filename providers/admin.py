from django.contrib import admin
from .models import (
    Provider,
    ProviderContact,
    ProviderDocument,
    ProviderRating,
    ProviderItem,
    PurchaseOrder,
    PurchaseOrderLine,
)


class ProviderContactInline(admin.TabularInline):
    model = ProviderContact
    extra = 0


class ProviderItemInline(admin.TabularInline):
    model = ProviderItem
    extra = 0


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "gym", "tax_id", "currency", "is_active", "is_blocked")
    list_filter = ("gym", "is_active", "is_blocked")
    search_fields = ("name", "tax_id", "email")
    inlines = [ProviderContactInline, ProviderItemInline]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "status", "issue_date", "total", "currency")
    list_filter = ("status", "provider")
    search_fields = ("id", "reference")


admin.site.register(ProviderContact)
admin.site.register(ProviderDocument)
admin.site.register(ProviderRating)
admin.site.register(ProviderItem)
admin.site.register(PurchaseOrderLine)
