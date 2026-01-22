from django.db import models
from datetime import time


class Franchise(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    owners = models.ManyToManyField("accounts.User", related_name='franchises_owned', blank=True)
    
    # Cross-booking configuration
    allow_cross_booking = models.BooleanField(
        default=False,
        verbose_name="Permitir reservas cruzadas",
        help_text="Permite a los clientes reservar clases en cualquier gimnasio de la franquicia"
    )

    def __str__(self):
        return self.name


class Gym(models.Model):
    name = models.CharField(max_length=200, help_text="Nombre interno/sistema")
    
    # Branding
    commercial_name = models.CharField(max_length=200, blank=True, help_text="Nombre Comercial (Público)")
    brand_color = models.CharField(max_length=7, default="#0f172a", help_text="Color corporativo en Hex (ej: #0f172a)")
    logo = models.ImageField(upload_to='gym_logos/', blank=True, null=True)
    
    # Fiscal Data (for Invoices)
    legal_name = models.CharField(max_length=200, blank=True, help_text="Razón Social / Nombre de Empresa")
    tax_id = models.CharField(max_length=20, blank=True, help_text="CIF / NIF")
    
    # Contact & Address
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="España", blank=True)
    
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Social Media
    instagram = models.URLField(blank=True, help_text="URL completa (https://instagram.com/...)")
    facebook = models.URLField(blank=True, help_text="URL completa")
    tiktok = models.URLField(blank=True, help_text="URL completa")
    youtube = models.URLField(blank=True, help_text="URL completa")

    # Idioma / Language
    LANGUAGE_CHOICES = [
        ('es', 'Español'),
        ('en', 'English'),
    ]
    language = models.CharField(
        max_length=2, 
        choices=LANGUAGE_CHOICES, 
        default='es',
        help_text="Idioma principal del gimnasio"
    )

    franchise = models.ForeignKey(
        Franchise,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gyms",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("franchise", "name")  # nombre único dentro de una franquicia

    def __str__(self):
        return self.commercial_name or self.name


class GymGoal(models.Model):
    """Objetivos establecidos por los owners para cada gimnasio"""
    
    PERIOD_CHOICES = [
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('yearly', 'Anual'),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='goals')
    
    # Objetivo de Socios
    target_members = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        help_text="Número objetivo de socios activos"
    )
    
    # Objetivo de Facturación
    target_revenue = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Facturación objetivo en euros"
    )
    
    # Período
    period = models.CharField(
        max_length=20, 
        choices=PERIOD_CHOICES, 
        default='monthly',
        help_text="Período del objetivo"
    )
    
    # Fecha de inicio del período
    start_date = models.DateField(help_text="Inicio del período del objetivo")
    end_date = models.DateField(help_text="Fin del período del objetivo")
    
    # Metadata
    created_by = models.ForeignKey(
        "accounts.User", 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_goals',
        help_text="Owner que estableció el objetivo"
    )
    notes = models.TextField(blank=True, help_text="Notas adicionales sobre el objetivo")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = "Objetivo de Gimnasio"
        verbose_name_plural = "Objetivos de Gimnasios"
    
    def __str__(self):
        period_display = self.get_period_display()
        return f"{self.gym.name} - {period_display} ({self.start_date.strftime('%m/%Y')})"
    
    def get_progress_members(self, current_members):
        """Calcula el progreso del objetivo de socios"""
        if not self.target_members or self.target_members == 0:
            return None
        return min(100, (current_members / self.target_members) * 100)
    
    def get_progress_revenue(self, current_revenue):
        """Calcula el progreso del objetivo de facturación"""
        if not self.target_revenue or self.target_revenue == 0:
            return None
        return min(100, (float(current_revenue) / float(self.target_revenue)) * 100)


class GymOpeningHours(models.Model):
    """Horarios de apertura regulares del gimnasio (Lunes a Domingo)"""
    
    DAYS_OF_WEEK = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    gym = models.OneToOneField(Gym, on_delete=models.CASCADE, related_name='opening_hours')
    
    # Lunes a Viernes
    monday_open = models.TimeField(default='06:00', help_text="Hora de apertura")
    monday_close = models.TimeField(default='22:00', help_text="Hora de cierre")
    
    tuesday_open = models.TimeField(default='06:00')
    tuesday_close = models.TimeField(default='22:00')
    
    wednesday_open = models.TimeField(default='06:00')
    wednesday_close = models.TimeField(default='22:00')
    
    thursday_open = models.TimeField(default='06:00')
    thursday_close = models.TimeField(default='22:00')
    
    friday_open = models.TimeField(default='06:00')
    friday_close = models.TimeField(default='22:00')
    
    # Fines de semana
    saturday_open = models.TimeField(default='08:00')
    saturday_close = models.TimeField(default='20:00')
    
    sunday_open = models.TimeField(default='08:00')
    sunday_close = models.TimeField(default='20:00')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Opening Hours"
    
    def __str__(self):
        return f"Horarios: {self.gym.name}"
    
    def get_hours_for_day(self, day_of_week):
        """Retorna horarios de apertura para un día (0=Lunes, 6=Domingo)"""
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        if 0 <= day_of_week < 7:
            day_name = day_names[day_of_week]
            opening = getattr(self, f'{day_name}_open')
            closing = getattr(self, f'{day_name}_close')
            return {'open': opening, 'close': closing}
        return None


