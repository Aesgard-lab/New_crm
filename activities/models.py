from django.db import models
from django.utils.translation import gettext_lazy as _
from organizations.models import Gym
from staff.models import StaffProfile

class Room(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='rooms')
    name = models.CharField(_("Nombre de la Sala"), max_length=100)
    capacity = models.PositiveIntegerField(_("Aforo Máximo"))
    layout_configuration = models.JSONField(_("Configuración de Diseño"), default=dict, blank=True)
    
    class Meta:
        permissions = [
            ("access_calendar", "Acceder al Calendario de Clases"),
            ("create_class_sessions", "Crear Sesiones de Clases"),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.gym.name})"

class ActivityCategory(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='activity_categories', null=True, blank=True)
    name = models.CharField(_("Nombre"), max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    icon = models.ImageField(upload_to='activity_icons/', null=True, blank=True)
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Evitar que una categoría sea su propio padre
        if self.parent_id and self.pk and self.parent_id == self.pk:
            raise ValidationError({'parent': _('Una categoría no puede ser su propia categoría padre.')})
        # Evitar subcategorías de subcategorías (máximo 2 niveles)
        if self.parent and self.parent.parent:
            raise ValidationError({'parent': _('No se permiten más de 2 niveles de anidación.')})
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

class Activity(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='activities')
    category = models.ForeignKey(ActivityCategory, on_delete=models.SET_NULL, null=True, related_name='activities')
    name = models.CharField(_("Nombre de la Actividad"), max_length=100)
    description = models.TextField(_("Descripción"), blank=True)
    image = models.ImageField(upload_to='activity_images/', null=True, blank=True)
    color = models.CharField(_("Color en Calendario"), max_length=7, default="#3B82F6", help_text="Código HEX (ej: #3B82F6)")
    duration = models.PositiveIntegerField(_("Duración (min)"), default=60)
    base_capacity = models.PositiveIntegerField(_("Aforo Base"), help_text=_("El aforo final dependerá de la sala"))
    intensity_level = models.CharField(_("Intensidad"), max_length=20, choices=[
        ('LOW', 'Baja'), ('MEDIUM', 'Media'), ('HIGH', 'Alta')
    ], default='MEDIUM')
    video_url = models.URLField(_("Video URL"), blank=True)
    
    # Check-in QR configuration per activity
    qr_checkin_enabled = models.BooleanField(
        _("Check-in QR habilitado"), 
        default=False,
        help_text=_("Permite a los clientes marcar asistencia escaneando QR")
    )
    
    # Online Visibility
    is_visible_online = models.BooleanField(
        _("Visible en Horario Público"),
        default=False,
        help_text=_("Si se activa, la actividad aparecerá en el horario público de la web/app")
    )
    
    # Spot Booking - Reserva de puesto específico
    allow_spot_booking = models.BooleanField(
        _("Permitir reserva de puesto"),
        default=False,
        help_text=_("Permite a los clientes elegir un puesto/máquina específico al reservar")
    )
    
    eligible_staff = models.ManyToManyField(StaffProfile, related_name='qualified_activities', blank=True)
    policy = models.ForeignKey('ActivityPolicy', on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')

    class Meta:
        permissions = [
            ("access_calendar", "Acceder al Calendario de Clases"),
            ("manage_activity_sessions", "Gestionar Sesiones de Actividades"),
        ]

    def __str__(self):
        return self.name

class ActivityPolicy(models.Model):
    PENALTY_CHOICES = [
        ('STRIKE', 'Strike (Falta)'),
        ('FEE', 'Cobro Monetario'),
        ('FORFEIT', 'Pérdida de Crédito'),
    ]

    WINDOW_MODE_CHOICES = [
        ('OPEN', _("Abierto (Sin restricción)")),
        ('RELATIVE_START', _("Horas antes del inicio")),
        ('FIXED_TIME', _("Días antes (hora fija)")),
        ('WEEKLY_FIXED', _("Día de la semana (hora fija)")),
    ]
    
    WEEKDAY_CHOICES = [
        (0, _("Lunes")),
        (1, _("Martes")),
        (2, _("Miércoles")),
        (3, _("Jueves")),
        (4, _("Viernes")),
        (5, _("Sábado")),
        (6, _("Domingo")),
    ]
    
    CANCELLATION_UNIT_CHOICES = [
        ('MINUTES', _("Minutos")),
        ('HOURS', _("Horas")),
        ('DAYS', _("Días")),
    ]

    WAITLIST_MODE_CHOICES = [
        ('AUTO_PROMOTE', _("Auto-Promoción (Automático)")),
        ('BROADCAST', _("Broadcast (Notifica a varios)")),
        ('FIRST_CLAIM', _("Primero que Reclama (Competición)")),
    ]
    
    MEMBERSHIP_REQUIREMENT_CHOICES = [
        (None, _("Heredar de configuración general")),
        (True, _("Sí, requerir")),
        (False, _("No, permitir sin membresía")),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='activity_policies')
    name = models.CharField(_("Nombre de la Política"), max_length=100)
    
    # Booking Configuration
    booking_window_mode = models.CharField(_("Modo de Apertura"), max_length=20, choices=WINDOW_MODE_CHOICES, default='RELATIVE_START')
    booking_window_value = models.PositiveIntegerField(_("Valor Antelación"), default=48, help_text=_("Horas (si es relativo) o Días (si es fijo)"))
    booking_time_release = models.TimeField(_("Hora de Apertura"), null=True, blank=True, help_text=_("Solo si el modo es Hora Fija (ej: 00:00)"))
    booking_weekday_release = models.IntegerField(
        _("Día de Apertura"), 
        choices=WEEKDAY_CHOICES, 
        null=True, 
        blank=True,
        help_text=_("Solo para modo 'Día de la semana'")
    )
    
    # Restricción de reserva por membresía (None = heredar de gym, True = requerir, False = no requerir)
    require_active_membership = models.BooleanField(
        _("Requiere Membresía Activa"),
        null=True,
        blank=True,
        default=None,
        help_text=_("Dejar vacío para usar la configuración general del gimnasio")
    )
    require_paid_membership = models.BooleanField(
        _("Requiere Membresía Pagada"),
        null=True,
        blank=True,
        default=None,
        help_text=_("Dejar vacío para usar la configuración general del gimnasio")
    )

    # Cancellation Configuration
    cancellation_window_value = models.PositiveIntegerField(
        _("Ventana de Cancelación"), 
        default=2,
        help_text=_("Tiempo antes de la clase para cancelar sin penalización")
    )
    cancellation_window_unit = models.CharField(
        _("Unidad de Tiempo"),
        max_length=10,
        choices=CANCELLATION_UNIT_CHOICES,
        default='HOURS'
    )
    penalty_type = models.CharField(_("Tipo de Penalización"), max_length=20, choices=PENALTY_CHOICES, default='FORFEIT')
    fee_amount = models.DecimalField(_("Monto de Multa"), max_digits=6, decimal_places=2, null=True, blank=True, help_text=_("Solo si el tipo es Cobro Monetario"))

    # Waitlist Configuration
    waitlist_enabled = models.BooleanField(_("Lista de Espera Activa"), default=True)
    waitlist_mode = models.CharField(_("Modo de Lista"), max_length=20, choices=WAITLIST_MODE_CHOICES, default='AUTO_PROMOTE')
    waitlist_limit = models.PositiveIntegerField(_("Límite Lista Espera"), default=0, help_text=_("0 = Sin límite"))
    auto_promote_cutoff_hours = models.PositiveIntegerField(_("Cierre Auto-Promoción (Horas)"), default=1, help_text=_("Horas antes donde la lista deja de correr sola"))
    
    # Claim Timeout (para modos BROADCAST y FIRST_CLAIM)
    waitlist_claim_timeout_minutes = models.PositiveIntegerField(
        _("Timeout para Reclamar (Minutos)"), 
        default=30,
        help_text=_("Minutos que tienen los clientes para reclamar. Tras esto, se auto-promociona al primero.")
    )
    
    # VIP Configuration - Grupos y Planes que tienen prioridad
    vip_groups = models.ManyToManyField(
        'clients.ClientGroup',
        blank=True,
        related_name='vip_policies',
        verbose_name=_("Grupos VIP"),
        help_text=_("Clientes en estos grupos tienen prioridad absoluta en lista de espera")
    )
    vip_membership_plans = models.ManyToManyField(
        'memberships.MembershipPlan',
        blank=True,
        related_name='vip_policies',
        verbose_name=_("Planes VIP"),
        help_text=_("Clientes con estos planes tienen prioridad absoluta en lista de espera")
    )
    
    def clean(self):
        """Validación para evitar configuraciones contradictorias"""
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Validar modo FIXED_TIME y WEEKLY_FIXED requieren hora
        if self.booking_window_mode in ('FIXED_TIME', 'WEEKLY_FIXED') and not self.booking_time_release:
            errors['booking_time_release'] = _("Debes especificar la hora de apertura para este modo")
        
        # Validar modo WEEKLY_FIXED requiere día de la semana
        if self.booking_window_mode == 'WEEKLY_FIXED' and self.booking_weekday_release is None:
            errors['booking_weekday_release'] = _("Debes especificar el día de la semana para este modo")
        
        # Validar que require_paid implica require_active (solo si ambos tienen valores explícitos)
        if self.require_paid_membership is True and self.require_active_membership is False:
            errors['require_active_membership'] = _("Si requieres membresía pagada, no puedes desactivar membresía activa")
        
        # Validar penalty FEE requiere monto
        if self.penalty_type == 'FEE' and not self.fee_amount:
            errors['fee_amount'] = _("Debes especificar el monto de la multa")
        
        if errors:
            raise ValidationError(errors)
    
    def get_cancellation_window_timedelta(self):
        """Retorna el timedelta de la ventana de cancelación"""
        from datetime import timedelta
        value = self.cancellation_window_value
        if self.cancellation_window_unit == 'MINUTES':
            return timedelta(minutes=value)
        elif self.cancellation_window_unit == 'HOURS':
            return timedelta(hours=value)
        else:  # DAYS
            return timedelta(days=value)
    
    def get_booking_opens_at(self, session_datetime):
        """
        Calcula cuándo se abren las reservas para una sesión específica.
        Retorna None si el modo es OPEN (siempre abierto).
        """
        from datetime import timedelta, datetime
        from django.utils import timezone
        
        if self.booking_window_mode == 'OPEN':
            return None  # Siempre abierto
        
        elif self.booking_window_mode == 'RELATIVE_START':
            # X horas antes del inicio
            return session_datetime - timedelta(hours=self.booking_window_value)
        
        elif self.booking_window_mode == 'FIXED_TIME':
            # X días antes a una hora específica
            release_date = session_datetime.date() - timedelta(days=self.booking_window_value)
            release_time = self.booking_time_release or datetime.min.time()
            return timezone.make_aware(datetime.combine(release_date, release_time))
        
        elif self.booking_window_mode == 'WEEKLY_FIXED':
            # El día de la semana específico a una hora específica
            # Encontrar el día de la semana anterior más cercano
            session_date = session_datetime.date()
            target_weekday = self.booking_weekday_release or 0
            
            # Calcular días hacia atrás hasta el día objetivo
            days_back = (session_date.weekday() - target_weekday) % 7
            if days_back == 0:
                days_back = 7  # Si es el mismo día, ir a la semana anterior
            
            release_date = session_date - timedelta(days=days_back)
            release_time = self.booking_time_release or datetime.min.time()
            return timezone.make_aware(datetime.combine(release_date, release_time))
        
        return None
    
    def is_booking_open(self, session_datetime):
        """Verifica si las reservas están abiertas para una sesión"""
        from django.utils import timezone
        
        opens_at = self.get_booking_opens_at(session_datetime)
        if opens_at is None:
            return True  # Modo OPEN
        return timezone.now() >= opens_at
    
    def get_effective_require_active_membership(self):
        """
        Retorna si se requiere membresía activa, considerando la jerarquía:
        1. Si la política tiene un valor explícito (True/False), lo usa
        2. Si es None, hereda de la configuración general del gimnasio
        """
        if self.require_active_membership is not None:
            return self.require_active_membership
        # Heredar del gimnasio - por defecto True si no hay config
        return True  # Por defecto requerimos membresía activa
    
    def get_effective_require_paid_membership(self):
        """
        Retorna si se requiere membresía pagada, considerando la jerarquía:
        1. Si la política tiene un valor explícito (True/False), lo usa
        2. Si es None, hereda de la configuración general del gimnasio
        """
        if self.require_paid_membership is not None:
            return self.require_paid_membership
        # Heredar del gimnasio - usa allow_booking_with_pending_payment (invertido)
        # Si allow_booking_with_pending_payment = True, entonces require_paid = False
        return not self.gym.allow_booking_with_pending_payment
    
    def can_client_book(self, client):
        """
        Verifica si un cliente puede reservar según los requisitos de membresía.
        Retorna (can_book: bool, reason: str|None)
        """
        from clients.models import ClientMembership
        from django.utils import timezone
        
        require_active = self.get_effective_require_active_membership()
        require_paid = self.get_effective_require_paid_membership()
        
        # Si no requiere membresía activa, puede reservar
        if not require_active:
            return True, None
        
        # Verificar membresía activa
        active_membership = ClientMembership.objects.filter(
            client=client,
            status='ACTIVE',
            end_date__gte=timezone.now().date()
        ).first()
        
        if not active_membership:
            return False, "Necesitas una membresía activa para reservar esta clase"
        
        # Si requiere pago al día
        if require_paid:
            # Verificar si tiene pagos pendientes
            if hasattr(active_membership, 'has_pending_payment') and active_membership.has_pending_payment():
                return False, "Tienes pagos pendientes. Regulariza tu situación para reservar."
        
        return True, None
    
    def __str__(self):
        return f"{self.name}"

class ScheduleRule(models.Model):
    """
    Defines a recurring schedule pattern (e.g. Yoga every Mon/Wed at 10:00).
    Used to generate ActivitySessions.
    """
    DAYS_OF_WEEK = [
        (0, _("Lunes")), (1, _("Martes")), (2, _("Miércoles")), 
        (3, _("Jueves")), (4, _("Viernes")), (5, _("Sábado")), (6, _("Domingo"))
    ]

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='schedule_rules')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='rules')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True)
    
    day_of_week = models.IntegerField(_("Día de la Semana"), choices=DAYS_OF_WEEK)
    start_time = models.TimeField(_("Hora Inicio"))
    end_time = models.TimeField(_("Hora Fin"))
    
    start_date = models.DateField(_("Vigente desde"), auto_now_add=True)
    end_date = models.DateField(_("Vigente hasta"), null=True, blank=True)
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        day_label = dict(self.DAYS_OF_WEEK).get(self.day_of_week, 'N/A')
        return f"{self.activity.name} - {day_label} {self.start_time}"

