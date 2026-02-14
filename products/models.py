from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from organizations.models import Gym
from finance.models import TaxRate
from accounts.models import User
import re


# ============================================
# BARCODE UTILITIES
# ============================================

def validate_ean13(code: str) -> bool:
    """
    Valida que un código sea un EAN-13 válido (incluyendo dígito de control).
    """
    if not code or len(code) != 13 or not code.isdigit():
        return False
    
    # Calcular dígito de control
    total = 0
    for i, digit in enumerate(code[:12]):
        if i % 2 == 0:
            total += int(digit)
        else:
            total += int(digit) * 3
    
    check_digit = (10 - (total % 10)) % 10
    return int(code[12]) == check_digit


def validate_ean8(code: str) -> bool:
    """
    Valida que un código sea un EAN-8 válido.
    """
    if not code or len(code) != 8 or not code.isdigit():
        return False
    
    total = 0
    for i, digit in enumerate(code[:7]):
        if i % 2 == 0:
            total += int(digit) * 3
        else:
            total += int(digit)
    
    check_digit = (10 - (total % 10)) % 10
    return int(code[7]) == check_digit


def calculate_ean13_check_digit(code_12: str) -> str:
    """
    Calcula el dígito de control para un código EAN-13 (12 dígitos sin el check).
    Retorna el código completo de 13 dígitos.
    """
    if len(code_12) != 12 or not code_12.isdigit():
        raise ValueError("El código debe tener exactamente 12 dígitos")
    
    total = 0
    for i, digit in enumerate(code_12):
        if i % 2 == 0:
            total += int(digit)
        else:
            total += int(digit) * 3
    
    check_digit = (10 - (total % 10)) % 10
    return code_12 + str(check_digit)


def detect_barcode_type(code: str) -> str:
    """
    Detecta automáticamente el tipo de código de barras.
    """
    if not code:
        return 'UNKNOWN'
    
    code = code.strip()
    
    # EAN-13
    if len(code) == 13 and code.isdigit():
        if validate_ean13(code):
            return 'EAN13'
        return 'INVALID_EAN13'
    
    # EAN-8
    if len(code) == 8 and code.isdigit():
        if validate_ean8(code):
            return 'EAN8'
        return 'INVALID_EAN8'
    
    # UPC-A (12 dígitos, común en USA)
    if len(code) == 12 and code.isdigit():
        return 'UPCA'
    
    # Code 128 / Internal (alfanumérico)
    if re.match(r'^[A-Za-z0-9\-_]+$', code):
        return 'CODE128'
    
    return 'UNKNOWN'


def generate_internal_sku(gym, category=None, prefix=None):
    """
    Genera un SKU interno único para el gimnasio.
    Formato: [PREFIX]-[CAT]-[SECUENCIAL]
    Ejemplo: GYM01-BEB-0001
    """
    from products.models import Product
    
    # Determinar prefijo
    if prefix:
        sku_prefix = prefix.upper()[:6]
    else:
        # Usar código del gym o primeras letras del nombre
        sku_prefix = f"G{gym.pk:03d}"
    
    # Determinar código de categoría
    if category:
        cat_code = ''.join(word[0] for word in category.name.split()[:2]).upper()[:3]
        if len(cat_code) < 2:
            cat_code = category.name[:3].upper()
    else:
        cat_code = "GEN"
    
    # Buscar el siguiente número secuencial para este prefijo+categoría
    base_pattern = f"{sku_prefix}-{cat_code}-"
    existing = Product.objects.filter(
        gym=gym,
        sku__startswith=base_pattern
    ).values_list('sku', flat=True)
    
    # Extraer números existentes
    max_num = 0
    for sku in existing:
        try:
            num_part = sku.replace(base_pattern, '')
            num = int(num_part)
            if num > max_num:
                max_num = num
        except (ValueError, IndexError):
            continue
    
    next_num = max_num + 1
    return f"{base_pattern}{next_num:04d}"


