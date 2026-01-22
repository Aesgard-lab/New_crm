from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


class Discount(models.Model):
    """
    Sistema completo de descuentos y promociones
    """
    
    class DiscountType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "Porcentaje (%)"
        FIXED_AMOUNT = "FIXED_AMOUNT", "Cantidad Fija"
        FIXED_PRICE = "FIXED_PRICE", "Precio Fijo"
    
    class AppliesTo(models.TextChoices):
        ALL = "ALL", "Todo"
        MEMBERSHIP = "MEMBERSHIP", "Membresías"
        SERVICE = "SERVICE", "Servicios"
        PRODUCT = "PRODUCT", "Productos"
        SPECIFIC_ITEMS = "SPECIFIC_ITEMS", "Items Específicos"
    
    class TargetType(models.TextChoices):
        ALL = "ALL", "Todos los Clientes"
        NEW_CLIENTS = "NEW_CLIENTS", "Solo Clientes Nuevos"
        INDIVIDUAL = "INDIVIDUAL", "Clientes Individuales"
        GROUP = "GROUP", "Por Grupo"
        TAG = "TAG", "Por Etiqueta"
        FIRST_PURCHASE = "FIRST_PURCHASE", "Primera Compra"
    
    # Información Básica
    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="discounts")
    name = models.CharField(max_length=200, help_text="Nombre interno del descuento")
    description = models.TextField(blank=True, help_text="Descripción visible para clientes")
    
    # Tipo y Valor del Descuento
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE)
    value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Porcentaje (0-100), cantidad fija o precio fijo según el tipo"
    )
    
    # Código Promocional (Opcional)
    code = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Código que los clientes pueden ingresar (ej: VERANO2026)"
    )
    code_case_sensitive = models.BooleanField(default=False)
    
    # Aplicabilidad
    applies_to = models.CharField(max_length=20, choices=AppliesTo.choices, default=AppliesTo.ALL)
    
    # Items específicos (si applies_to = SPECIFIC_ITEMS)
    specific_memberships = models.ManyToManyField("memberships.MembershipPlan", blank=True, related_name="discounts")
    specific_services = models.ManyToManyField("services.Service", blank=True, related_name="discounts")
    specific_products = models.ManyToManyField("products.Product", blank=True, related_name="discounts")
    
    # Restricciones de Compra
    minimum_purchase = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Monto mínimo de compra para aplicar"
    )
    maximum_discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Límite máximo del descuento en dinero (cap)"
    )
    
    # Target / A quién aplica
    target_type = models.CharField(max_length=20, choices=TargetType.choices, default=TargetType.ALL)
    target_clients = models.ManyToManyField("clients.Client", blank=True, related_name="personal_discounts")
    target_groups = models.ManyToManyField("clients.ClientGroup", blank=True, related_name="group_discounts")
    target_tags = models.ManyToManyField("clients.ClientTag", blank=True, related_name="tag_discounts")
    
    # Restricciones de Uso
    max_uses_total = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Número máximo de veces que se puede usar en total"
    )
    max_uses_per_client = models.IntegerField(
        default=1,
        help_text="Número máximo de veces que cada cliente puede usarlo"
    )
    current_uses = models.IntegerField(default=0, help_text="Contador de usos actuales")
    
    # Fechas de Validez
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    
    # Combinabilidad y Prioridad
    stackable = models.BooleanField(
        default=False, 
        help_text="¿Se puede combinar con otros descuentos?"
    )
    priority = models.IntegerField(
        default=0,
        help_text="Mayor número = mayor prioridad (se aplica primero)"
    )
    excludes_discounts = models.ManyToManyField(
        "self", 
        blank=True, 
        symmetrical=False,
        related_name="excluded_by",
        help_text="Descuentos incompatibles con este"
    )
    
    # Estado
    is_active = models.BooleanField(default=True)
    auto_apply = models.BooleanField(
        default=False,
        help_text="Aplicar automáticamente si el cliente cumple condiciones"
    )
    
    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name="created_discounts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['gym', 'is_active']),
            models.Index(fields=['code']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_display_value()}"
    
    def get_display_value(self):
        """Retorna el valor del descuento formateado"""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return f"{self.value}%"
        elif self.discount_type == self.DiscountType.FIXED_AMOUNT:
            return f"${self.value}"
        else:  # FIXED_PRICE
            return f"Precio: ${self.value}"
    
    def is_valid_now(self):
        """Verifica si el descuento es válido en este momento"""
        now = timezone.now()
        
        if not self.is_active:
            return False
        
        if self.valid_from and now < self.valid_from:
            return False
        
        if self.valid_until and now > self.valid_until:
            return False
        
        if self.max_uses_total and self.current_uses >= self.max_uses_total:
            return False
        
        return True
    
    def can_be_used_by_client(self, client):
        """Verifica si un cliente específico puede usar este descuento"""
        if not self.is_valid_now():
            return False
        
        # Verificar target type
        if self.target_type == self.TargetType.INDIVIDUAL:
            if not self.target_clients.filter(id=client.id).exists():
                return False
        
        elif self.target_type == self.TargetType.GROUP:
            if not self.target_groups.filter(clients=client).exists():
                return False
        
        elif self.target_type == self.TargetType.TAG:
            if not self.target_tags.filter(clients=client).exists():
                return False
        
        elif self.target_type == self.TargetType.NEW_CLIENTS:
            # Verificar si es cliente nuevo (nunca ha tenido membresía)
            from clients.models import ClientMembership
            if ClientMembership.objects.filter(client=client).exists():
                return False
        
        # Verificar usos por cliente
        uses_by_client = DiscountUsage.objects.filter(
            discount=self,
            client=client
        ).count()
        
        if uses_by_client >= self.max_uses_per_client:
            return False
        
        return True
    
    def calculate_discount_amount(self, subtotal):
        """Calcula el monto del descuento dado un subtotal"""
        if subtotal < self.minimum_purchase:
            return Decimal('0.00')
        
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = subtotal * (self.value / Decimal('100'))
        elif self.discount_type == self.DiscountType.FIXED_AMOUNT:
            discount = self.value
        else:  # FIXED_PRICE
            discount = subtotal - self.value
            if discount < 0:
                discount = Decimal('0.00')
        
        # Aplicar cap si existe
        if self.maximum_discount_amount and discount > self.maximum_discount_amount:
            discount = self.maximum_discount_amount
        
        # No puede ser negativo ni mayor al subtotal
        discount = max(Decimal('0.00'), min(discount, subtotal))
        
        return discount.quantize(Decimal('0.01'))
    
    def increment_usage(self):
        """Incrementa el contador de usos"""
        self.current_uses += 1
        self.save(update_fields=['current_uses'])


