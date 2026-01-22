from django.db import models
from django.utils.translation import gettext_lazy as _
from organizations.models import Gym
from django.utils import timezone


class MarketingSettings(models.Model):
    """
    SMTP and general marketing configuration per Gym.
    Contraseñas cifradas usando Fernet para seguridad.
    """
    gym = models.OneToOneField(Gym, on_delete=models.CASCADE, related_name='marketing_settings')
    
    # SMTP Configuration
    smtp_host = models.CharField(max_length=255, default='smtp.gmail.com')
    smtp_port = models.IntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True)
    _smtp_password_encrypted = models.CharField(max_length=512, blank=True, db_column='smtp_password')
    smtp_use_tls = models.BooleanField(default=True)
    default_sender_email = models.EmailField(help_text="From address for emails")
    default_sender_name = models.CharField(max_length=255, default="Mi Gimnasio")
    
    # Branding
    header_logo = models.ImageField(upload_to='marketing/logos/', blank=True, null=True)
    footer_text = models.TextField(blank=True, help_text="HTML allowed")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def smtp_password(self):
        """Descifra la contraseña SMTP"""
        if not self._smtp_password_encrypted:
            return ''
        try:
            from core.security_utils import decrypt_value
            return decrypt_value(self._smtp_password_encrypted) or ''
        except Exception:
            return ''
    
    @smtp_password.setter
    def smtp_password(self, value):
        """Cifra la contraseña SMTP antes de guardar"""
        if value:
            from core.security_utils import encrypt_value
            self._smtp_password_encrypted = encrypt_value(value)
        else:
            self._smtp_password_encrypted = ''

    def __str__(self):
        return f"Marketing Settings for {self.gym.name}"

class EmailTemplate(models.Model):
    """
    Drag & Drop Email Templates.
    Stores both the raw JSON (for the builder) and compiled HTML (for sending).
    """
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='email_templates')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # GrapesJS/Internal format
    content_json = models.JSONField(default=dict, blank=True) 
    # Compiled HTML
    content_html = models.TextField(blank=True)
    
    thumbnail = models.ImageField(upload_to='marketing/thumbnails/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Borrador')
        SCHEDULED = 'SCHEDULED', _('Programada')
        SENDING = 'SENDING', _('Enviando')
        SENT = 'SENT', _('Enviada')
        FAILED = 'FAILED', _('Fallida')

    class AudienceType(models.TextChoices):
        ALL_ACTIVE = 'ALL_ACTIVE', _('Todos los Activos')
        ALL_CLIENTS = 'ALL_CLIENTS', _('Todos los Clientes')
        INACTIVE = 'INACTIVE', _('Inactivos/Expirados')
        STAFF = 'STAFF', _('Staff')
        CUSTOM_TAG = 'CUSTOM_TAG', _('Etiqueta Personalizada')

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='campaigns')
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    audience_type = models.CharField(max_length=50, choices=AudienceType.choices, default=AudienceType.ALL_ACTIVE)
    audience_filter_value = models.CharField(max_length=255, blank=True, null=True, help_text="Tag name or specific filter ID")
    
    scheduled_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    sent_count = models.IntegerField(default=0)
    open_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # Important for draft saving

    def __str__(self):
        return f"{self.name} ({self.status})"

class Popup(models.Model):
    """
    In-app messages for users.
    """
    class Target(models.TextChoices):
        CLIENTS = 'CLIENTS', _('Clientes')
        STAFF = 'STAFF', _('Staff')
        ALL = 'ALL', _('Todos')

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='popups')
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="HTML content allowed")
    image = models.ImageField(upload_to='marketing/popups/', blank=True, null=True)
    
    # Priority
    PRIORITY_CHOICES = [
        ('INFO', _('Informativo')),
        ('WARNING', _('Aviso Important')),
        ('URGENT', _('Urgente')),
    ]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='INFO')
    
    # Matching Campaign Audience
    audience_type = models.CharField(max_length=50, choices=Campaign.AudienceType.choices, default=Campaign.AudienceType.ALL_ACTIVE)
    audience_filter_value = models.CharField(max_length=255, blank=True, null=True, help_text="Tag name or specific filter ID")

    # Direct Individual Targeting
    target_client = models.ForeignKey(
        'clients.Client', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='targeted_popups',
        help_text="Si se selecciona, este popup solo se mostrará a este cliente específico"
    )

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_priority_display()})"