class GymHoliday(models.Model):
    """Festivos del gimnasio - días cerrados o con horario especial"""
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='holidays')
    date = models.DateField(help_text="Fecha del festivo")
    name = models.CharField(max_length=100, help_text="Nombre del festivo (ej: Navidad, Año Nuevo)")
    is_closed = models.BooleanField(default=True, help_text="¿Está cerrado todo el día?")
    
    # Si no está cerrado, horario especial
    special_open = models.TimeField(null=True, blank=True, help_text="Hora de apertura especial (si abre)")
    special_close = models.TimeField(null=True, blank=True, help_text="Hora de cierre especial")
    
    allow_classes = models.BooleanField(
        default=False, 
        help_text="Permitir clases aunque sea festivo (si se fuerza)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ("gym", "date")
        verbose_name_plural = "Holidays"
        ordering = ['date']
    
    def __str__(self):
        return f"{self.name} ({self.date.strftime('%d/%m/%Y')}) - {self.gym.name}"


class PublicPortalSettings(models.Model):
    """Configuración del portal público y widgets embebibles para cada gimnasio"""
    
    gym = models.OneToOneField(
        Gym, 
        on_delete=models.CASCADE, 
        related_name='public_portal_settings',
        help_text="Configuración del portal público del gimnasio"
    )
    
    # ===== ACTIVACIÓN DEL PORTAL =====
    public_portal_enabled = models.BooleanField(
        default=False,
        help_text="Activa el portal público para este gimnasio"
    )
    public_slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL amigable del gimnasio (ej: 'qombo-arganzuela')"
    )
    
    # ===== MÓDULOS VISIBLES =====
    show_schedule = models.BooleanField(
        default=True,
        verbose_name="Mostrar Horario",
        help_text="Permite ver el calendario de clases públicamente"
    )
    show_pricing = models.BooleanField(
        default=True,
        verbose_name="Mostrar Precios",
        help_text="Muestra los planes y tarifas"
    )
    show_services = models.BooleanField(
        default=False,
        verbose_name="Mostrar Servicios",
        help_text="Muestra los servicios adicionales"
    )
    show_shop = models.BooleanField(
        default=False,
        verbose_name="Mostrar Tienda",
        help_text="Muestra productos en venta"
    )
    
    # ===== AUTO-REGISTRO DE CLIENTES =====
    allow_self_registration = models.BooleanField(
        default=False,
        verbose_name="Permitir Auto-Registro",
        help_text="Los clientes pueden crear su propia cuenta desde el portal público"
    )
    require_email_verification = models.BooleanField(
        default=True,
        verbose_name="Verificar Email",
        help_text="Requiere verificación de email al auto-registrarse"
    )
    require_staff_approval = models.BooleanField(
        default=False,
        verbose_name="Aprobación Manual",
        help_text="El staff debe aprobar manualmente cada nuevo registro"
    )
    
    # ===== RESERVAS ONLINE =====
    allow_online_booking = models.BooleanField(
        default=False,
        verbose_name="Reservas Online",
        help_text="Permite reservar clases desde el portal público"
    )
    booking_requires_login = models.BooleanField(
        default=True,
        verbose_name="Login Obligatorio",
        help_text="Requiere cuenta de cliente para reservar"
    )
    booking_requires_payment = models.BooleanField(
        default=False,
        verbose_name="Pago Obligatorio",
        help_text="Requiere método de pago vinculado para reservar"
    )
    
    # ===== PERSONALIZACIÓN =====
    meta_title = models.CharField(
        max_length=60,
        blank=True,
        help_text="Título SEO (aparece en Google)"
    )
    meta_description = models.TextField(
        max_length=160,
        blank=True,
        help_text="Descripción SEO (aparece en Google)"
    )
    og_image = models.ImageField(
        upload_to='portal/og_images/',
        null=True,
        blank=True,
        help_text="Imagen de portada para redes sociales (Open Graph)"
    )
    
    # ===== WIDGETS EMBEBIBLES =====
    allow_embedding = models.BooleanField(
        default=True,
        verbose_name="Permitir Embeber",
        help_text="Permite usar el calendario/precios como iframe en otras webs"
    )
    embed_domains = models.TextField(
        blank=True,
        verbose_name="Dominios Permitidos",
        help_text="Dominios permitidos para embeber (uno por línea). Dejar vacío para permitir todos."
    )
    
    # ===== TRACKING =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración Portal Público"
        verbose_name_plural = "Configuraciones Portal Público"
    
    def __str__(self):
        status = "✅ Activo" if self.public_portal_enabled else "❌ Inactivo"
        return f"Portal: {self.gym.name} ({status})"
    
    def get_public_url(self):
        """Retorna la URL pública del gimnasio"""
        if self.public_slug:
            # En producción sería: https://tudominio.com/gym/{slug}
            return f"/public/gym/{self.public_slug}/"
        return None
    
    def get_embed_url(self, module='schedule'):
        """Retorna la URL para embeber un módulo específico"""
        if self.public_slug and self.allow_embedding:
            return f"/embed/gym/{self.public_slug}/{module}/"
        return None