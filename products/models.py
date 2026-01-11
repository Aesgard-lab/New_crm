from django.db import models
from django.utils.translation import gettext_lazy as _
from organizations.models import Gym
from finance.models import TaxRate
from accounts.models import User

class ProductCategory(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='product_categories')
    name = models.CharField(_("Nombre"), max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    icon = models.ImageField(upload_to='product_icons/', null=True, blank=True)
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

class Product(models.Model):
    PRICE_STRATEGY = [
        ('TAX_INCLUDED', _("Impuestos Incluidos")),
        ('TAX_EXCLUDED', _("Impuestos Excluidos")),
    ]

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(_("Nombre del Producto"), max_length=100)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(_("Descripción"), blank=True)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    sku = models.CharField(_("SKU / Código de Barras"), max_length=50, blank=True)
    
    # Financials
    cost_price = models.DecimalField(_("Precio de Compra (Sin IVA)"), max_digits=10, decimal_places=2, default=0)
    base_price = models.DecimalField(_("Precio de Venta"), max_digits=10, decimal_places=2)
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.SET_NULL, null=True, blank=True)
    price_strategy = models.CharField(_("Estrategia de Precio"), max_length=20, choices=PRICE_STRATEGY, default='TAX_INCLUDED')
    
    # Supplier Info
    supplier_name = models.CharField(_("Proveedor"), max_length=100, blank=True)
    supplier_reference = models.CharField(_("Ref. Proveedor"), max_length=100, blank=True)
    
    # Inventory
    track_stock = models.BooleanField(_("Controlar Stock"), default=True)
    stock_quantity = models.IntegerField(_("Stock Actual"), default=0)
    low_stock_threshold = models.IntegerField(_("Alerta Stock Bajo"), default=5)
    
    # Visibility
    is_active = models.BooleanField(_("Activo (POS)"), default=True)
    is_visible_online = models.BooleanField(_("Venta Online"), default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    @property
    def final_price(self):
        if not self.tax_rate:
            return self.base_price
        rate = self.tax_rate.rate_percent / 100
        if self.price_strategy == 'TAX_EXCLUDED':
            return self.base_price * (1 + rate)
        return self.base_price

class StockMove(models.Model):
    REASONS = [
        ('SALE', _("Venta")),
        ('RESTOCK', _("Reabastecimiento")),
        ('ADJUSTMENT', _("Ajuste Manual")),
        ('LOSS', _("Pérdida/Daño")),
        ('RETURN', _("Devolución")),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_moves')
    quantity_change = models.IntegerField(_("Cambio (+/-)"))
    reason = models.CharField(max_length=20, choices=REASONS)
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Update product stock on save
        if not self.pk: # Only on creation
            self.product.stock_quantity += self.quantity_change
            self.product.save()
        super().save(*args, **kwargs)
