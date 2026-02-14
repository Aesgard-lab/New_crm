from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from organizations.models import Gym
from finance.models import CashSession, PaymentMethod
from clients.models import Client
import uuid

class Order(models.Model):
    STATS_CHOICES = (
        ('PENDING', _('Pendiente')),
        ('PAID', _('Pagado')),
        ('CANCELLED', _('Cancelado')),
        ('DEFERRED', _('Diferido')),
    )
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='orders')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Financial linkage
    session = models.ForeignKey(CashSession, on_delete=models.PROTECT, null=True, blank=True, related_name='orders',
        help_text=_("Sesión de caja donde se registró esta venta"))
    
    created_at = models.DateTimeField(_("Fecha Creación"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Última Actualización"), auto_now=True)
    
    status = models.CharField(_("Estado"), max_length=20, choices=STATS_CHOICES, default='PENDING', db_index=True)
    
    # Totals (Denormalized for easy querying)
    total_base = models.DecimalField(_("Total Base"), max_digits=10, decimal_places=2, default=0.00)
    total_tax = models.DecimalField(_("Total Impuestos"), max_digits=10, decimal_places=2, default=0.00)
    total_discount = models.DecimalField(_("Total Descuento"), max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(_("Total Venta"), max_digits=10, decimal_places=2, default=0.00)
    total_refunded = models.DecimalField(_("Total Devuelto"), max_digits=10, decimal_places=2, default=0.00)
    
    # Deferred Payment Fields (Cobro Diferido)
    scheduled_payment_date = models.DateField(_("Fecha Pago Programado"), null=True, blank=True,
        help_text=_("Fecha en que se debe cobrar esta venta diferida"))
    auto_charge = models.BooleanField(_("Cobro Automático"), default=False,
        help_text=_("Si está activo, se intentará cobrar automáticamente en la fecha programada"))
    deferred_notes = models.TextField(_("Notas del Diferido"), blank=True,
        help_text=_("Razón o comentarios sobre por qué se difirió el pago"))
    
    internal_notes = models.TextField(_("Nota Interna"), blank=True)
    invoice_number = models.CharField(_("Número de Factura"), max_length=50, blank=True, null=True, unique=True, db_index=True)
    verification_token = models.UUIDField(
        _("Token de Verificación"),
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        help_text=_("Identificador único para el QR de verificación del recibo/factura")
    )
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_orders')

    class Meta:
        verbose_name = _("Venta / Ticket")
        verbose_name_plural = _("Ventas")
        ordering = ['-created_at']

    def __str__(self):
        return f"Ticket #{self.pk} - {self.total_amount}€"
    
    @property
    def refundable_amount(self):
        """Cantidad máxima que se puede devolver (total - ya devuelto)."""
        return max(self.total_amount - self.total_refunded, 0)
    
    @property
    def is_fully_refunded(self):
        """Si la orden está completamente devuelta."""
        return self.total_refunded >= self.total_amount
    
    @property
    def has_partial_refund(self):
        """Si la orden tiene alguna devolución parcial."""
        return self.total_refunded > 0 and self.total_refunded < self.total_amount
    
    def update_refund_total(self):
        """Recalcula el total devuelto desde las devoluciones completadas."""
        from django.db.models import Sum
        total = self.refunds.filter(status='COMPLETED').aggregate(
            total=Sum('amount')
        )['total'] or 0
        self.total_refunded = total
        self.save(update_fields=['total_refunded'])
    
    def get_verification_path(self):
        """Ruta relativa de verificación del documento."""
        return f"/sales/verify/{self.verification_token}/"
    
    def get_qr_image_url(self, base_url=''):
        """
        URL de la imagen QR generada por quickchart.io (funciona en emails HTML).
        base_url: dominio completo, ej: https://app.tudominio.com
        """
        import urllib.parse
        verify_url = f"{base_url}{self.get_verification_path()}"
        encoded = urllib.parse.quote_plus(verify_url)
        return f"https://quickchart.io/qr?text={encoded}&size=200&margin=1"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    
    # Polymorphic Relation
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    description = models.CharField(_("Descripción"), max_length=255)
    quantity = models.PositiveIntegerField(_("Cantidad"), default=1)
    notes = models.TextField(
        _("Notas del Recibo"),
        blank=True,
        help_text=_("Notas que aparecen en el ticket/factura para este artículo")
    )
    
    unit_price = models.DecimalField(_("Precio Unitario"), max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(_("Impuesto (%)"), max_digits=5, decimal_places=2, default=0.00)
    
    discount_amount = models.DecimalField(_("Descuento (€)"), max_digits=10, decimal_places=2, default=0.00)
    
    subtotal = models.DecimalField(_("Subtotal"), max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity}x {self.description}"

class OrderPayment(models.Model):
    GATEWAY_CHOICES = [
        ('NONE', _('Sin pasarela (Manual/Efectivo)')),
        ('STRIPE', _('Stripe')),
        ('REDSYS', _('Redsys')),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    amount = models.DecimalField(_("Cantidad"), max_digits=10, decimal_places=2)
    transaction_id = models.CharField(_("ID Transacción"), max_length=255, blank=True, null=True)
    gateway_used = models.CharField(_("Pasarela Usada"), max_length=20, choices=GATEWAY_CHOICES, default='NONE')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_method.name}: {self.amount}€"
    
    @property
    def refundable_amount(self):
        """Cantidad que aún se puede devolver de este pago."""
        refunded = self.refunds.filter(status='COMPLETED').aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        return max(self.amount - refunded, 0)


class OrderRefund(models.Model):
    """Modelo para trackear devoluciones parciales o totales."""
    
    STATUS_CHOICES = [
        ('PENDING', _('Pendiente')),
        ('COMPLETED', _('Completado')),
        ('FAILED', _('Fallido')),
    ]
    
    GATEWAY_CHOICES = [
        ('NONE', _('Manual')),
        ('STRIPE', _('Stripe')),
        ('REDSYS', _('Redsys')),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    payment = models.ForeignKey(
        OrderPayment, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='refunds',
        help_text=_("Pago específico que se devuelve (si aplica)")
    )
    
    amount = models.DecimalField(_("Cantidad Devuelta"), max_digits=10, decimal_places=2)
    reason = models.CharField(_("Motivo"), max_length=255, blank=True)
    notes = models.TextField(_("Notas internas"), blank=True)
    refund_method_name = models.CharField(_("Método de Devolución"), max_length=100, blank=True,
        help_text=_("Nombre del método usado para la devolución (manual)"))
    
    status = models.CharField(_("Estado"), max_length=20, choices=STATUS_CHOICES, default='PENDING')
    gateway = models.CharField(_("Pasarela"), max_length=20, choices=GATEWAY_CHOICES, default='NONE')
    gateway_refund_id = models.CharField(_("ID Reembolso Pasarela"), max_length=255, blank=True, null=True)
    error_message = models.TextField(_("Mensaje de Error"), blank=True)
    
    # Orden negativa creada para contabilidad (si accounting_mode='negative')
    negative_order = models.ForeignKey(
        'Order', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='refund_source', help_text=_("Orden con importe negativo creada para esta devolución")
    )
    
    created_at = models.DateTimeField(_("Fecha"), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, 
        related_name='created_refunds'
    )
    
    class Meta:
        verbose_name = _("Devolución")
        verbose_name_plural = _("Devoluciones")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Devolución #{self.pk} - {self.amount}€ ({self.get_status_display()})"