class PopupRead(models.Model):
    """
    Tracks which users have seen/closed which specific popup.
    """
    popup = models.ForeignKey(Popup, on_delete=models.CASCADE, related_name='reads')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='read_popups')
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('popup', 'client')

    def __str__(self):
        return f"{self.client} read {self.popup}"


# =============================================================================
# ADVERTISEMENTS / BANNERS (Sistema de anuncios publicitarios)
# =============================================================================

class Advertisement(models.Model):
    """
    Anuncios publicitarios / Carteles para mostrar en la app del cliente.
    DIFERENTE del sistema de Popups: estos son banners fijos en ubicaciones específicas.
    """
    
    class ScreenType(models.TextChoices):
        ALL = 'ALL', _('Todas las Pantallas')
        HOME = 'HOME', _('Inicio/Dashboard')
        CLASS_CATALOG = 'CLASS_CATALOG', _('Catálogo de Clases')
        CLASS_DETAIL = 'CLASS_DETAIL', _('Detalle de Clase')
        PROFILE = 'PROFILE', _('Mi Perfil')
        BOOKINGS = 'BOOKINGS', _('Mis Reservas')
        SHOP = 'SHOP', _('Tienda')
        CHECKIN = 'CHECKIN', _('Check-in')
        SETTINGS = 'SETTINGS', _('Configuración')
    
    class PositionType(models.TextChoices):
        HERO_CAROUSEL = 'HERO_CAROUSEL', _('Hero Carousel (Home)')
        STICKY_FOOTER = 'STICKY_FOOTER', _('Banner Inferior Fijo')
        INLINE_MIDDLE = 'INLINE_MIDDLE', _('Banner Intermedio')
        STORIES = 'STORIES', _('Stories Verticales')
    
    class AdType(models.TextChoices):
        INTERNAL_PROMO = 'INTERNAL_PROMO', _('Promoción Interna')
        SPONSOR = 'SPONSOR', _('Sponsor/Partner')
        CROSS_SELL = 'CROSS_SELL', _('Cross-selling')
        EDUCATIONAL = 'EDUCATIONAL', _('Contenido Educativo')
    
    class ActionType(models.TextChoices):
        NONE = 'NONE', _('Sin acción')
        BOOK_CLASS = 'BOOK_CLASS', _('Reservar Clase')
        VIEW_CATALOG = 'VIEW_CATALOG', _('Ver Catálogo')
        EXTERNAL_URL = 'EXTERNAL_URL', _('URL Externa')
        VIEW_PROMO = 'VIEW_PROMO', _('Ver Promoción')
    
    # Basics
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='advertisements')
    title = models.CharField(max_length=255, help_text="Título interno (no se muestra al cliente)")
    
    # Positioning
    position = models.CharField(
        max_length=50,
        choices=PositionType.choices,
        default=PositionType.HERO_CAROUSEL,
        help_text="Ubicación del anuncio en la app"
    )
    ad_type = models.CharField(
        max_length=50,
        choices=AdType.choices,
        default=AdType.INTERNAL_PROMO
    )
    
    # Media
    image_desktop = models.ImageField(
        upload_to='marketing/advertisements/desktop/',
        help_text="1080x600px recomendado para carousel hero"
    )
    image_mobile = models.ImageField(
        upload_to='marketing/advertisements/mobile/',
        blank=True,
        null=True,
        help_text="Si está vacío, se usa image_desktop"
    )
    video_url = models.URLField(blank=True, null=True, help_text="URL de video (opcional)")
    
    # CTA (Call to Action)
    cta_text = models.CharField(
        max_length=100,
        blank=True,
        help_text="Texto del botón (ej: '¡Reserva Ahora!')"
    )
    cta_action = models.CharField(
        max_length=50,
        choices=ActionType.choices,
        default=ActionType.NONE
    )
    cta_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL o parámetro según la acción (ej: clase_id, producto_id, url externa)"
    )
    
    # Segmentación (Fase 1: básica)
    target_gyms = models.ManyToManyField(
        Gym,
        blank=True,
        related_name='targeted_ads',
        help_text="Dejar vacío para todos los gimnasios de la franquicia"
    )
    
    # Segmentación por pantallas
    target_screens = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de pantallas donde mostrar el anuncio. Vacío = todas las pantallas. Ej: ['HOME', 'CLASS_CATALOG']"
    )
    
    # Programación
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True, help_text="Dejar vacío para indefinido")
    
    # Configuración de visualización
    priority = models.IntegerField(
        default=1,
        help_text="Orden en carrusel (menor = primero)"
    )
    duration_seconds = models.IntegerField(
        default=5,
        help_text="Segundos que se muestra en carrusel"
    )
    is_collapsible = models.BooleanField(
        default=True,
        help_text="Permitir cerrar/ocultar (para sticky footer)"
    )
    is_active = models.BooleanField(default=True)
    
    # Analytics (Fase 2+)
    impressions = models.IntegerField(default=0, help_text="Número de veces mostrado")
    clicks = models.IntegerField(default=0, help_text="Número de clicks en CTA")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_advertisements'
    )
    
    class Meta:
        ordering = ['priority', '-created_at']
        verbose_name = 'Anuncio Publicitario'
        verbose_name_plural = 'Anuncios Publicitarios'
    
    def __str__(self):
        return f"{self.title} ({self.get_position_display()})"
    
    @property
    def ctr(self):
        """Click-through rate"""
        if self.impressions == 0:
            return 0
        return round((self.clicks / self.impressions) * 100, 2)
    
    def is_currently_active(self):
        """Verifica si el anuncio debe mostrarse ahora"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True


class AdvertisementImpression(models.Model):
    """
    Tracking de impresiones individuales (Fase 2+)
    """
    advertisement = models.ForeignKey(
        Advertisement,
        on_delete=models.CASCADE,
        related_name='impression_logs'
    )
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    clicked = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['advertisement', 'timestamp']),
        ]
    
    def __str__(self):
        return f"Impression {self.advertisement} - {self.timestamp}"


# =============================================================================
# LEAD MANAGEMENT
# =============================================================================

class LeadPipeline(models.Model):
    """
    Main pipeline configuration per gym.
    Each gym can have multiple pipelines (e.g., "Sales Pipeline", "Corporate Leads").
    """
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='lead_pipelines')
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.gym.name})"


class LeadStage(models.Model):
    """
    Configurable stages within a pipeline (columns in Kanban).
    Examples: New Lead, Contacted, Trial Started, Converted, Lost
    """
    pipeline = models.ForeignKey(LeadPipeline, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=50)
    order = models.IntegerField(default=0)
    color = models.CharField(max_length=7, default='#6366f1')  # Indigo
    monthly_quota = models.IntegerField(default=0, help_text="Monthly goal (0 = no quota)")
    is_won = models.BooleanField(default=False, help_text="Mark this as the 'Converted' stage")
    is_lost = models.BooleanField(default=False, help_text="Mark this as the 'Lost' stage")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} (Order: {self.order})"
    
    def get_current_month_count(self):
        """Count leads in this stage for the current month."""
        from django.utils import timezone
        today = timezone.now().date()
        first_day = today.replace(day=1)
        return self.lead_cards.filter(updated_at__date__gte=first_day).count()


class LeadStageAutomation(models.Model):
    """
    Configurable automation rules for moving leads between stages.
    """
    class TriggerType(models.TextChoices):
        FIRST_VISIT = 'FIRST_VISIT', _('Primera Visita')
        MEMBERSHIP_CREATED = 'MEMBERSHIP_CREATED', _('Membresía Creada')
        DAYS_INACTIVE = 'DAYS_INACTIVE', _('Días Sin Actividad')
        TRIAL_ENDED = 'TRIAL_ENDED', _('Periodo de Prueba Finalizado')
        ORDER_CREATED = 'ORDER_CREATED', _('Compra Realizada')
    
    from_stage = models.ForeignKey(
        LeadStage, 
        on_delete=models.CASCADE, 
        related_name='automations_from',
        help_text="Source stage"
    )
    to_stage = models.ForeignKey(
        LeadStage, 
        on_delete=models.CASCADE, 
        related_name='automations_to',
        help_text="Destination stage"
    )
    trigger_type = models.CharField(max_length=50, choices=TriggerType.choices)
    trigger_value = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Days for DAYS_INACTIVE trigger"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Lead Automation Rule")
        verbose_name_plural = _("Lead Automation Rules")

    def __str__(self):
        return f"{self.from_stage.name} → {self.to_stage.name} ({self.get_trigger_type_display()})"


class LeadCard(models.Model):
    """
    Represents a lead in the pipeline.
    Links to an existing Client with status=LEAD.
    """
    class Source(models.TextChoices):
        WEB = 'WEB', _('Formulario Web')
        WALKIN = 'WALKIN', _('Walk-in')
        REFERRAL = 'REFERRAL', _('Referido')
        SOCIAL = 'SOCIAL', _('Redes Sociales')
        ADS = 'ADS', _('Publicidad')
        OTHER = 'OTHER', _('Otro')

    client = models.OneToOneField(
        'clients.Client', 
        on_delete=models.CASCADE, 
        related_name='lead_card'
    )
    stage = models.ForeignKey(
        LeadStage, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='lead_cards'
    )
    assigned_to = models.ForeignKey(
        'staff.StaffProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_leads'
    )
    source = models.CharField(
        max_length=20, 
        choices=Source.choices, 
        default=Source.OTHER
    )
    notes = models.TextField(blank=True)
    last_contacted = models.DateTimeField(null=True, blank=True)
    next_followup = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.client} - {self.stage.name if self.stage else 'No Stage'}"


# =============================================================================
# EMAIL WORKFLOWS (Secuencias Automatizadas)
# =============================================================================

class EmailWorkflow(models.Model):
    """
    Secuencia automatizada de emails (Drip Campaign).
    Ej: Bienvenida nueva membresía → Email día 1, 3, 7
    """
    class TriggerEvent(models.TextChoices):
        LEAD_CREATED = 'LEAD_CREATED', _('Lead Creado')
        MEMBERSHIP_CREATED = 'MEMBERSHIP_CREATED', _('Membresía Creada')
        TRIAL_STARTED = 'TRIAL_STARTED', _('Prueba Iniciada')
        FIRST_VISIT = 'FIRST_VISIT', _('Primera Visita')
        INACTIVE_DAYS = 'INACTIVE_DAYS', _('Días Sin Actividad')
        
        # Class/Waitlist Events
        CLASS_BOOKED = 'CLASS_BOOKED', _('Clase Reservada')
        CLASS_CANCELLED = 'CLASS_CANCELLED', _('Clase Cancelada')
        WAITLIST_JOINED = 'WAITLIST_JOINED', _('Añadido a Lista de Espera')
        WAITLIST_SPOT_AVAILABLE = 'WAITLIST_SPOT_AVAILABLE', _('Plaza Disponible')
        WAITLIST_PROMOTED = 'WAITLIST_PROMOTED', _('Promovido a Clase')
        CLASS_REMINDER_24H = 'CLASS_REMINDER_24H', _('Recordatorio 24h Antes')
        CLASS_REMINDER_2H = 'CLASS_REMINDER_2H', _('Recordatorio 2h Antes')
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='email_workflows')
    name = models.CharField(max_length=200, help_text="Ej: Secuencia Bienvenida Nuevos")
    description = models.TextField(blank=True)
    trigger_event = models.CharField(max_length=50, choices=TriggerEvent.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Email Workflow")
        verbose_name_plural = _("Email Workflows")

    def __str__(self):
        return f"{self.name} ({self.get_trigger_event_display()})"


class ClassNotificationSettings(models.Model):
    """
    Configuración de notificaciones automáticas para eventos de clases.
    Controla qué notificaciones se envían automáticamente.
    """
    gym = models.OneToOneField(Gym, on_delete=models.CASCADE, related_name='class_notification_settings')
    
    # Email Notifications
    email_booking_confirmation = models.BooleanField(default=True, verbose_name="Email: Confirmación de reserva")
    email_cancellation_confirmation = models.BooleanField(default=True, verbose_name="Email: Confirmación de cancelación")
    email_waitlist_joined = models.BooleanField(default=True, verbose_name="Email: Añadido a lista de espera")
    email_spot_available = models.BooleanField(default=True, verbose_name="Email: Plaza disponible")
    email_reminder_24h = models.BooleanField(default=True, verbose_name="Email: Recordatorio 24h")
    email_reminder_2h = models.BooleanField(default=False, verbose_name="Email: Recordatorio 2h")
    
    # Popup Notifications (In-App)
    popup_booking_confirmation = models.BooleanField(default=True, verbose_name="Popup: Confirmación de reserva")
    popup_cancellation_confirmation = models.BooleanField(default=True, verbose_name="Popup: Confirmación de cancelación")
    popup_waitlist_joined = models.BooleanField(default=True, verbose_name="Popup: Añadido a lista de espera")
    popup_spot_available = models.BooleanField(default=True, verbose_name="Popup: Plaza disponible")
    popup_promoted = models.BooleanField(default=True, verbose_name="Popup: Promovido a clase")
    
    # Broadcast Waitlist Settings
    waitlist_broadcast_count = models.IntegerField(default=3, verbose_name="Notificar a X personas (Broadcast)", help_text="Cuántas personas notificar simultáneamente cuando se libera una plaza")
    waitlist_claim_timeout_minutes = models.IntegerField(default=15, verbose_name="Tiempo para reclamar (minutos)", help_text="Minutos que tiene el cliente para confirmar la plaza")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración de Notificaciones de Clases"
        verbose_name_plural = "Configuraciones de Notificaciones de Clases"
    
    def __str__(self):
        return f"Notificaciones - {self.gym.name}"


class EmailWorkflowStep(models.Model):
    """
    Paso individual dentro de un workflow.
    Ej: "Email Día 1: Bienvenida", "Email Día 3: Consejos"
    """
    workflow = models.ForeignKey(EmailWorkflow, on_delete=models.CASCADE, related_name='steps')
    order = models.IntegerField(default=0, help_text="Orden de ejecución")
    delay_days = models.IntegerField(default=0, help_text="Días después del trigger o paso anterior")
    
    subject = models.CharField(max_length=255)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Si no hay template, usar contenido directo
    content_html = models.TextField(blank=True, help_text="HTML del email si no usa template")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = _("Workflow Step")
        verbose_name_plural = _("Workflow Steps")

    def __str__(self):
        return f"{self.workflow.name} - Paso {self.order} (Día {self.delay_days})"


class EmailWorkflowExecution(models.Model):
    """
    Rastrea qué clientes están en qué workflow y qué pasos han recibido.
    """
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('En Progreso')
        COMPLETED = 'COMPLETED', _('Completado')
        CANCELLED = 'CANCELLED', _('Cancelado')
    
    workflow = models.ForeignKey(EmailWorkflow, on_delete=models.CASCADE, related_name='executions')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='workflow_executions')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    current_step = models.ForeignKey(EmailWorkflowStep, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_executions')

    class Meta:
        ordering = ['-started_at']
        unique_together = ('workflow', 'client')  # Un cliente solo puede estar una vez en cada workflow

    def __str__(self):
        return f"{self.client} - {self.workflow.name} ({self.status})"


class EmailWorkflowStepLog(models.Model):
    """
    Log de cada email enviado dentro de un workflow.
    """
    execution = models.ForeignKey(EmailWorkflowExecution, on_delete=models.CASCADE, related_name='step_logs')
    step = models.ForeignKey(EmailWorkflowStep, on_delete=models.CASCADE, related_name='logs')
    
    sent_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(help_text="Cuándo debía enviarse")
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    opened = models.BooleanField(default=False)
    opened_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.execution.client} - {self.step} ({'✓' if self.success else '✗'})"


# =============================================================================
# LEAD SCORING
# =============================================================================

class LeadScoringRule(models.Model):
    """
    Reglas configurables para asignar puntos a leads.
    Ej: "Abrió email +5pts", "Visitó +10pts", "No responde -5pts"
    """
    class EventType(models.TextChoices):
        EMAIL_OPENED = 'EMAIL_OPENED', _('Email Abierto')
        EMAIL_CLICKED = 'EMAIL_CLICKED', _('Link en Email Clicado')
        FORM_SUBMITTED = 'FORM_SUBMITTED', _('Formulario Enviado')
        VISIT_REGISTERED = 'VISIT_REGISTERED', _('Visita Registrada')
        CLASS_BOOKED = 'CLASS_BOOKED', _('Clase Reservada')
        RESPONDED_MESSAGE = 'RESPONDED_MESSAGE', _('Respondió Mensaje')
        DAYS_NO_RESPONSE = 'DAYS_NO_RESPONSE', _('Días Sin Respuesta')
        PURCHASE_MADE = 'PURCHASE_MADE', _('Compra Realizada')
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='scoring_rules')
    name = models.CharField(max_length=200, help_text="Ej: Puntos por visita")
    event_type = models.CharField(max_length=50, choices=EventType.choices)
    points = models.IntegerField(help_text="Puede ser negativo para penalizaciones")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Lead Scoring Rule")
        verbose_name_plural = _("Lead Scoring Rules")

    def __str__(self):
        return f"{self.name} ({self.points:+d} pts)"


class LeadScore(models.Model):
    """
    Score actual de cada lead/cliente.
    """
    client = models.OneToOneField('clients.Client', on_delete=models.CASCADE, related_name='lead_score')
    score = models.IntegerField(default=0)
    
    last_positive_event = models.DateTimeField(null=True, blank=True)
    last_negative_event = models.DateTimeField(null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-score']

    def __str__(self):
        return f"{self.client} - {self.score} pts"
    
    def add_points(self, points, event_description=""):
        """Añade puntos y registra el evento."""
        from django.utils import timezone
        self.score += points
        if points > 0:
            self.last_positive_event = timezone.now()
        elif points < 0:
            self.last_negative_event = timezone.now()
        self.save()
        
        # Registrar en historial
        LeadScoreLog.objects.create(
            lead_score=self,
            points=points,
            description=event_description
        )


class LeadScoreLog(models.Model):
    """
    Historial de cambios de score.
    """
    lead_score = models.ForeignKey(LeadScore, on_delete=models.CASCADE, related_name='logs')
    points = models.IntegerField()
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.lead_score.client} - {self.points:+d} pts ({self.description})"


class LeadScoringAutomation(models.Model):
    """
    Acciones automáticas basadas en el score.
    Ej: "Si score >= 70, mover a Hot Leads"
    """
    class ActionType(models.TextChoices):
        MOVE_TO_STAGE = 'MOVE_TO_STAGE', _('Mover a Etapa')
        ASSIGN_TO_STAFF = 'ASSIGN_TO_STAFF', _('Asignar a Vendedor')
        SEND_NOTIFICATION = 'SEND_NOTIFICATION', _('Enviar Notificación')
        START_WORKFLOW = 'START_WORKFLOW', _('Iniciar Workflow')
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='scoring_automations')
    name = models.CharField(max_length=200)
    
    # Condición
    min_score = models.IntegerField(help_text="Score mínimo para activar")
    max_score = models.IntegerField(null=True, blank=True, help_text="Score máximo (dejar vacío para ilimitado)")
    
    # Acción
    action_type = models.CharField(max_length=50, choices=ActionType.choices)
    target_stage = models.ForeignKey(LeadStage, on_delete=models.SET_NULL, null=True, blank=True, help_text="Para acción MOVE_TO_STAGE")
    target_staff = models.ForeignKey('staff.StaffProfile', on_delete=models.SET_NULL, null=True, blank=True, help_text="Para acción ASSIGN_TO_STAFF")
    target_workflow = models.ForeignKey(EmailWorkflow, on_delete=models.SET_NULL, null=True, blank=True, help_text="Para acción START_WORKFLOW")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-min_score']
        verbose_name = _("Lead Scoring Automation")
        verbose_name_plural = _("Lead Scoring Automations")

    def __str__(self):
        return f"{self.name} (Score >= {self.min_score})"


# =============================================================================
# ALERTAS DE RETENCIÓN
# =============================================================================

class RetentionAlert(models.Model):
    """
    Alertas automáticas para clientes en riesgo.
    Ej: "Cliente sin asistir 14 días", "Membresía expira en 7 días"
    """
    class AlertType(models.TextChoices):
        NO_ATTENDANCE = 'NO_ATTENDANCE', _('Sin Asistencia')
        MEMBERSHIP_EXPIRING = 'MEMBERSHIP_EXPIRING', _('Membresía Por Expirar')
        LOW_CLASS_BOOKING = 'LOW_CLASS_BOOKING', _('Pocas Reservas')
        PAYMENT_FAILED = 'PAYMENT_FAILED', _('Fallo en Pago')
        HIGH_CANCELLATION_RATE = 'HIGH_CANCELLATION_RATE', _('Muchas Cancelaciones')
    
    class Status(models.TextChoices):
        OPEN = 'OPEN', _('Abierta')
        IN_PROGRESS = 'IN_PROGRESS', _('En Progreso')
        RESOLVED = 'RESOLVED', _('Resuelta')
        DISMISSED = 'DISMISSED', _('Descartada')
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='retention_alerts')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='retention_alerts')
    
    alert_type = models.CharField(max_length=50, choices=AlertType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Métricas relevantes
    days_inactive = models.IntegerField(null=True, blank=True)
    risk_score = models.IntegerField(default=0, help_text="0-100, donde 100 es alto riesgo")
    
    # Asignación
    assigned_to = models.ForeignKey('staff.StaffProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_retention_alerts')
    
    # Seguimiento
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-risk_score', '-created_at']
        verbose_name = _("Retention Alert")
        verbose_name_plural = _("Retention Alerts")

    def __str__(self):
        return f"{self.client} - {self.get_alert_type_display()} (Riesgo: {self.risk_score})"


class RetentionRule(models.Model):
    """
    Reglas configurables para generar alertas automáticas.
    """
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='retention_rules')
    name = models.CharField(max_length=200)
    alert_type = models.CharField(max_length=50, choices=RetentionAlert.AlertType.choices)
    
    # Condiciones
    days_threshold = models.IntegerField(help_text="Ej: 14 días sin asistencia")
    risk_score = models.IntegerField(default=50, help_text="Score de riesgo 0-100")
    
    # Acciones
    auto_assign_to_staff = models.BooleanField(default=False)
    assigned_staff = models.ForeignKey('staff.StaffProfile', on_delete=models.SET_NULL, null=True, blank=True, help_text="Staff al que asignar automáticamente")
    send_notification = models.BooleanField(default=True)
    start_workflow = models.ForeignKey(EmailWorkflow, on_delete=models.SET_NULL, null=True, blank=True, help_text="Workflow a iniciar automáticamente")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Retention Rule")
        verbose_name_plural = _("Retention Rules")

    def __str__(self):
        return f"{self.name} ({self.days_threshold} días)"

