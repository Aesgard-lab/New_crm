from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from organizations.models import Gym
from finance.models import CashSession, PaymentMethod
from clients.models import Client

class Order(models.Model):
    STATS_CHOICES = (
        ('PENDING', _('Pendiente')),
        ('PAID', _('Pagado')),
        ('CANCELLED', _('Cancelado')),
    )
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='orders')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Financial linkage
    session = models.ForeignKey(CashSession, on_delete=models.PROTECT, null=True, blank=True, related_name='orders',
        help_text=_("Sesión de caja donde se registró esta venta"))
    
    created_at = models.DateTimeField(_("Fecha Creación"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Última Actualización"), auto_now=True)
    
    status = models.CharField(_("Estado"), max_length=20, choices=STATS_CHOICES, default='PENDING')
    
    # Totals (Denormalized for easy querying)
    total_base = models.DecimalField(_("Total Base"), max_digits=10, decimal_places=2, default=0.00)
    total_tax = models.DecimalField(_("Total Impuestos"), max_digits=10, decimal_places=2, default=0.00)
    total_discount = models.DecimalField(_("Total Descuento"), max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(_("Total Venta"), max_digits=10, decimal_places=2, default=0.00)
    
    internal_notes = models.TextField(_("Nota Interna"), blank=True)
    invoice_number = models.CharField(_("Número de Factura"), max_length=50, blank=True, null=True, unique=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_orders')

    class Meta:
        verbose_name = _("Venta / Ticket")
        verbose_name_plural = _("Ventas")
        ordering = ['-created_at']

    def __str__(self):
        return f"Ticket #{self.pk} - {self.total_amount}€"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    
    # Polymorphic Relation
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    description = models.CharField(_("Descripción"), max_length=255)
    quantity = models.PositiveIntegerField(_("Cantidad"), default=1)
    
    unit_price = models.DecimalField(_("Precio Unitario"), max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(_("Impuesto (%)"), max_digits=5, decimal_places=2, default=0.00)
    
    discount_amount = models.DecimalField(_("Descuento (€)"), max_digits=10, decimal_places=2, default=0.00)
    
    subtotal = models.DecimalField(_("Subtotal"), max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity}x {self.description}"

class OrderPayment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    amount = models.DecimalField(_("Cantidad"), max_digits=10, decimal_places=2)
    transaction_id = models.CharField(_("ID Transacción (Stripe)"), max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_method.name}: {self.amount}€"
