from django.db import models
from django.conf import settings
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
    receipt_notes = models.TextField(
        _("Notas del Recibo"),
        blank=True,
        help_text=_("Texto que aparecerá en el ticket/factura cuando se venda este plan")
    )
    image = models.ImageField(upload_to='membership_images/', null=True, blank=True)
    
    # Barcode (para escaneo rápido en TPV)
    barcode = models.CharField(
        _("Código de Barras"),
        max_length=50,
        blank=True,
        db_index=True,
        help_text=_("Código de barras para venta rápida en TPV")
    )
    
    # Financials
    base_price = models.DecimalField(_("Precio Base"), max_digits=10, decimal_places=2)
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Impuesto Principal"), related_name='membership_plans_primary')
    additional_tax_rates = models.ManyToManyField(
        TaxRate, blank=True,
        verbose_name=_("Impuestos Adicionales"),
        related_name='membership_plans_additional',
        help_text=_("Impuestos adicionales que se aplican junto al principal (ej: recargos locales)")
    )
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
    
    # Activation Mode
    ACTIVATION_MODES = [
        ('ON_SALE', _("En el día de la venta")),
        ('ON_FIRST_VISIT', _("En la primera visita del cliente")),
        ('ON_SPECIFIC_DATE', _("En una fecha específica (manual)")),
    ]
    activation_mode = models.CharField(
        _("Fecha de Activación"),
        max_length=20,
        choices=ACTIVATION_MODES,
        default='ON_SALE',
        help_text=_("Define cuándo se activa la membresía tras la compra")
    )
    
    # Options
    prorate_first_month = models.BooleanField(_("Prorratear primer mes"), default=True)
    scheduling_open_day = models.PositiveIntegerField(
        _("Día de apertura de programación"),
        null=True,
        blank=True,
        help_text=_("Día del mes en que se abren las reservas del siguiente periodo (vacío = sin restricción)")
    )
    display_order = models.IntegerField(default=0)
    
    # Visibility / Reporting
    is_active = models.BooleanField(default=True)
    is_visible_online = models.BooleanField(default=False)
    is_membership = models.BooleanField(_("Es Membresía (Informe)"), default=True, help_text=_("Marcar si este plan cuenta como socio activo para informes."))
    
    # Contract
    contract_required = models.BooleanField(_("Requiere Firma de Contrato"), default=False)
    contract_content = models.TextField(_("Contenido del Contrato"), blank=True, help_text=_("Texto legal que el cliente debe aceptar y firmar."))
    
    # Pause Configuration (for recurring plans)
    allow_pause = models.BooleanField(_("Permitir Pausas"), default=False, help_text=_("Solo para planes recurrentes"))
    pause_fee = models.DecimalField(_("Cargo por Pausa"), max_digits=10, decimal_places=2, default=0, help_text=_("Cargo único al activar la pausa"))
    pause_min_days = models.IntegerField(_("Días Mínimos de Pausa"), default=7)
    pause_max_days = models.IntegerField(_("Días Máximos de Pausa"), default=90)
    pause_max_per_year = models.IntegerField(_("Pausas Máximas al Año"), default=2)
    pause_advance_notice_days = models.IntegerField(_("Días de Anticipación"), default=3, help_text=_("Días mínimos de anticipación para solicitar pausa"))
    pause_allows_gym_access = models.BooleanField(_("Permite Acceso al Gimnasio"), default=False, help_text=_("Durante la pausa"))
    pause_allows_booking = models.BooleanField(_("Permite Reservas"), default=False, help_text=_("Durante la pausa"))
    pause_extends_end_date = models.BooleanField(_("Extiende Fecha Final"), default=True, help_text=_("Suma los días de pausa al final de la membresía"))
    
    # Attendance & Late Cancellation Settings
    count_late_cancel_as_used = models.BooleanField(
        _("Contar Cancelación Tardía como Sesión Consumida"),
        default=False,
        help_text=_("Si está activado, las cancelaciones fuera de ventana contarán como sesión gastada")
    )
    
    # === CUOTA DE INSCRIPCIÓN / MATRÍCULA ===
    has_enrollment_fee = models.BooleanField(
        _("Tiene cuota de inscripción"),
        default=False,
        help_text=_("Cargo único al dar de alta en este plan (matrícula)")
    )
    enrollment_fee = models.DecimalField(
        _("Cuota de Inscripción"),
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_("Importe base de la matrícula")
    )
    enrollment_fee_tax_rate = models.ForeignKey(
        TaxRate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrollment_fees',
        verbose_name=_("Impuesto Inscripción"),
        help_text=_("Impuesto aplicable a la cuota de inscripción")
    )
    enrollment_fee_price_strategy = models.CharField(
        _("Estrategia Precio Matrícula"),
        max_length=20,
        default='TAX_INCLUDED',
        choices=[
            ('TAX_INCLUDED', _("Impuestos Incluidos")),
            ('TAX_EXCLUDED', _("Impuestos Excluidos")),
        ],
        help_text=_("Define si el importe incluye o excluye impuestos")
    )
    enrollment_fee_waivable = models.BooleanField(
        _("Matrícula condonable"),
        default=True,
        help_text=_("Permite al staff eximir la cuota de inscripción en casos especiales")
    )
    
    # Dónde se cobra la matrícula
    ENROLLMENT_FEE_CHANNELS = [
        ('BOTH', _("Presencial y Online")),
        ('ONSITE', _("Solo Presencial (in-situ)")),
        ('ONLINE', _("Solo Online")),
    ]
    enrollment_fee_channel = models.CharField(
        _("Dónde cobrar matrícula"),
        max_length=10,
        choices=ENROLLMENT_FEE_CHANNELS,
        default='BOTH',
        help_text=_("Define en qué canales se cobra la cuota de inscripción")
    )
    
    # === OFERTAS CON RESTRICCIÓN DE ELEGIBILIDAD ===
    ELIGIBILITY_CRITERIA = [
        ('NONE', _("Sin restricción (disponible para todos)")),
        ('NEVER_HAD_MEMBERSHIP', _("Solo clientes que NUNCA han tenido membresía")),
        ('NEVER_BOUGHT_THIS', _("Solo clientes que NUNCA han comprado este plan")),
        ('HAS_BOUGHT_THIS', _("Solo clientes que YA han comprado este plan (fidelización)")),
        ('REGISTERED_RECENTLY', _("Solo registrados recientemente")),
        ('INACTIVE_PERIOD', _("Solo clientes inactivos (re-captación)")),
        ('NO_ACTIVE_MEMBERSHIP', _("Solo clientes SIN membresía activa actualmente")),
        ('HAS_ACTIVE_MEMBERSHIP', _("Solo clientes CON membresía activa (upgrade/complemento)")),
    ]
    
    VISIBILITY_FOR_INELIGIBLE = [
        ('HIDE', _("Ocultar completamente")),
        ('SHOW_LOCKED', _("Mostrar bloqueado (genera interés)")),
    ]
    
    eligibility_criteria = models.CharField(
        _("Criterio de Elegibilidad"),
        max_length=30,
        choices=ELIGIBILITY_CRITERIA,
        default='NONE',
        help_text=_("Define quién puede ver/comprar este plan")
    )
    eligibility_days_threshold = models.PositiveIntegerField(
        _("Umbral de Días/Meses"),
        default=30,
        help_text=_("Para 'Registrado recientemente': días desde registro. Para 'Inactivos': meses sin membresía.")
    )
    visibility_for_ineligible = models.CharField(
        _("Visibilidad para No Elegibles"),
        max_length=15,
        choices=VISIBILITY_FOR_INELIGIBLE,
        default='HIDE',
        help_text=_("Qué hacer con el plan cuando el cliente no cumple el criterio")
    )
    eligibility_badge_text = models.CharField(
        _("Texto del Badge"),
        max_length=30,
        default="",
        blank=True,
        help_text=_("Badge promocional (ej: '🎁 Solo Nuevos', '⭐ VIP', '🔄 Renueva y ahorra')")
    )
    
    # Campos legacy para compatibilidad (migración)
    is_new_client_only = models.BooleanField(
        _("Solo para Nuevos Clientes (legacy)"),
        default=False,
        help_text=_("[DEPRECATED] Usar eligibility_criteria en su lugar")
    )
    new_client_criteria = models.CharField(
        _("Criterio de Cliente Nuevo (legacy)"),
        max_length=30,
        choices=[('NEVER_HAD_MEMBERSHIP', 'Legacy')],
        default='NEVER_HAD_MEMBERSHIP',
        blank=True
    )
    new_client_days_threshold = models.PositiveIntegerField(
        _("Umbral de Días (legacy)"),
        default=30
    )
    new_client_badge_text = models.CharField(
        _("Texto del Badge (legacy)"),
        max_length=30,
        default="🎁 Oferta Bienvenida",
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
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
    def final_enrollment_fee(self):
        """Calcula el precio final de la cuota de inscripción con impuestos"""
        if not self.has_enrollment_fee or self.enrollment_fee == 0:
            return 0
        if not self.enrollment_fee_tax_rate:
            return self.enrollment_fee
        rate = self.enrollment_fee_tax_rate.rate_percent / 100
        # La cuota de inscripción siempre se considera impuestos incluidos por simplicidad
        return self.enrollment_fee
    
    @property
    def enrollment_fee_tax_amount(self):
        """Calcula el importe del impuesto sobre la cuota de inscripción"""
        if not self.has_enrollment_fee or not self.enrollment_fee_tax_rate:
            return 0
        rate = self.enrollment_fee_tax_rate.rate_percent / 100
        # Calcular el impuesto incluido en el precio
        return self.enrollment_fee - (self.enrollment_fee / (1 + rate))
    
    @property
    def first_payment_total(self):
        """Total del primer pago: cuota + matrícula (para transparencia al cliente)"""
        total = self.final_price
        if self.has_enrollment_fee:
            total += self.final_enrollment_fee
        return total
        
    def get_frequency_display_custom(self):
        unit_label = dict(self.FREQUENCY_UNITS).get(self.frequency_unit, '')
        if self.frequency_amount == 1:
            # Singular adjustments
            if self.frequency_unit == 'MONTH': return "Mensual"
            if self.frequency_unit == 'YEAR': return "Anual"
            if self.frequency_unit == 'WEEK': return "Semanal"
            if self.frequency_unit == 'DAY': return "Diario"
        return f"Cada {self.frequency_amount} {unit_label}"
    
    def is_client_eligible(self, client):
        """
        Verifica si un cliente es elegible para este plan.
        Retorna (is_eligible: bool, reason: str)
        """
        from django.utils import timezone
        from clients.models import ClientMembership
        from dateutil.relativedelta import relativedelta
        
        # Usar nuevo sistema de criterios si está configurado
        criteria = self.eligibility_criteria
        threshold = self.eligibility_days_threshold
        
        # Si no hay restricción (NONE) -> elegible para todos
        if criteria == 'NONE':
            # Compatibilidad: revisar campo legacy
            if self.is_new_client_only:
                criteria = self.new_client_criteria or 'NEVER_HAD_MEMBERSHIP'
                threshold = self.new_client_days_threshold
            else:
                return True, ""
        
        if criteria == 'NEVER_HAD_MEMBERSHIP':
            has_any = ClientMembership.objects.filter(
                client=client,
                plan__gym=self.gym
            ).exists()
            if has_any:
                return False, _("Esta oferta es solo para clientes que nunca han tenido membresía")
            return True, ""
        
        elif criteria == 'NEVER_BOUGHT_THIS':
            has_bought = ClientMembership.objects.filter(
                client=client,
                plan=self
            ).exists()
            if has_bought:
                return False, _("Esta oferta es solo para clientes que nunca han comprado este plan")
            return True, ""
        
        elif criteria == 'HAS_BOUGHT_THIS':
            # Solo para clientes que YA compraron este plan (fidelización)
            has_bought = ClientMembership.objects.filter(
                client=client,
                plan=self
            ).exists()
            if not has_bought:
                return False, _("Esta oferta es exclusiva para clientes que ya han tenido este plan")
            return True, ""
        
        elif criteria == 'REGISTERED_RECENTLY':
            if client.created_at:
                days_since = (timezone.now() - client.created_at).days
                if days_since > threshold:
                    return False, _("Esta oferta es solo para clientes registrados en los últimos {} días").format(threshold)
            return True, ""
        
        elif criteria == 'INACTIVE_PERIOD':
            cutoff = timezone.now() - relativedelta(months=threshold)
            recent_active = ClientMembership.objects.filter(
                client=client,
                plan__gym=self.gym,
                end_date__gte=cutoff.date()
            ).exists()
            if recent_active:
                return False, _("Esta oferta es para clientes sin actividad en los últimos {} meses").format(threshold)
            return True, ""
        
        elif criteria == 'NO_ACTIVE_MEMBERSHIP':
            # Solo clientes sin membresía activa actualmente
            today = timezone.now().date()
            has_active = ClientMembership.objects.filter(
                client=client,
                plan__gym=self.gym,
                status='ACTIVE',
                start_date__lte=today,
                end_date__gte=today
            ).exists()
            if has_active:
                return False, _("Esta oferta es solo para clientes sin membresía activa")
            return True, ""
        
        elif criteria == 'HAS_ACTIVE_MEMBERSHIP':
            # Solo clientes con membresía activa (para upgrades/complementos)
            today = timezone.now().date()
            has_active = ClientMembership.objects.filter(
                client=client,
                plan__gym=self.gym,
                status='ACTIVE',
                start_date__lte=today,
                end_date__gte=today
            ).exists()
            if not has_active:
                return False, _("Esta oferta es exclusiva para socios con membresía activa")
            return True, ""
        
        return True, ""
    
    def should_show_to_client(self, client):
        """
        Determina si el plan debe mostrarse a este cliente.
        Retorna (should_show: bool, is_eligible: bool, reason: str)
        """
        # Si no hay restricción, siempre mostrar
        if self.eligibility_criteria == 'NONE' and not self.is_new_client_only:
            return True, True, ""
        
        is_eligible, reason = self.is_client_eligible(client)
        
        if is_eligible:
            return True, True, ""
        
        # No es elegible - verificar visibilidad configurada
        visibility = self.visibility_for_ineligible
        if visibility == 'HIDE':
            return False, False, reason
        else:  # SHOW_LOCKED
            return True, False, reason
    
    def get_badge_text(self):
        """Retorna el texto del badge si aplica"""
        if self.eligibility_badge_text:
            return self.eligibility_badge_text
        # Fallback a campo legacy
        if self.is_new_client_only and self.new_client_badge_text:
            return self.new_client_badge_text
        return ""
    
    def has_eligibility_restriction(self):
        """Indica si este plan tiene alguna restricción de elegibilidad"""
        return self.eligibility_criteria != 'NONE' or self.is_new_client_only

class PlanAccessRule(models.Model):
    """
    Define qué actividades/servicios incluye un plan y con qué restricciones.
    
    Ejemplo de configuración:
    - Plan "Básico": 4 clases/mes, máx 1/día, reservar 24h antes
    - Plan "Premium": Ilimitado, máx 2/día, reservar 7 días antes
    - Plan "VIP": Ilimitado sin restricciones
    """
    PERIODS = [
        ('TOTAL', _("Total (Bono)")),
        ('PER_CYCLE', _("Por Ciclo (Recurrente)")),
        ('PER_DAY', _("Por Día")),
        ('PER_WEEK', _("Por Semana")),
    ]
    
    LIMIT_PERIODS = [
        ('', _("Sin límite")),
        ('PER_DAY', _("Por Día")),
        ('PER_WEEK', _("Por Semana")),
        ('PER_MONTH', _("Por Mes")),
    ]
    
    plan = models.ForeignKey(MembershipPlan, on_delete=models.CASCADE, related_name='access_rules')
    
    # Targets: Can be broadly (Category) or Specific (Activity/Service)
    # At least one should be set.
    activity_category = models.ForeignKey(ActivityCategory, on_delete=models.CASCADE, null=True, blank=True)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, null=True, blank=True)
    
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    
    # === LÍMITES DE CANTIDAD ===
    quantity = models.IntegerField(
        _("Cantidad"), 
        default=0, 
        help_text=_("0 = Ilimitado")
    )
    period = models.CharField(
        max_length=20, 
        choices=PERIODS, 
        default='PER_CYCLE'
    )
    
    # === LÍMITE DE USO (combinado: cantidad + periodo) ===
    usage_limit = models.PositiveIntegerField(
        _("Límite de uso"),
        default=0,
        help_text=_("Máximo de usos permitidos en el periodo seleccionado. 0 = sin límite")
    )
    usage_limit_period = models.CharField(
        _("Periodo del límite"),
        max_length=20,
        choices=LIMIT_PERIODS,
        default='',
        blank=True,
        help_text=_("Periodo sobre el que aplica el límite de uso")
    )
    
    # === RESTRICCIONES DE RESERVA (NUEVO) ===
    max_per_day = models.PositiveIntegerField(
        _("Máx. reservas por día"),
        default=0,
        help_text=_("0 = Sin límite diario")
    )
    
    max_per_week = models.PositiveIntegerField(
        _("Máx. reservas por semana"),
        default=0,
        help_text=_("0 = Sin límite semanal")
    )
    
    max_per_month = models.PositiveIntegerField(
        _("Máx. reservas por mes"),
        default=0,
        help_text=_("0 = Sin límite mensual")
    )
    
    no_consecutive_days = models.BooleanField(
        _("No permite días consecutivos"),
        default=False,
        help_text=_("Impide que el cliente reserve o asista en días seguidos")
    )
    
    max_simultaneous = models.PositiveIntegerField(
        _("Máx. reservas simultáneas"),
        default=0,
        help_text=_("0 = Sin límite de reservas futuras a la vez")
    )
    
    # === VENTANA DE RESERVA ===
    advance_booking_hours = models.PositiveIntegerField(
        _("Horas de antelación para reservar"),
        default=0,
        help_text=_("Cuántas horas antes puede reservar (0 = usar config. global)")
    )
    
    advance_booking_days = models.PositiveIntegerField(
        _("Días máximos para reservar"),
        default=0,
        help_text=_("Cuántos días en el futuro puede reservar (0 = usar config. global)")
    )
    
    # === RESTRICCIÓN DE FRANJA HORARIA ===
    access_time_start = models.TimeField(
        _("Hora de acceso desde"),
        null=True,
        blank=True,
        help_text=_("Hora desde la que se permite reservar/asistir (vacío = sin restricción)")
    )
    access_time_end = models.TimeField(
        _("Hora de acceso hasta"),
        null=True,
        blank=True,
        help_text=_("Hora hasta la que se permite reservar/asistir (vacío = sin restricción)")
    )
    
    # === PRIORIDAD Y ACCESO ANTICIPADO (Para planes premium) ===
    booking_priority = models.PositiveIntegerField(
        _("Prioridad de reserva"),
        default=0,
        help_text=_("Mayor número = más prioridad (para desempate en waitlist)")
    )
    
    early_access_hours = models.PositiveIntegerField(
        _("Horas de acceso anticipado"),
        default=0,
        help_text=_(
            "Horas antes de la apertura normal en que este plan puede reservar. "
            "Ej: si la actividad abre reservas 48h antes y este campo es 24, "
            "los clientes con este plan pueden reservar 72h antes."
        )
    )
    
    # === PERMITE LISTA DE ESPERA ===
    allow_waitlist = models.BooleanField(
        _("Permitir lista de espera"),
        default=True,
        help_text=_("Si la clase está llena, puede unirse a la lista")
    )
    
    class Meta:
        verbose_name = _("Regla de Acceso")
        verbose_name_plural = _("Reglas de Acceso")
    
    def __str__(self):
        if self.activity: target = f"Actividad: {self.activity.name}"
        elif self.activity_category: target = f"Cat. Act.: {self.activity_category.name}"
        elif self.service: target = f"Servicio: {self.service.name}"
        elif self.service_category: target = f"Cat. Serv.: {self.service_category.name}"
        else: target = "Todo"
        
        qty = "Ilimitado" if self.quantity == 0 else str(self.quantity)
        return f"{qty} x {target}"
    
    def get_restrictions_display(self):
        """Devuelve un resumen legible de las restricciones"""
        parts = []
        # Nuevo campo combinado
        if self.usage_limit > 0 and self.usage_limit_period:
            period_labels = {'PER_DAY': 'día', 'PER_WEEK': 'semana', 'PER_MONTH': 'mes'}
            label = period_labels.get(self.usage_limit_period, self.usage_limit_period)
            parts.append(f"Máx {self.usage_limit}/{label}")
        else:
            # Legacy fields (solo si no hay campo combinado)
            if self.max_per_day > 0:
                parts.append(f"Máx {self.max_per_day}/día")
            if self.max_per_week > 0:
                parts.append(f"Máx {self.max_per_week}/semana")
            if self.max_per_month > 0:
                parts.append(f"Máx {self.max_per_month}/mes")
        if self.no_consecutive_days:
            parts.append("Sin días consecutivos")
        if self.max_simultaneous > 0:
            parts.append(f"Máx {self.max_simultaneous} simultáneas")
        if self.advance_booking_days > 0:
            parts.append(f"Reservar hasta {self.advance_booking_days} días antes")
        if self.access_time_start and self.access_time_end:
            parts.append(f"Horario: {self.access_time_start.strftime('%H:%M')} - {self.access_time_end.strftime('%H:%M')}")
        elif self.access_time_start:
            parts.append(f"Desde las {self.access_time_start.strftime('%H:%M')}")
        elif self.access_time_end:
            parts.append(f"Hasta las {self.access_time_end.strftime('%H:%M')}")
        if self.early_access_hours > 0:
            parts.append(f"Acceso anticipado: {self.early_access_hours}h")
        return " • ".join(parts) if parts else "Sin restricciones adicionales"


