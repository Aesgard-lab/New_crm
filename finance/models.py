from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from organizations.models import Gym

class TaxRate(models.Model):
    """
    Centralized tax rates (optional usage for now, ensuring future compatibility).
    """
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='tax_rates', default=1)
    name = models.CharField(_("Nombre del Impuesto"), max_length=50, help_text=_("Ej: IVA 21%"))
    rate_percent = models.DecimalField(_("Porcentaje"), max_digits=5, decimal_places=2, help_text=_("Ej: 21.00"))
    is_active = models.BooleanField(_("Activo"), default=True)

    def __str__(self):
        return f"{self.name} ({self.rate_percent}%)"

    class Meta:
        verbose_name = _("Impuesto")
        verbose_name_plural = _("Impuestos")

class PaymentMethod(models.Model):
    """
    Configurable payment methods (Cash, Card, Transfer, Stripe, etc.)
    """
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='payment_methods', default=1)
    name = models.CharField(_("Nombre"), max_length=50) # Efectivo, Tarjeta, Bizum...
    is_cash = models.BooleanField(_("Control de Caja"), default=False, 
        help_text=_("Si se marca, este método requiere una Sesión de Caja abierta y suma al efectivo físico."))
    is_active = models.BooleanField(_("Activo"), default=True)
    
    # For future integrations:
    provider_code = models.CharField(_("Código Proveedor"), max_length=50, blank=True, null=True,
        help_text=_("ej: 'stripe_terminal', 'redsys', etc."))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Método de Pago")
        verbose_name_plural = _("Métodos de Pago")

class CashSession(models.Model):
    """
    Represents a Shift or Day of 'Cash Drawer' (Arqueo).
    """
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='cash_sessions', default=1)
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='opened_sessions')
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='closed_sessions', null=True, blank=True)
    
    opened_at = models.DateTimeField(_("Apertura"), auto_now_add=True)
    closed_at = models.DateTimeField(_("Cierre"), null=True, blank=True)
    
    opening_balance = models.DecimalField(_("Fondo Inicial"), max_digits=10, decimal_places=2, default=0.00)
    
    # Financials at close
    total_cash_sales = models.DecimalField(_("Ventas Efectivo Sistema"), max_digits=10, decimal_places=2, default=0.00, help_text=_("Calculado automáticamente"))
    total_cash_withdrawals = models.DecimalField(_("Retiradas"), max_digits=10, decimal_places=2, default=0.00)
    total_cash_additions = models.DecimalField(_("Ingresos Extra"), max_digits=10, decimal_places=2, default=0.00)
    
    expected_balance = models.DecimalField(_("Esperado en Caja"), max_digits=10, decimal_places=2, default=0.00)
    actual_balance = models.DecimalField(_("Contado Real (Arqueo)"), max_digits=10, decimal_places=2, null=True, blank=True)
    discrepancy = models.DecimalField(_("Descuadre"), max_digits=10, decimal_places=2, null=True, blank=True)
    
    notes = models.TextField(_("Notas de Cierre"), blank=True)
    is_closed = models.BooleanField(_("Cerrada"), default=False)

    class Meta:
        verbose_name = _("Sesión de Caja")
        verbose_name_plural = _("Sesiones de Caja")
        ordering = ['-opened_at']

    def calculate_expected(self):
        """Helper to update expected balance"""
        self.expected_balance = self.opening_balance + self.total_cash_sales + self.total_cash_additions - self.total_cash_withdrawals

    def save(self, *args, **kwargs):
        self.calculate_expected()
        if self.actual_balance is not None:
            self.discrepancy = self.actual_balance - self.expected_balance
        super().save(*args, **kwargs)

class FinanceSettings(models.Model):
    """
    Singleton-like Settings for Finance per Gym (Stripe, Currency, etc.)
    """
    gym = models.OneToOneField(Gym, on_delete=models.CASCADE, related_name='finance_settings')
    
    # Stripe Configuration
    stripe_public_key = models.CharField(_("Stripe Public Key"), max_length=255, blank=True)
    stripe_secret_key = models.CharField(_("Stripe Secret Key"), max_length=255, blank=True)
    
    # Redsys
    redsys_merchant_code = models.CharField(_("FUC (Código de Comercio)"), max_length=255, blank=True)
    redsys_merchant_terminal = models.CharField(_("Terminal"), max_length=10, default="001", blank=True)
    redsys_secret_key = models.CharField(_("Clave Secreta (clave256)"), max_length=255, blank=True)
    redsys_environment = models.CharField(_("Entorno"), max_length=10, choices=[('TEST', 'Pruebas / Sandbox'), ('REAL', 'Producción / Real')], default='TEST') # TEST (sis-t) or REAL (sis)
    
    # Currency
    currency = models.CharField(_("Moneda Principal"), max_length=3, default='EUR', help_text=_("Ej: EUR, USD"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Configuración Financiera")
        verbose_name_plural = _("Configuraciones Financieras")

    def __str__(self):
        return f"Configuración Financiera de {self.gym.name}"

class ClientRedsysToken(models.Model):
    """
    Stores Redsys 'Reference' (Order ID of the initial auth) for recurring payments (Pago por Referencia).
    """
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='redsys_tokens')
    token = models.CharField(_("Token / Referencia"), max_length=100, help_text="Suele ser el Ds_Order de la primera operación")
    card_brand = models.CharField(_("Marca"), max_length=50, blank=True) # VISA, MASTERCARD
    card_number = models.CharField(_("Número Enmascarado"), max_length=20, blank=True) # **** **** **** 1234
    expiration = models.CharField(_("Caducidad"), max_length=10, blank=True) # YYMM
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.card_brand} {self.card_number} ({self.client})"

    class Meta:
        verbose_name = _("Token Redsys Cliente")
        verbose_name_plural = _("Tokens Redsys Cliente")
