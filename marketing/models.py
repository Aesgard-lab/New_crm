from django.db import models
from django.utils.translation import gettext_lazy as _
from organizations.models import Gym
from django.utils import timezone


# =============================================================================
# SAVED AUDIENCES (Audiencias Guardadas Reutilizables)
# =============================================================================

class SavedAudience(models.Model):
    """
    Audiencias guardadas que pueden reutilizarse en Campañas, Popups, Anuncios.
    Permite tanto audiencias dinámicas (basadas en filtros) como estáticas (lista de clientes).
    """
    
    class AudienceType(models.TextChoices):
        DYNAMIC = 'DYNAMIC', _('Dinámica (filtros)')
        STATIC = 'STATIC', _('Estática (lista fija)')
        MIXED = 'MIXED', _('Mixta (filtros + exclusiones)')
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='saved_audiences')
    name = models.CharField(max_length=255, verbose_name=_('Nombre'))
    description = models.TextField(blank=True, verbose_name=_('Descripción'))
    
    audience_type = models.CharField(
        max_length=20, 
        choices=AudienceType.choices, 
        default=AudienceType.DYNAMIC,
        verbose_name=_('Tipo de audiencia')
    )
    
    # Filtros dinámicos (guardados como JSON)
    filters = models.JSONField(
        default=dict, 
        blank=True,
        help_text=_('Filtros para audiencia dinámica: {status, gender, age_min, age_max, membership_plan, tags, etc.}')
    )
    
    # Miembros estáticos (para audiencias manuales)
    static_members = models.ManyToManyField(
        'clients.Client',
        blank=True,
        related_name='static_audiences',
        verbose_name=_('Miembros estáticos')
    )
    
    # Exclusiones (clientes a excluir siempre)
    excluded_members = models.ManyToManyField(
        'clients.Client',
        blank=True,
        related_name='excluded_from_audiences',
        verbose_name=_('Clientes excluidos')
    )
    
    # Metadatos
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_audiences'
    )
    
    # Cache del conteo (se actualiza periódicamente)
    _cached_count = models.IntegerField(default=0, db_column='cached_count')
    _count_updated_at = models.DateTimeField(null=True, blank=True, db_column='count_updated_at')
    
    class Meta:
        verbose_name = _('Audiencia guardada')
        verbose_name_plural = _('Audiencias guardadas')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_members_count()} clientes)"
    
    def get_members_queryset(self):
        """
        Devuelve el QuerySet de clientes que pertenecen a esta audiencia.
        Soporta filtros múltiples (listas) y filtros simples para compatibilidad.
        """
        from clients.models import Client, ClientGroup
        from django.db.models import Q
        
        if self.audience_type == self.AudienceType.STATIC:
            # Solo miembros estáticos
            qs = self.static_members.all()
        else:
            # Audiencia dinámica basada en filtros
            qs = Client.objects.filter(gym=self.gym)
            
            filters = self.filters or {}
            
            # Filtros múltiples (nuevo formato: listas)
            # Estado (múltiple)
            if filters.get('statuses'):
                statuses = filters['statuses'] if isinstance(filters['statuses'], list) else [filters['statuses']]
                qs = qs.filter(status__in=statuses)
            # Compatibilidad con formato antiguo (single)
            elif filters.get('status') and filters['status'] != 'all':
                qs = qs.filter(status=filters['status'])
            
            # Género (múltiple)
            if filters.get('genders'):
                genders = filters['genders'] if isinstance(filters['genders'], list) else [filters['genders']]
                qs = qs.filter(gender__in=genders)
            elif filters.get('gender') and filters['gender'] != 'all':
                qs = qs.filter(gender=filters['gender'])
            
            # Planes de membresía (múltiple)
            if filters.get('membership_plans'):
                plan_ids = filters['membership_plans'] if isinstance(filters['membership_plans'], list) else [filters['membership_plans']]
                qs = qs.filter(memberships__plan_id__in=plan_ids).distinct()
            elif filters.get('membership_plan') and filters['membership_plan'] != 'all':
                qs = qs.filter(
                    memberships__plan_id=filters['membership_plan'],
                    memberships__status='ACTIVE'
                ).distinct()
            
            # Servicios (múltiple)
            if filters.get('services'):
                from services.models import Service
                service_ids = filters['services'] if isinstance(filters['services'], list) else [filters['services']]
                service_names = list(Service.objects.filter(id__in=service_ids).values_list('name', flat=True))
                q_services = Q()
                for name in service_names:
                    q_services |= Q(visits__concept__icontains=name)
                if q_services:
                    qs = qs.filter(q_services).distinct()
            elif filters.get('service') and filters['service'] != 'all':
                qs = qs.filter(
                    orders__items__service_id=filters['service']
                ).distinct()
            
            # Productos (múltiple)
            if filters.get('products'):
                from products.models import Product
                product_ids = filters['products'] if isinstance(filters['products'], list) else [filters['products']]
                product_names = list(Product.objects.filter(id__in=product_ids).values_list('name', flat=True))
                q_products = Q()
                for name in product_names:
                    q_products |= Q(sales__concept__icontains=name)
                if q_products:
                    qs = qs.filter(q_products).distinct()
            
            # Grupos (múltiple)
            if filters.get('groups'):
                group_ids = filters['groups'] if isinstance(filters['groups'], list) else [filters['groups']]
                qs = qs.filter(groups__id__in=group_ids).distinct()
            
            # Tags (múltiple)
            if filters.get('tags'):
                tag_ids = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
                qs = qs.filter(tags__id__in=tag_ids).distinct()
            
            # Origen de alta (múltiple)
            if filters.get('created_from'):
                created_from = filters['created_from'] if isinstance(filters['created_from'], list) else [filters['created_from']]
                qs = qs.filter(extra_data__created_from__in=created_from)
            
            # Filtros simples (edad)
            if filters.get('age_min'):
                from datetime import date
                from dateutil.relativedelta import relativedelta
                max_birth = date.today() - relativedelta(years=int(filters['age_min']))
                qs = qs.filter(birth_date__lte=max_birth)
            
            if filters.get('age_max'):
                from datetime import date
                from dateutil.relativedelta import relativedelta
                min_birth = date.today() - relativedelta(years=int(filters['age_max']) + 1)
                qs = qs.filter(birth_date__gt=min_birth)
            
            if filters.get('has_active_membership'):
                qs = qs.filter(memberships__status='ACTIVE').distinct()
            
            if filters.get('is_inactive'):
                qs = qs.exclude(memberships__status='ACTIVE')
            
            if filters.get('company') == 'company':
                qs = qs.filter(is_company_client=True)
            elif filters.get('company') == 'individual':
                qs = qs.filter(is_company_client=False)
            
            # Para audiencia mixta, añadir miembros estáticos
            if self.audience_type == self.AudienceType.MIXED:
                static_ids = self.static_members.values_list('id', flat=True)
                qs = qs | Client.objects.filter(id__in=static_ids)
        
        # Excluir miembros excluidos
        excluded_ids = self.excluded_members.values_list('id', flat=True)
        if excluded_ids:
            qs = qs.exclude(id__in=excluded_ids)
        
        return qs.distinct()
    
    def get_members_count(self, use_cache=True):
        """
        Devuelve el número de clientes en la audiencia.
        """
        # Usar caché si es reciente (menos de 1 hora)
        if use_cache and self._count_updated_at:
            from datetime import timedelta
            if timezone.now() - self._count_updated_at < timedelta(hours=1):
                return self._cached_count
        
        count = self.get_members_queryset().count()
        
        # Actualizar caché
        self._cached_count = count
        self._count_updated_at = timezone.now()
        SavedAudience.objects.filter(pk=self.pk).update(
            _cached_count=count,
            _count_updated_at=self._count_updated_at
        )
        
        return count
    
    def get_filters_display(self):
        """
        Devuelve una descripción legible de los filtros aplicados.
        """
        if not self.filters:
            return "Sin filtros"
        
        parts = []
        filters = self.filters
        
        if filters.get('status') and filters['status'] != 'all':
            status_map = {
                'ACTIVE': 'Activos',
                'INACTIVE': 'Inactivos', 
                'LEAD': 'Prospectos',
                'PAUSED': 'En pausa',
                'BLOCKED': 'Bloqueados'
            }
            parts.append(status_map.get(filters['status'], filters['status']))
        
        if filters.get('gender') and filters['gender'] != 'all':
            gender_map = {'M': 'Hombres', 'F': 'Mujeres', 'O': 'Otro'}
            parts.append(gender_map.get(filters['gender'], filters['gender']))
        
        if filters.get('age_min') or filters.get('age_max'):
            age_str = f"{filters.get('age_min', '0')}-{filters.get('age_max', '∞')} años"
            parts.append(age_str)
        
        if filters.get('has_active_membership'):
            parts.append("Con cuota activa")
        
        if filters.get('is_inactive'):
            parts.append("Sin cuota activa")
        
        return ", ".join(parts) if parts else "Todos los clientes"


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
        SAVED_AUDIENCE = 'SAVED_AUDIENCE', _('Audiencia Guardada')

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='campaigns')
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    audience_type = models.CharField(max_length=50, choices=AudienceType.choices, default=AudienceType.ALL_ACTIVE)
    audience_filter_value = models.CharField(max_length=255, blank=True, null=True, help_text="Tag name or specific filter ID")
    
    # Referencia a audiencia guardada
    saved_audience = models.ForeignKey(
        'SavedAudience',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='campaigns',
        verbose_name=_('Audiencia guardada')
    )
    
    scheduled_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    sent_count = models.IntegerField(default=0)
    open_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # Important for draft saving

    def __str__(self):
        return f"{self.name} ({self.status})"
    
    def get_recipients_queryset(self):
        """
        Devuelve el QuerySet de clientes destinatarios de la campaña.
        """
        from clients.models import Client
        
        # Si usa audiencia guardada
        if self.audience_type == self.AudienceType.SAVED_AUDIENCE and self.saved_audience:
            return self.saved_audience.get_members_queryset()
        
        # Audiencias predefinidas (legacy)
        qs = Client.objects.filter(gym=self.gym)
        
        if self.audience_type == self.AudienceType.ALL_ACTIVE:
            qs = qs.filter(memberships__status='ACTIVE').distinct()
        elif self.audience_type == self.AudienceType.INACTIVE:
            qs = qs.exclude(memberships__status='ACTIVE')
        elif self.audience_type == self.AudienceType.CUSTOM_TAG and self.audience_filter_value:
            qs = qs.filter(tags__name__iexact=self.audience_filter_value).distinct()
        # ALL_CLIENTS: no filter needed
        
        return qs.filter(email__isnull=False).exclude(email='')
    
    def get_recipients_count(self):
        """Devuelve el número de destinatarios."""
        return self.get_recipients_queryset().count()