class MembershipPause(models.Model):
    """Historial de pausas en membresías"""
    class Status(models.TextChoices):
        PENDING = 'PENDING', _("Pendiente")
        ACTIVE = 'ACTIVE', _("Activa")
        COMPLETED = 'COMPLETED', _("Completada")
        CANCELLED = 'CANCELLED', _("Cancelada")
    
    membership = models.ForeignKey('clients.ClientMembership', on_delete=models.CASCADE, related_name='pauses')
    start_date = models.DateField(_("Fecha de Inicio"))
    end_date = models.DateField(_("Fecha de Fin"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    fee_charged = models.DecimalField(_("Cargo Aplicado"), max_digits=10, decimal_places=2, default=0)
    reason = models.TextField(_("Motivo"), blank=True, help_text=_("Motivo de la pausa"))
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_pauses')
    created_at = models.DateTimeField(auto_now_add=True)
    
    gym_access_allowed = models.BooleanField(_("Acceso Permitido"), default=False)
    booking_allowed = models.BooleanField(_("Reservas Permitidas"), default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Pausa de Membresía")
        verbose_name_plural = _("Pausas de Membresías")
    
    def __str__(self):
        return f"Pausa {self.membership.client.full_name} ({self.start_date} - {self.end_date})"
    
    @property
    def duration_days(self):
        """Duración de la pausa en días"""
        return (self.end_date - self.start_date).days + 1
    
    def is_active_now(self):
        """Verifica si la pausa está activa en este momento"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.status == self.Status.ACTIVE and self.start_date <= today <= self.end_date
