from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import ProductCategory, Product, StockMove


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
	list_display = ("name", "code", "gym", "parent")
	list_filter = ("gym",)
	search_fields = ("name", "code")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"display_barcode",
		"sku",
		"gym",
		"category",
		"base_price",
		"stock_quantity",
		"is_active",
		"is_visible_online",
	)
	list_filter = (
		"gym",
		"category",
		"barcode_type",
		"price_strategy",
		"track_stock",
		"is_active",
		"is_visible_online",
	)
	search_fields = (
		"name",
		"barcode",
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
	readonly_fields = ("created_at", "updated_at", "display_code")
	fieldsets = (
		(_("Datos básicos"), {"fields": ("gym", "name", "category", "description", "image")}),
		(
			_("Códigos de Barras y SKU"),
			{
				"fields": (
					"barcode",
					"barcode_type",
					"sku",
					"display_code",
				),
				"description": _("El código de barras es el EAN del fabricante. El SKU es el código interno del gimnasio (auto-generado si se deja vacío).")
			},
		),
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
	
	@admin.display(description=_("Código de Barras"))
	def display_barcode(self, obj):
		if obj.barcode:
			return format_html(
				'<code style="font-family: monospace; background: #f3f4f6; padding: 2px 6px; border-radius: 4px;">{}</code> <small style="color: #6b7280;">({})</small>',
				obj.barcode,
				obj.get_barcode_type_display()
			)
		return "-"


@admin.register(StockMove)
class StockMoveAdmin(admin.ModelAdmin):
	list_display = ("product", "quantity_change", "reason", "created_by", "created_at")
	list_filter = ("reason",)
	search_fields = ("product__name", "notes")
	raw_id_fields = ("product", "created_by")