class Popup(models.Model):
    """
    In-app messages for users.
    """
    class Target(models.TextChoices):
        CLIENTS = 'CLIENTS', _('Clientes')
        STAFF = 'STAFF', _('Staff')
        ALL = 'ALL', _('Todos')
    
    class DisplayFrequency(models.TextChoices):
        ONCE = 'ONCE', _('Solo una vez (cuando marque Entendido)')
        EVERY_SESSION = 'EVERY_SESSION', _('Cada vez que abra la app')
        DAILY = 'DAILY', _('Una vez al día')
        WEEKLY = 'WEEKLY', _('Una vez por semana')

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
    
    # Display Frequency
    display_frequency = models.CharField(
        max_length=20, 
        choices=DisplayFrequency.choices, 
        default=DisplayFrequency.ONCE,
        verbose_name=_('Frecuencia de visualización'),
        help_text=_('Controla cuántas veces se muestra el popup a cada usuario')
    )
    
    # Matching Campaign Audience
    audience_type = models.CharField(max_length=50, choices=Campaign.AudienceType.choices, default=Campaign.AudienceType.ALL_ACTIVE)
    audience_filter_value = models.CharField(max_length=255, blank=True, null=True, help_text="Tag name or specific filter ID")

    # Referencia a audiencia guardada
    saved_audience = models.ForeignKey(
        'SavedAudience',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='popups',
        verbose_name=_('Audiencia guardada')
    )

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
    Supports different display frequencies by tracking last seen time.
    """
    popup = models.ForeignKey(Popup, on_delete=models.CASCADE, related_name='reads')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='read_popups')
    seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True, help_text="Updated each time popup is shown again")
    times_seen = models.PositiveIntegerField(default=1, help_text="How many times user has seen this popup")

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
    
    # Segmentación por gimnasios
    target_gyms = models.ManyToManyField(
        Gym,
        blank=True,
        related_name='targeted_ads',
        help_text="Dejar vacío para todos los gimnasios de la franquicia"
    )
    
    # Segmentación por audiencia (igual que Popup)
    audience_type = models.CharField(
        max_length=50,
        choices=Campaign.AudienceType.choices,
        default=Campaign.AudienceType.ALL_ACTIVE,
        help_text="Tipo de audiencia objetivo"
    )
    audience_filter_value = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Tag o filtro específico según tipo de audiencia"
    )
    
    # Referencia a audiencia guardada
    saved_audience = models.ForeignKey(
        'SavedAudience',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='advertisements',
        verbose_name=_('Audiencia guardada')
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
    description = models.TextField(blank=True, help_text="Descripción de la etapa")
    order = models.IntegerField(default=0)
    color = models.CharField(max_length=7, default='#6366f1')  # Indigo
    monthly_quota = models.IntegerField(default=0, help_text="Monthly goal (0 = no quota)")
    is_won = models.BooleanField(default=False, help_text="Mark this as the 'Converted' stage")
    is_lost = models.BooleanField(default=False, help_text="Mark this as the 'Lost' stage")
    # Servicios y planes asociados a esta etapa (cuando se convierte)
    required_services = models.ManyToManyField(
        'services.Service',
        blank=True,
        related_name='lead_stages',
        help_text="Servicios que debe contratar el lead en esta etapa"
    )
    required_plans = models.ManyToManyField(
        'memberships.MembershipPlan',
        blank=True,
        related_name='lead_stages',
        help_text="Planes de membresía asociados a esta etapa"
    )
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
    Supports time-based rules, action-based rules, and inactivity rules.
    """
    class TriggerType(models.TextChoices):
        # Action-based triggers (positive)
        FIRST_VISIT = 'FIRST_VISIT', _('Primera Visita Realizada')
        MEMBERSHIP_CREATED = 'MEMBERSHIP_CREATED', _('Membresía Contratada')
        ORDER_CREATED = 'ORDER_CREATED', _('Compra Realizada')
        SERVICE_BOOKED = 'SERVICE_BOOKED', _('Servicio Reservado')
        TRIAL_STARTED = 'TRIAL_STARTED', _('Prueba Iniciada')
        
        # Time-based triggers (negative/timeout)
        DAYS_IN_STAGE = 'DAYS_IN_STAGE', _('Días en esta Fase (timeout)')
        DAYS_NO_RESPONSE = 'DAYS_NO_RESPONSE', _('Días Sin Respuesta')
        DAYS_NO_PURCHASE = 'DAYS_NO_PURCHASE', _('Días Sin Compra')
        DAYS_NO_VISIT = 'DAYS_NO_VISIT', _('Días Sin Visita')
        TRIAL_ENDED = 'TRIAL_ENDED', _('Periodo de Prueba Finalizado')
        
        # Scheduled
        DAYS_INACTIVE = 'DAYS_INACTIVE', _('Días Sin Actividad General')
    
    class ActionType(models.TextChoices):
        MOVE_STAGE = 'MOVE_STAGE', _('Mover a otra fase')
        SEND_EMAIL = 'SEND_EMAIL', _('Enviar email')
        CREATE_TASK = 'CREATE_TASK', _('Crear tarea para comercial')
        NOTIFY_STAFF = 'NOTIFY_STAFF', _('Notificar al equipo')
    
    name = models.CharField(max_length=100, blank=True, help_text="Nombre descriptivo de la regla")
    from_stage = models.ForeignKey(
        LeadStage, 
        on_delete=models.CASCADE, 
        related_name='automations_from',
        help_text="Fase origen (donde está el lead)"
    )
    to_stage = models.ForeignKey(
        LeadStage, 
        on_delete=models.CASCADE, 
        related_name='automations_to',
        null=True,
        blank=True,
        help_text="Fase destino (a donde mover el lead)"
    )
    trigger_type = models.CharField(max_length=50, choices=TriggerType.choices)
    trigger_days = models.IntegerField(
        default=0,
        help_text="Días para triggers basados en tiempo (0 = inmediato)"
    )
    action_type = models.CharField(
        max_length=20, 
        choices=ActionType.choices, 
        default='MOVE_STAGE'
    )
    # Para acciones de email
    email_template = models.ForeignKey(
        'EmailTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stage_automations',
        help_text="Plantilla de email a enviar (si la acción es SEND_EMAIL)"
    )
    # Para notificaciones
    notify_message = models.TextField(
        blank=True,
        help_text="Mensaje de notificación (si la acción es NOTIFY_STAFF)"
    )
    # Control
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Mayor prioridad se ejecuta primero")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Regla de Automatización")
        verbose_name_plural = _("Reglas de Automatización")
        ordering = ['-priority', 'from_stage__order']

    def __str__(self):
        if self.name:
            return self.name
        return f"{self.from_stage.name} → {self.to_stage.name if self.to_stage else 'N/A'} ({self.get_trigger_type_display()})"
    
    def get_trigger_description(self):
        """Returns a human-readable description of the trigger."""
        if self.trigger_days > 0:
            return f"{self.get_trigger_type_display()} ({self.trigger_days} días)"
        return self.get_trigger_type_display()


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
        FACEBOOK = 'FACEBOOK', _('Facebook Lead Ads')
        INSTAGRAM = 'INSTAGRAM', _('Instagram Lead Ads')
        GOOGLE = 'GOOGLE', _('Google Ads')
        PHONE = 'PHONE', _('Llamada Telefónica')
        EMAIL = 'EMAIL', _('Email')
        EVENT = 'EVENT', _('Evento/Feria')
        PARTNER = 'PARTNER', _('Partner/Colaborador')
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