class ActivitySession(models.Model):
    """
    A specific instance of a class (e.g. Yoga on Jan 12th at 10:00).
    """
    STATUS_CHOICES = [
        ('SCHEDULED', _("Programada")),
        ('CANCELLED', _("Cancelada")),
        ('COMPLETED', _("Completada")),
    ]

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='sessions')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='sessions')
    rule = models.ForeignKey(ScheduleRule, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_sessions')
    
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True)
    
    start_datetime = models.DateTimeField(_("Inicio"))
    end_datetime = models.DateTimeField(_("Fin"))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    
    # Capacity management (snapshot from Activity/Room, but editable per session)
    max_capacity = models.PositiveIntegerField(_("Aforo Máximo"), default=0)
    
    attendees = models.ManyToManyField('clients.Client', related_name='attended_sessions', blank=True)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_datetime']

    def __str__(self):
        return f"{self.activity.name} - {self.start_datetime.strftime('%d/%m %H:%M')}"
    
    @property
    def attendee_count(self):
        return self.attendees.count()
    
    @property
    def utilization_percent(self):
        if self.max_capacity == 0: return 0
        return (self.attendees.count() / self.max_capacity) * 100



class ActivitySessionBooking(models.Model):
    """
    Representa una reserva de un cliente para una sesión de actividad específica.
    """
    STATUS_CHOICES = [
        ('CONFIRMED', _("Confirmada")),
        ('CANCELLED', _("Cancelada")),
        ('PENDING', _("Pendiente de Pago")), # Si requiere pago previo
    ]
    
    ATTENDANCE_STATUS_CHOICES = [
        ('PENDING', _("Pendiente")),  # Reserva confirmada pero aún no ha pasado la clase
        ('ATTENDED', _("Asistió")),  # Marcado como asistido
        ('NO_SHOW', _("No Asistió")),  # Marcado como ausente
        ('LATE_CANCEL', _("Canceló Tarde")),  # Canceló después de la ventana permitida
    ]

    session = models.ForeignKey(ActivitySession, on_delete=models.CASCADE, related_name='bookings')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='bookings')
    
    # Spot booking - Puesto reservado
    spot_number = models.PositiveIntegerField(
        _("Número de puesto"),
        null=True,
        blank=True,
        help_text=_("Número de puesto/máquina reservado (si la actividad lo permite)")
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CONFIRMED')
    attendance_status = models.CharField(
        max_length=20, 
        choices=ATTENDANCE_STATUS_CHOICES, 
        default='PENDING',
        help_text=_("Estado de asistencia a la clase")
    )
    booked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Flags adicionales
    attended = models.BooleanField(default=False)  # Mantener por compatibilidad, se sincroniza con attendance_status
    marked_by = models.ForeignKey(
        StaffProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendances',
        help_text=_("Staff que marcó la asistencia")
    )
    marked_at = models.DateTimeField(null=True, blank=True, help_text=_("Cuándo se marcó la asistencia"))
    
    class Meta:
        unique_together = ('session', 'client')
        ordering = ['-booked_at']
        verbose_name = _("Reserva de Clase")
        verbose_name_plural = _("Reservas de Clases")

    def __str__(self):
        return f"Reserva: {self.client} - {self.session}"
    
    def mark_attendance(self, status, staff=None):
        """
        Marca el estado de asistencia y sincroniza el flag 'attended'
        """
        from django.utils import timezone
        self.attendance_status = status
        self.attended = (status == 'ATTENDED')
        self.marked_by = staff
        self.marked_at = timezone.now()
        self.save()
        
        # Si marca como cancelado tarde, actualizar el estado general
        if status == 'LATE_CANCEL':
            self.status = 'CANCELLED'
            self.save()


class WaitlistEntry(models.Model):
    STATUS_CHOICES = [
        ('WAITING', _("En espera")),
        ('NOTIFIED', _("Notificado (Esperando claim)")),
        ('PROMOTED', _("Promovido (Dentro)")),
        ('EXPIRED', _("Expirado")),
        ('CANCELLED', _("Cancelado")),
    ]

    session = models.ForeignKey(ActivitySession, on_delete=models.CASCADE, related_name='waitlist_entries')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='waitlist_entries')
    gym = models.ForeignKey('organizations.Gym', on_delete=models.CASCADE, related_name='waitlist_entries', null=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WAITING')
    promoted_at = models.DateTimeField(null=True, blank=True)
    
    # VIP Priority
    is_vip = models.BooleanField(default=False, help_text=_("Cliente tiene prioridad VIP"))
    
    # Claim tracking (para modos FIRST_CLAIM y BROADCAST)
    notified_at = models.DateTimeField(null=True, blank=True, help_text=_("Cuándo se notificó que hay plaza"))
    claim_expires_at = models.DateTimeField(null=True, blank=True, help_text=_("Cuándo expira el tiempo para reclamar"))
    claimed_at = models.DateTimeField(null=True, blank=True, help_text=_("Cuándo reclamó la plaza"))
    note = models.TextField(blank=True, default='')
    
    class Meta:
        unique_together = ('session', 'client')
        ordering = ['-is_vip', 'joined_at']  # VIPs primero, luego por orden de llegada

    def __str__(self):
        return f"{self.client} in waitlist for {self.session} ({self.status})"


class ReviewSettings(models.Model):
    """
    Configuración global para el sistema de valoraciones de clases.
    """
    gym = models.OneToOneField(Gym, on_delete=models.CASCADE, related_name='review_settings')
    
    # Activación
    enabled = models.BooleanField(default=False, help_text="Activar sistema de valoraciones")
    
    # Timing
    delay_hours = models.PositiveIntegerField(default=3, help_text="Horas después de clase para solicitar review")
    
    # Frecuencia
    REQUEST_MODE_CHOICES = [
        ('ALL', 'Solicitar a todos los asistentes'),
        ('RANDOM', 'Solicitud aleatoria'),
    ]
    request_mode = models.CharField(max_length=20, choices=REQUEST_MODE_CHOICES, default='RANDOM')
    random_probability = models.PositiveIntegerField(
        default=30, 
        help_text="Probabilidad % de solicitar review (solo si modo aleatorio)"
    )
    
    # Incentivos
    points_per_review = models.PositiveIntegerField(default=10, help_text="Puntos de fidelidad por dejar review")
    
    # Visibilidad
    reviews_public = models.BooleanField(default=False, help_text="Reviews visibles públicamente")
    require_approval = models.BooleanField(default=True, help_text="Requiere aprobación del staff antes de publicar")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Review Settings - {self.gym.name}"


class ClassReview(models.Model):
    """
    Valoración de una clase por un cliente.
    """
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='class_reviews')
    session = models.ForeignKey(ActivitySession, on_delete=models.CASCADE, related_name='reviews')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='class_reviews')
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='received_reviews')
    
    # Valoraciones (1-5 estrellas)
    instructor_rating = models.PositiveIntegerField(help_text="Valoración del instructor (1-5)")
    class_rating = models.PositiveIntegerField(help_text="Valoración de la clase (1-5)")
    
    # Comentario opcional
    comment = models.TextField(blank=True)
    
    # Tags predefinidos (JSON array)
    tags = models.JSONField(default=list, blank=True, help_text="Tags: Limpio, Intenso, Amigable, etc.")
    
    # Estado
    is_approved = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        StaffProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_reviews'
    )
    
    class Meta:
        unique_together = ('session', 'client')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review by {self.client} - {self.session.activity.name} ({self.instructor_rating}⭐)"
    
    @property
    def average_rating(self):
        return (self.instructor_rating + self.class_rating) / 2


