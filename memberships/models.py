from django.db import models
from django.utils.translation import gettext_lazy as _
from organizations.models import Gym
from finance.models import TaxRate
from activities.models import Activity, ActivityCategory
from services.models import Service, ServiceCategory

class MembershipPlan(models.Model):
    FREQUENCY_UNITS = [
        ('DAY', _("Días")),
        ('WEEK', _("Semanas")),
        ('MONTH', _("Meses")),
        ('YEAR', _("Años")),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='membership_plans')
    name = models.CharField(_("Nombre del Plan"), max_length=100)
    description = models.TextField(_("Descripción"), blank=True)
    image = models.ImageField(upload_to='membership_images/', null=True, blank=True)
    
    # Financials
    base_price = models.DecimalField(_("Precio Base"), max_digits=10, decimal_places=2)
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.SET_NULL, null=True, blank=True)
    price_strategy = models.CharField(max_length=20, default='TAX_INCLUDED', choices=[
        ('TAX_INCLUDED', _("Impuestos Incluidos")),
        ('TAX_EXCLUDED', _("Impuestos Excluidos")),
    ])
    
    # Recurring (Flexible)
    is_recurring = models.BooleanField(_("Es Recurrente"), default=True)
    frequency_amount = models.IntegerField(_("Cada..."), default=1)
    frequency_unit = models.CharField(_("Unidad"), max_length=10, choices=FREQUENCY_UNITS, default='MONTH')
    
    # Pack Settings
    pack_validity_days = models.IntegerField(_("Días de Validez"), null=True, blank=True)
    
    # Options
    prorate_first_month = models.BooleanField(_("Prorratear primer mes"), default=True)
    display_order = models.IntegerField(default=0)
    
    # Visibility / Reporting
    is_active = models.BooleanField(default=True)
    is_visible_online = models.BooleanField(default=False)
    is_membership = models.BooleanField(_("Es Membresía (Informe)"), default=True, help_text=_("Marcar si este plan cuenta como socio activo para informes."))
    
    # Contract
    contract_required = models.BooleanField(_("Requiere Firma de Contrato"), default=False)
    contract_content = models.TextField(_("Contenido del Contrato"), blank=True, help_text=_("Texto legal que el cliente debe aceptar y firmar."))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
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
        
    def get_frequency_display_custom(self):
        unit_label = dict(self.FREQUENCY_UNITS).get(self.frequency_unit, '')
        if self.frequency_amount == 1:
            # Singular adjustments
            if self.frequency_unit == 'MONTH': return "Mensual"
            if self.frequency_unit == 'YEAR': return "Anual"
            if self.frequency_unit == 'WEEK': return "Semanal"
            if self.frequency_unit == 'DAY': return "Diario"
        return f"Cada {self.frequency_amount} {unit_label}"

class PlanAccessRule(models.Model):
    PERIODS = [
        ('TOTAL', _("Total (Bono)")),
        ('PER_CYCLE', _("Por Ciclo (Recurrente)")),
    ]
    
    plan = models.ForeignKey(MembershipPlan, on_delete=models.CASCADE, related_name='access_rules')
    
    # Targets: Can be broadly (Category) or Specific (Activity/Service)
    # At least one should be set.
    activity_category = models.ForeignKey(ActivityCategory, on_delete=models.CASCADE, null=True, blank=True)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, null=True, blank=True)
    
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    
    quantity = models.IntegerField(_("Cantidad"), default=0, help_text=_("0 = Ilimitado"))
    period = models.CharField(max_length=20, choices=PERIODS, default='PER_CYCLE')
    
    def __str__(self):
        if self.activity: target = f"Actividad: {self.activity.name}"
        elif self.activity_category: target = f"Cat. Act.: {self.activity_category.name}"
        elif self.service: target = f"Servicio: {self.service.name}"
        elif self.service_category: target = f"Cat. Serv.: {self.service_category.name}"
        else: target = "Todo"
        
        qty = "Ilimitado" if self.quantity == 0 else str(self.quantity)
        return f"{qty} x {target}"