class DiscountUsage(models.Model):
    """
    Registro de uso de descuentos para tracking y analytics
    """
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name="usages")
    client = models.ForeignKey("clients.Client", on_delete=models.CASCADE, related_name="discount_usages")
    order = models.ForeignKey("sales.Order", on_delete=models.CASCADE, related_name="discount_usages", null=True, blank=True)
    
    # Datos del descuento en el momento del uso
    discount_name = models.CharField(max_length=200)
    discount_type = models.CharField(max_length=20)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Montos
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Metadata
    code_used = models.CharField(max_length=50, blank=True, null=True)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_discounts",
        help_text="Staff que aplicó el descuento"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['discount', 'client']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.discount_name} - {self.client} - ${self.discount_amount}"
    
    def savings_percentage(self):
        """Calcula el porcentaje de ahorro"""
        if self.subtotal > 0:
            return (self.discount_amount / self.subtotal * 100).quantize(Decimal('0.1'))
        return Decimal('0.0')


class ReferralProgram(models.Model):
    """
    Programa de referidos - el cliente refiere a otros y ambos ganan
    """
    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="referral_programs")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Recompensas
    referrer_discount = models.ForeignKey(
        Discount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrer_programs",
        help_text="Descuento para quien refiere"
    )
    referrer_credit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Crédito en cuenta para quien refiere"
    )
    
    referred_discount = models.ForeignKey(
        Discount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referred_programs",
        help_text="Descuento para el referido"
    )
    
    # Condiciones
    min_referrals_for_bonus = models.IntegerField(
        default=3,
        help_text="Mínimo de referidos para obtener bonus adicional"
    )
    bonus_discount = models.ForeignKey(
        Discount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bonus_programs",
        help_text="Bonus al alcanzar el mínimo de referidos"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class Referral(models.Model):
    """
    Registro individual de un referido
    """
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        COMPLETED = "COMPLETED", "Completado"
        REWARDED = "REWARDED", "Recompensado"
    
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE, related_name="referrals")
    referrer = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="referrals_made",
        help_text="Cliente que refirió"
    )
    referred = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="referred_by",
        help_text="Cliente referido"
    )
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Tracking
    referral_code = models.CharField(max_length=50, unique=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rewarded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('referrer', 'referred')
    
    def __str__(self):
        return f"{self.referrer} → {self.referred} ({self.status})"
