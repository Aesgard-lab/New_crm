from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import ProductCategory, Product, StockMove


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
	list_display = ("name", "gym", "parent")
	list_filter = ("gym",)
	search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"gym",
		"category",
		"preferred_provider",
		"preferred_provider_item",
		"is_active",
		"is_visible_online",
	)
	list_filter = (
		"gym",
		"category",
		"price_strategy",
		"track_stock",
		"is_active",
		"is_visible_online",
	)
	search_fields = (
		"name",
		"sku",
		"supplier_name",
		"supplier_reference",
		"preferred_provider__name",
		"preferred_provider_item__sku_provider",
	)
	raw_id_fields = (
		"gym",
		"category",
		"tax_rate",
		"preferred_provider",
		"preferred_provider_item",
	)
	readonly_fields = ("created_at", "updated_at")
	fieldsets = (
		(_("Datos básicos"), {"fields": ("gym", "name", "category", "description", "image", "sku")}),
		(
			_("Precios"),
			{
				"fields": (
					"cost_price",
					"base_price",
					"tax_rate",
					"price_strategy",
				)
			},
		),
		(
			_("Proveedor"),
			{
				"fields": (
					"supplier_name",
					"supplier_reference",
					"preferred_provider",
					"preferred_provider_item",
				)
			},
		),
		(
			_("Inventario"),
			{"fields": ("track_stock", "stock_quantity", "low_stock_threshold")},
		),
		(
			_("Visibilidad"),
			{"fields": ("is_active", "is_visible_online")},
		),
		(
			_("Trazabilidad"),
			{"fields": ("created_at", "updated_at")},
		),
	)


@admin.register(StockMove)
class StockMoveAdmin(admin.ModelAdmin):
	list_display = ("product", "quantity_change", "reason", "created_by", "created_at")
	list_filter = ("reason",)
	search_fields = ("product__name", "notes")
	raw_id_fields = ("product", "created_by")