class ProductCategory(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='product_categories')
    name = models.CharField(_("Nombre"), max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    icon = models.ImageField(upload_to='product_icons/', null=True, blank=True)
    
    # Código corto para generación de SKUs (ej: BEB para Bebidas)
    code = models.CharField(_("Código Categoría"), max_length=5, blank=True,
        help_text=_("Código corto para SKUs automáticos (ej: BEB, SUP, ROA)"))
    
    class Meta:
        verbose_name = _("Categoría de Producto")
        verbose_name_plural = _("Categorías de Productos")
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        # Auto-generar código si no existe
        if not self.code:
            self.code = ''.join(word[0] for word in self.name.split()[:3]).upper()[:5]
        super().save(*args, **kwargs)


class Product(models.Model):
    PRICE_STRATEGY = [
        ('TAX_INCLUDED', _("Impuestos Incluidos")),
        ('TAX_EXCLUDED', _("Impuestos Excluidos")),
    ]
    
    BARCODE_TYPE_CHOICES = [
        ('EAN13', _('EAN-13 (Estándar)')),
        ('EAN8', _('EAN-8 (Compacto)')),
        ('UPCA', _('UPC-A (USA)')),
        ('CODE128', _('Code 128 (Interno)')),
        ('INTERNAL', _('SKU Interno')),
        ('NONE', _('Sin código')),
    ]

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(_("Nombre del Producto"), max_length=100)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(_("Descripción"), blank=True)
    receipt_notes = models.TextField(
        _("Notas del Recibo"),
        blank=True,
        help_text=_("Texto que aparecerá en el ticket/factura cuando se venda este producto")
    )
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    
    # === CÓDIGOS DE BARRAS Y SKU ===
    barcode = models.CharField(_("Código de Barras"), max_length=50, blank=True, db_index=True,
        help_text=_("EAN-13/EAN-8 del fabricante o código escaneado"))
    barcode_type = models.CharField(_("Tipo de Código"), max_length=10, 
        choices=BARCODE_TYPE_CHOICES, default='NONE')
    sku = models.CharField(_("SKU Interno"), max_length=30, blank=True, db_index=True,
        help_text=_("Código interno del gimnasio (auto-generado si se deja vacío)"))
    
    # Financials
    cost_price = models.DecimalField(_("Precio de Compra (Sin IVA)"), max_digits=10, decimal_places=2, default=0)
    base_price = models.DecimalField(_("Precio de Venta"), max_digits=10, decimal_places=2)
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Impuesto Principal"), related_name='products_primary')
    additional_tax_rates = models.ManyToManyField(
        TaxRate, blank=True,
        verbose_name=_("Impuestos Adicionales"),
        related_name='products_additional',
        help_text=_("Impuestos adicionales que se aplican junto al principal")
    )
    price_strategy = models.CharField(_("Estrategia de Precio"), max_length=20, choices=PRICE_STRATEGY, default='TAX_INCLUDED')
    
    # Supplier Info
    supplier_name = models.CharField(_("Proveedor"), max_length=100, blank=True)
    supplier_reference = models.CharField(_("Ref. Proveedor"), max_length=100, blank=True)
    preferred_provider = models.ForeignKey(
        "providers.Provider",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_products",
        verbose_name=_("Proveedor preferente"),
    )
    preferred_provider_item = models.ForeignKey(
        "providers.ProviderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_products",
        verbose_name=_("Artículo proveedor preferente"),
    )
    
    # Inventory
    track_stock = models.BooleanField(_("Controlar Stock"), default=True)
    stock_quantity = models.IntegerField(_("Stock Actual"), default=0)
    low_stock_threshold = models.IntegerField(_("Alerta Stock Bajo"), default=5)
    
    # Visibility
    is_active = models.BooleanField(_("Activo (POS)"), default=True)
    is_visible_online = models.BooleanField(_("Venta Online"), default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Producto")
        verbose_name_plural = _("Productos")
        constraints = [
            # Código de barras único por gimnasio (si no está vacío)
            models.UniqueConstraint(
                fields=['gym', 'barcode'],
                name='unique_barcode_per_gym',
                condition=models.Q(barcode__gt='')
            ),
            # SKU único por gimnasio (si no está vacío)
            models.UniqueConstraint(
                fields=['gym', 'sku'],
                name='unique_sku_per_gym',
                condition=models.Q(sku__gt='')
            ),
        ]
        indexes = [
            models.Index(fields=['gym', 'barcode']),
            models.Index(fields=['gym', 'sku']),
            models.Index(fields=['gym', 'is_active']),
        ]

    def __str__(self):
        return self.name
    
    def clean(self):
        """Validar códigos de barras."""
        super().clean()
        
        if self.barcode:
            # Detectar tipo automáticamente si no está definido
            detected_type = detect_barcode_type(self.barcode)
            
            if detected_type.startswith('INVALID'):
                raise ValidationError({
                    'barcode': _('El código de barras no es válido. Verifique el dígito de control.')
                })
            
            # Asignar tipo detectado si es NONE
            if self.barcode_type == 'NONE':
                self.barcode_type = detected_type if detected_type != 'UNKNOWN' else 'CODE128'
    
    def save(self, *args, **kwargs):
        # Limpiar espacios
        if self.barcode:
            self.barcode = self.barcode.strip()
        if self.sku:
            self.sku = self.sku.strip().upper()
        
        # Auto-detectar tipo de código de barras
        if self.barcode and self.barcode_type == 'NONE':
            detected = detect_barcode_type(self.barcode)
            if detected not in ('UNKNOWN', 'INVALID_EAN13', 'INVALID_EAN8'):
                self.barcode_type = detected
        
        # Auto-generar SKU si no existe y hay categoría
        if not self.sku and self.pk is None:  # Solo en creación
            self.sku = generate_internal_sku(self.gym, self.category)
        
        super().save(*args, **kwargs)
    
    @property
    def total_tax_rate_percent(self):
        """Suma de todos los impuestos (principal + adicionales) en porcentaje."""
        total = self.tax_rate.rate_percent if self.tax_rate else 0
        for tr in self.additional_tax_rates.all():
            total += tr.rate_percent
        return total
    
    @property
    def final_price(self):
        rate = self.total_tax_rate_percent / 100
        if rate == 0:
            return self.base_price
        if self.price_strategy == 'TAX_EXCLUDED':
            return self.base_price * (1 + rate)
        return self.base_price
    
    @property
    def display_code(self):
        """Retorna el código principal para mostrar (barcode o SKU)."""
        return self.barcode or self.sku or f"P{self.pk:05d}"
    
    @property
    def has_valid_barcode(self):
        """Indica si tiene un código de barras válido para escaneo."""
        return bool(self.barcode) and self.barcode_type in ('EAN13', 'EAN8', 'UPCA', 'CODE128')
    
    @classmethod
    def find_by_code(cls, gym, code):
        """
        Busca un producto por código de barras o SKU.
        Útil para escaneo rápido en POS.
        """
        code = code.strip()
        
        # Primero buscar por barcode exacto
        product = cls.objects.filter(gym=gym, barcode=code, is_active=True).first()
        if product:
            return product
        
        # Luego por SKU
        product = cls.objects.filter(gym=gym, sku__iexact=code, is_active=True).first()
        if product:
            return product
        
        return None

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
