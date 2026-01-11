from django.db import models
from django.utils.translation import gettext_lazy as _
from organizations.models import Gym
from django.utils import timezone

class MarketingSettings(models.Model):
    """
    SMTP and general marketing configuration per Gym.
    """
    gym = models.OneToOneField(Gym, on_delete=models.CASCADE, related_name='marketing_settings')
    
    # SMTP Configuration
    smtp_host = models.CharField(max_length=255, default='smtp.gmail.com')
    smtp_port = models.IntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True) # Check if we need encryption
    smtp_use_tls = models.BooleanField(default=True)
    default_sender_email = models.EmailField(help_text="From address for emails")
    default_sender_name = models.CharField(max_length=255, default="Mi Gimnasio")
    
    # Branding
    header_logo = models.ImageField(upload_to='marketing/logos/', blank=True, null=True)
    footer_text = models.TextField(blank=True, help_text="HTML allowed")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    
    # Matching Campaign Audience
    audience_type = models.CharField(max_length=50, choices=Campaign.AudienceType.choices, default=Campaign.AudienceType.ALL_ACTIVE)
    audience_filter_value = models.CharField(max_length=255, blank=True, null=True, help_text="Tag name or specific filter ID")

    # Old target field (kept for compatibility or remove if migration allows)
    # We will use audience_type instead of target_group from now on
    
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
