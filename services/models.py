from django.db import models
from django.utils.translation import gettext_lazy as _
from organizations.models import Gym
from finance.models import TaxRate
from activities.models import Room

class ServiceCategory(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='service_categories', null=True, blank=True)
    name = models.CharField(_("Nombre"), max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    icon = models.ImageField(upload_to='service_icons/', null=True, blank=True)
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

class Service(models.Model):
    PRICE_STRATEGY = [
        ('TAX_INCLUDED', _("Impuestos Incluidos")),
        ('TAX_EXCLUDED', _("Impuestos Excluidos")),
    ]

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(_("Nombre del Servicio"), max_length=100)
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(_("Descripción"), blank=True)
    image = models.ImageField(upload_to='service_images/', null=True, blank=True)
    color = models.CharField(_("Color en Calendario"), max_length=7, default="#8B5CF6", help_text="Código HEX (ej: #8B5CF6)")
    
    duration = models.PositiveIntegerField(_("Duración (min)"), default=60)
    max_attendees = models.PositiveIntegerField(_("Asistentes Máximos"), default=1)
    
    default_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Pricing
    base_price = models.DecimalField(_("Precio Base"), max_digits=10, decimal_places=2)
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.SET_NULL, null=True, blank=True)
    price_strategy = models.CharField(_("Estrategia de Precio"), max_length=20, choices=PRICE_STRATEGY, default='TAX_INCLUDED')
    
    # Visibility
    is_active = models.BooleanField(_("Activo (Visible en POS)"), default=True, help_text=_("Si se desactiva, no aparecerá en el punto de venta."))
    is_visible_online = models.BooleanField(_("Venta Online (App/Web)"), default=False, help_text=_("Si se activa, los clientes podrán comprarlo desde la App/Web."))

    def __str__(self):
        return self.name
        
    @property
    def final_price(self):
        if not self.tax_rate:
            return self.base_price
            
        rate = self.tax_rate.rate_percent / 100
        if self.price_strategy == 'TAX_EXCLUDED':
            return self.base_price * (1 + rate)
        return self.base_price # Already included

class ServiceAppointment(models.Model):
    """
    1-on-1 Appointment (Booking) for a Service.
    """
    STATUS_CHOICES = [
        ('CONFIRMED', _("Confirmada")),
        ('PENDING', _("Pendiente")),
        ('CANCELLED', _("Cancelada")),
        ('COMPLETED', _("Completada")),
        ('NOSHOW', _("No Show")),
    ]

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='appointments')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='appointments')
    
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='appointments')
    staff = models.ForeignKey('staff.StaffProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    
    start_datetime = models.DateTimeField(_("Inicio"))
    end_datetime = models.DateTimeField(_("Fin"))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CONFIRMED')
    notes = models.TextField(blank=True)
    
    # Financial Link
    order = models.ForeignKey('sales.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointment_link')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_datetime']

    def __str__(self):
        return f"{self.service.name} - {self.client} ({self.start_datetime.strftime('%d/%m %H:%M')})"