class ReviewRequest(models.Model):
    """
    Solicitud de review enviada a un cliente.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('COMPLETED', 'Completada'),
        ('EXPIRED', 'Expirada'),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='review_requests')
    session = models.ForeignKey(ActivitySession, on_delete=models.CASCADE, related_name='review_requests')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='review_requests')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(help_text="Fecha límite para completar la review")
    
    # Notificación
    email_sent = models.BooleanField(default=False)
    popup_created = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('session', 'client')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review Request - {self.client} for {self.session}"


class AttendanceSettings(models.Model):
    """
    Configuración global para el sistema de asistencias/check-in del gimnasio.
    """
    CHECKIN_MODE_CHOICES = [
        ('STAFF_ONLY', _("Solo el staff marca asistencia")),
        ('QR_ENABLED', _("Clientes pueden marcar con QR")),
        ('FACE_ENABLED', _("Reconocimiento facial habilitado")),
        ('BOTH', _("Ambos métodos disponibles")),
        ('ALL', _("Todos los métodos (QR, Facial, Staff)")),
    ]
    
    gym = models.OneToOneField(Gym, on_delete=models.CASCADE, related_name='attendance_settings')
    
    # Modo de check-in global
    checkin_mode = models.CharField(
        _("Modo de Check-in"),
        max_length=20,
        choices=CHECKIN_MODE_CHOICES,
        default='STAFF_ONLY',
        help_text=_("Define cómo los clientes pueden marcar asistencia")
    )
    
    # Ventana de tiempo para check-in QR
    qr_checkin_minutes_before = models.PositiveIntegerField(
        _("Minutos antes de clase"),
        default=15,
        help_text=_("Minutos antes del inicio que se permite el check-in")
    )
    qr_checkin_minutes_after = models.PositiveIntegerField(
        _("Minutos después del inicio"),
        default=30,
        help_text=_("Minutos después del inicio que se permite el check-in")
    )
    
    # QR dinámico (seguridad)
    qr_refresh_seconds = models.PositiveIntegerField(
        _("Renovar QR cada (segundos)"),
        default=30,
        help_text=_("Segundos para renovar el código QR (seguridad)")
    )
    
    # Mensaje de confirmación
    checkin_success_message = models.CharField(
        _("Mensaje de éxito"),
        max_length=200,
        default="✅ ¡Check-in completado! Te esperamos en clase.",
        help_text=_("Mensaje mostrado al cliente tras check-in exitoso")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Configuración de Asistencias")
        verbose_name_plural = _("Configuraciones de Asistencias")
    
    def __str__(self):
        return f"Attendance Settings - {self.gym.name}"


class SessionCheckin(models.Model):
    """
    Registro de check-in a una sesión de clase.
    Registra quién, cuándo y cómo se hizo el check-in.
    """
    CHECKIN_METHOD_CHOICES = [
        ('STAFF', _("Marcado por Staff")),
        ('QR', _("Escaneado QR por cliente")),
        ('FACE', _("Reconocimiento facial")),
        ('APP', _("Desde App del cliente")),
        ('AUTO', _("Automático (reserva previa)")),
    ]
    
    session = models.ForeignKey(
        ActivitySession, 
        on_delete=models.CASCADE, 
        related_name='checkins'
    )
    client = models.ForeignKey(
        'clients.Client', 
        on_delete=models.CASCADE, 
        related_name='class_checkins'
    )
    
    # Método de check-in
    method = models.CharField(
        _("Método de check-in"),
        max_length=20,
        choices=CHECKIN_METHOD_CHOICES,
        default='STAFF'
    )
    
    # Verificación - token usado para QR (previene reutilización)
    qr_token = models.CharField(max_length=64, blank=True, null=True)
    
    # Staff que hizo el check-in (si aplica)
    checked_by = models.ForeignKey(
        StaffProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checkins_performed'
    )
    
    # Timestamps
    checked_in_at = models.DateTimeField(auto_now_add=True)
    
    # IP para auditoría (opcional)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        unique_together = ('session', 'client')
        ordering = ['-checked_in_at']
        verbose_name = _("Check-in de Sesión")
        verbose_name_plural = _("Check-ins de Sesiones")
    
    def __str__(self):
        return f"{self.client} → {self.session} ({self.get_method_display()})"


class ScheduleSettings(models.Model):
    """
    Configuración del sistema de horarios y programación de clases.
    Controla validaciones y restricciones para evitar conflictos.
    """
    gym = models.OneToOneField(
        Gym,
        on_delete=models.CASCADE,
        related_name='schedule_settings',
        verbose_name=_("Gimnasio")
    )
    
    # === VALIDACIONES DE CONFLICTOS ===
    allow_room_overlaps = models.BooleanField(
        default=False,
        verbose_name=_("Permitir solapamiento de salas"),
        help_text=_("Si está desactivado, no se podrán crear clases simultáneas en la misma sala")
    )
    
    allow_staff_overlaps = models.BooleanField(
        default=False,
        verbose_name=_("Permitir solapamiento de instructores"),
        help_text=_("Si está desactivado, un instructor no podrá impartir dos clases a la vez")
    )
    
    min_break_between_classes = models.IntegerField(
        default=0,
        verbose_name=_("Descanso mínimo entre clases (minutos)"),
        help_text=_("Tiempo mínimo que debe pasar entre dos clases del mismo instructor")
    )
    
    max_consecutive_classes = models.IntegerField(
        default=0,
        verbose_name=_("Máximo de clases consecutivas"),
        help_text=_("Número máximo de clases seguidas que puede impartir un instructor (0 = sin límite)")
    )
    
    # === NOTA: Las políticas de reservas, cancelaciones y listas de espera ===
    # === se gestionan por actividad a través del modelo ActivityPolicy ===
    
    # === NOTIFICACIONES ===
    notify_class_changes = models.BooleanField(
        default=True,
        verbose_name=_("Notificar cambios de clases"),
        help_text=_("Enviar notificaciones cuando se modifica o cancela una clase")
    )
    
    reminder_hours_before = models.IntegerField(
        default=2,
        verbose_name=_("Recordatorio (horas antes)"),
        help_text=_("Enviar recordatorio X horas antes de la clase (0 = desactivado)")
    )
    
    # === RESTRICCIONES DE HORARIO ===
    enforce_opening_hours = models.BooleanField(
        default=True,
        verbose_name=_("Respetar horario de apertura"),
        help_text=_("Las clases deben estar dentro del horario de apertura del gimnasio")
    )
    
    # Horario de operación para clases
    schedule_start_time = models.TimeField(
        default='07:00',
        verbose_name=_("Hora inicio de clases"),
        help_text=_("Hora más temprana para programar clases")
    )
    
    schedule_end_time = models.TimeField(
        default='22:00',
        verbose_name=_("Hora fin de clases"),
        help_text=_("Hora más tardía para que terminen las clases")
    )
    
    # Intervalo de tiempo para el calendario
    calendar_slot_minutes = models.IntegerField(
        default=30,
        verbose_name=_("Intervalo de calendario (minutos)"),
        help_text=_("Duración de cada slot en el calendario (15, 30, 60 min)")
    )
    
    # Validar festivos
    block_holidays = models.BooleanField(
        default=True,
        verbose_name=_("Bloquear clases en festivos"),
        help_text=_("No permitir crear clases en días marcados como festivos cerrados")
    )
    
    # Check-in
    allow_late_checkin = models.BooleanField(
        default=True,
        verbose_name=_("Permitir check-in tardío"),
        help_text=_("Permitir check-in después de que haya empezado la clase")
    )
    
    late_checkin_grace_minutes = models.IntegerField(
        default=10,
        verbose_name=_("Minutos de gracia para llegar tarde"),
        help_text=_("Cuántos minutos después del inicio se permite el check-in")
    )
    
    # === METADATOS ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Configuración de Horarios")
        verbose_name_plural = _("Configuraciones de Horarios")
        permissions = [
            ("access_schedule_settings", "Acceder a Configuración de Horarios"),
            ("modify_schedule_settings", "Modificar Configuración de Horarios"),
        ]
        
    def __str__(self):
        return f"Configuración de horarios - {self.gym.name}"
    
    @classmethod
    def get_for_gym(cls, gym):
        """Obtener o crear configuración para un gimnasio"""
        config, created = cls.objects.get_or_create(gym=gym)
        return config