# =============================================================================
# META (FACEBOOK/INSTAGRAM) LEAD ADS INTEGRATION
# =============================================================================

class MetaLeadIntegration(models.Model):
    """
    Configuración de integración con Meta (Facebook/Instagram) Lead Ads.
    Permite recibir leads automáticamente desde formularios de Facebook e Instagram.
    """
    gym = models.OneToOneField(Gym, on_delete=models.CASCADE, related_name='meta_integration')
    
    # OAuth Credentials
    app_id = models.CharField(max_length=100, blank=True, help_text="Meta App ID")
    app_secret = models.CharField(max_length=255, blank=True, help_text="Meta App Secret (encriptado)")
    access_token = models.TextField(blank=True, help_text="Page Access Token (long-lived)")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Page Info
    page_id = models.CharField(max_length=100, blank=True, help_text="Facebook Page ID")
    page_name = models.CharField(max_length=255, blank=True)
    instagram_business_account_id = models.CharField(max_length=100, blank=True)
    
    # Configuration
    is_active = models.BooleanField(default=False)
    auto_create_lead = models.BooleanField(default=True, help_text="Crear lead automáticamente al recibir")
    default_stage = models.ForeignKey(
        LeadStage, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Etapa inicial para leads de Meta"
    )
    
    # Webhook
    webhook_verify_token = models.CharField(max_length=100, blank=True, help_text="Token de verificación del webhook")
    webhook_url = models.CharField(max_length=500, blank=True, help_text="URL del webhook (auto-generada)")
    
    # Stats
    leads_received = models.IntegerField(default=0)
    last_lead_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Meta Lead Integration")
        verbose_name_plural = _("Meta Lead Integrations")

    def __str__(self):
        status = "✓ Conectado" if self.is_active and self.access_token else "✗ No conectado"
        return f"Meta Integration - {self.gym.name} ({status})"
    
    def is_connected(self):
        """Check if the integration is properly connected."""
        return bool(self.is_active and self.access_token and self.page_id)
    
    def save(self, *args, **kwargs):
        # Generate webhook verify token if not set
        if not self.webhook_verify_token:
            import secrets
            self.webhook_verify_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class MetaLeadForm(models.Model):
    """
    Formularios de lead ads vinculados desde Meta.
    Un Page puede tener múltiples formularios.
    """
    integration = models.ForeignKey(MetaLeadIntegration, on_delete=models.CASCADE, related_name='lead_forms')
    form_id = models.CharField(max_length=100, unique=True)
    form_name = models.CharField(max_length=255)
    
    # Configuration específica por formulario
    is_active = models.BooleanField(default=True)
    target_stage = models.ForeignKey(
        LeadStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Etapa específica para este formulario (override default)"
    )
    assign_to = models.ForeignKey(
        'staff.StaffProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Asignar automáticamente a este vendedor"
    )
    
    # Field mapping (JSON)
    field_mapping = models.JSONField(
        default=dict,
        blank=True,
        help_text="Mapeo de campos del formulario Meta a campos del lead"
    )
    
    # Stats
    leads_received = models.IntegerField(default=0)
    last_lead_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Meta Lead Form")
        verbose_name_plural = _("Meta Lead Forms")

    def __str__(self):
        return f"{self.form_name} ({self.form_id})"


