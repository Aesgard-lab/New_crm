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

    # === OFERTAS PARA NUEVOS CLIENTES ===
    NEW_CLIENT_CRITERIA = [
        ('NEVER_HAD_MEMBERSHIP', _("Nunca ha tenido una membresía")),
        ('REGISTERED_RECENTLY', _("Registrado recientemente")),
        ('NEVER_BOUGHT_THIS', _("Nunca ha comprado este servicio")),
        ('INACTIVE_PERIOD', _("Sin actividad en X meses (re-captación)")),
    ]
    
    is_new_client_only = models.BooleanField(
        _("Solo para Nuevos Clientes"),
        default=False,
        help_text=_("Si se activa, solo los clientes que cumplan el criterio podrán ver/comprar este servicio")
    )
    new_client_criteria = models.CharField(
        _("Criterio de Cliente Nuevo"),
        max_length=30,
        choices=NEW_CLIENT_CRITERIA,
        default='NEVER_HAD_MEMBERSHIP',
        help_text=_("Define qué se considera 'cliente nuevo' para esta oferta")
    )
    new_client_days_threshold = models.PositiveIntegerField(
        _("Umbral de Días"),
        default=30,
        help_text=_("Para 'Registrado recientemente': días desde registro. Para 'Sin actividad': meses sin membresía activa.")
    )
    new_client_badge_text = models.CharField(
        _("Texto del Badge"),
        max_length=30,
        default="🎁 Oferta Bienvenida",
        blank=True,
        help_text=_("Texto que se muestra en el badge promocional")
    )

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
    
    def is_client_eligible(self, client):
        """
        Verifica si un cliente es elegible para esta oferta de "nuevo cliente".
        Retorna (is_eligible: bool, reason: str)
        """
        if not self.is_new_client_only:
            return True, ""
        
        from django.utils import timezone
        from clients.models import ClientMembership
        from sales.models import OrderLine
        from dateutil.relativedelta import relativedelta
        
        criteria = self.new_client_criteria
        threshold = self.new_client_days_threshold
        
        if criteria == 'NEVER_HAD_MEMBERSHIP':
            # Cliente nunca ha tenido ninguna membresía en este gym
            has_any = ClientMembership.objects.filter(
                client=client,
                plan__gym=self.gym
            ).exists()
            if has_any:
                return False, _("Esta oferta es solo para clientes que nunca han tenido membresía")
            return True, ""
        
        elif criteria == 'REGISTERED_RECENTLY':
            # Cliente se registró hace menos de X días
            if client.created_at:
                days_since = (timezone.now() - client.created_at).days
                if days_since > threshold:
                    return False, _("Esta oferta es solo para clientes registrados en los últimos {} días").format(threshold)
                return True, ""
            return True, ""
        
        elif criteria == 'NEVER_BOUGHT_THIS':
            # Cliente nunca ha comprado este servicio específico
            has_bought = OrderLine.objects.filter(
                order__client=client,
                service=self,
                order__status__in=['PAID', 'COMPLETED']
            ).exists()
            if has_bought:
                return False, _("Esta oferta es solo para clientes que nunca han comprado este servicio")
            return True, ""
        
        elif criteria == 'INACTIVE_PERIOD':
            # Cliente sin membresía activa en los últimos X meses
            cutoff = timezone.now() - relativedelta(months=threshold)
            recent_active = ClientMembership.objects.filter(
                client=client,
                plan__gym=self.gym,
                end_date__gte=cutoff.date()
            ).exists()
            if recent_active:
                return False, _("Esta oferta es para clientes sin actividad en los últimos {} meses").format(threshold)
            return True, ""
        
        return True, ""

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