class MetaLeadEntry(models.Model):
    """
    Registro de cada lead recibido desde Meta.
    Guarda los datos raw y el estado del procesamiento.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pendiente')
        PROCESSED = 'PROCESSED', _('Procesado')
        ERROR = 'ERROR', _('Error')
        DUPLICATE = 'DUPLICATE', _('Duplicado')
    
    integration = models.ForeignKey(MetaLeadIntegration, on_delete=models.CASCADE, related_name='lead_entries')
    form = models.ForeignKey(MetaLeadForm, on_delete=models.SET_NULL, null=True, blank=True, related_name='entries')
    
    # Meta Lead Data
    leadgen_id = models.CharField(max_length=100, unique=True, help_text="Meta Lead ID")
    ad_id = models.CharField(max_length=100, blank=True)
    ad_name = models.CharField(max_length=255, blank=True)
    campaign_id = models.CharField(max_length=100, blank=True)
    campaign_name = models.CharField(max_length=255, blank=True)
    
    # Raw data from webhook
    raw_data = models.JSONField(default=dict)
    
    # Extracted fields
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    
    # Processing
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)
    
    # Link to created lead
    lead_card = models.ForeignKey(LeadCard, on_delete=models.SET_NULL, null=True, blank=True, related_name='meta_entries')
    
    # Platform info
    platform = models.CharField(max_length=20, default='facebook', help_text="facebook or instagram")
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Meta Lead Entry")
        verbose_name_plural = _("Meta Lead Entries")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email}) - {self.get_status_display()}"


# =============================================================================
# LEAD DISTRIBUTION (Asignación Automática de Leads)
# =============================================================================

class LeadDistributionRule(models.Model):
    """
    Reglas de distribución automática de leads entre vendedores.
    Soporta Round-Robin, carga balanceada, y asignación por fuente.
    """
    class DistributionMethod(models.TextChoices):
        ROUND_ROBIN = 'ROUND_ROBIN', _('Round Robin (rotación)')
        LOAD_BALANCED = 'LOAD_BALANCED', _('Balanceado por Carga')
        RANDOM = 'RANDOM', _('Aleatorio')
        FIXED = 'FIXED', _('Asignación Fija')
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='lead_distribution_rules')
    name = models.CharField(max_length=100)
    
    # Distribution method
    method = models.CharField(max_length=20, choices=DistributionMethod.choices, default=DistributionMethod.ROUND_ROBIN)
    
    # Source filter (None = all sources)
    source_filter = models.CharField(
        max_length=30,
        blank=True,
        help_text="Solo aplicar a leads de esta fuente (vacío = todas)"
    )
    
    # Staff pool
    staff_members = models.ManyToManyField(
        'staff.StaffProfile',
        related_name='distribution_rules',
        help_text="Vendedores que participan en la distribución"
    )
    
    # For round-robin tracking
    current_index = models.IntegerField(default=0)
    
    # Limits
    max_leads_per_day = models.IntegerField(default=0, help_text="Máximo leads por vendedor por día (0 = sin límite)")
    max_active_leads = models.IntegerField(default=0, help_text="Máximo leads activos por vendedor (0 = sin límite)")
    
    # Notifications
    notify_on_assignment = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Mayor prioridad se evalúa primero")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = _("Lead Distribution Rule")
        verbose_name_plural = _("Lead Distribution Rules")

    def __str__(self):
        return f"{self.name} ({self.get_method_display()})"
    
    def get_next_assignee(self):
        """Get the next staff member based on distribution method."""
        active_staff = list(self.staff_members.filter(is_active=True))
        
        if not active_staff:
            return None
        
        if self.method == self.DistributionMethod.ROUND_ROBIN:
            # Simple round-robin
            assignee = active_staff[self.current_index % len(active_staff)]
            self.current_index = (self.current_index + 1) % len(active_staff)
            self.save(update_fields=['current_index'])
            return assignee
        
        elif self.method == self.DistributionMethod.LOAD_BALANCED:
            # Assign to staff with fewest active leads
            from django.db.models import Count
            staff_with_counts = []
            for staff in active_staff:
                active_leads = LeadCard.objects.filter(
                    assigned_to=staff,
                    stage__is_won=False,
                    stage__is_lost=False
                ).count()
                staff_with_counts.append((staff, active_leads))
            
            # Sort by lead count (ascending)
            staff_with_counts.sort(key=lambda x: x[1])
            return staff_with_counts[0][0] if staff_with_counts else None
        
        elif self.method == self.DistributionMethod.RANDOM:
            import random
            return random.choice(active_staff)
        
        elif self.method == self.DistributionMethod.FIXED:
            # Just return the first active staff
            return active_staff[0] if active_staff else None
        
        return None


class LeadAssignmentLog(models.Model):
    """
    Log de asignaciones de leads para tracking y auditoría.
    """
    lead_card = models.ForeignKey(LeadCard, on_delete=models.CASCADE, related_name='assignment_logs')
    assigned_to = models.ForeignKey('staff.StaffProfile', on_delete=models.SET_NULL, null=True)
    assigned_by = models.ForeignKey(
        'staff.StaffProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assignments_made'
    )
    rule = models.ForeignKey(
        LeadDistributionRule, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Regla que realizó la asignación automática"
    )
    
    # Assignment details
    assignment_type = models.CharField(
        max_length=20,
        choices=[
            ('AUTO', 'Automática'),
            ('MANUAL', 'Manual'),
            ('REASSIGN', 'Reasignación'),
        ],
        default='MANUAL'
    )
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Lead Assignment Log")
        verbose_name_plural = _("Lead Assignment Logs")

    def __str__(self):
        return f"{self.lead_card.client} → {self.assigned_to} ({self.assignment_type})"


# =============================================================================
# SALES FUNNEL ANALYTICS (Histórico para reportes)
# =============================================================================

class LeadStageHistory(models.Model):
    """
    Historial de movimientos de leads entre etapas.
    Permite calcular tiempos de conversión y tasas por etapa.
    """
    lead_card = models.ForeignKey(LeadCard, on_delete=models.CASCADE, related_name='stage_history')
    from_stage = models.ForeignKey(LeadStage, on_delete=models.SET_NULL, null=True, blank=True, related_name='history_from')
    to_stage = models.ForeignKey(LeadStage, on_delete=models.SET_NULL, null=True, related_name='history_to')
    
    # Who/what made the change
    changed_by = models.ForeignKey('staff.StaffProfile', on_delete=models.SET_NULL, null=True, blank=True)
    changed_by_automation = models.ForeignKey(LeadStageAutomation, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Time tracking
    time_in_previous_stage = models.DurationField(null=True, blank=True, help_text="Tiempo que estuvo en la etapa anterior")
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Lead Stage History")
        verbose_name_plural = _("Lead Stage Histories")

    def __str__(self):
        from_name = self.from_stage.name if self.from_stage else "Nueva entrada"
        to_name = self.to_stage.name if self.to_stage else "Eliminado"
        return f"{self.lead_card.client}: {from_name} → {to_name}"

