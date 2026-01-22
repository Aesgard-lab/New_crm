from django.contrib import admin
from organizations.models import PublicPortalSettings


@admin.register(PublicPortalSettings)
class PublicPortalSettingsAdmin(admin.ModelAdmin):
    list_display = ['gym', 'public_portal_enabled', 'public_slug', 'allow_self_registration', 'allow_online_booking']
    list_filter = ['public_portal_enabled', 'allow_self_registration', 'allow_online_booking', 'allow_embedding']
    search_fields = ['gym__name', 'public_slug']
    
    fieldsets = (
        ('General', {
            'fields': ('gym', 'public_portal_enabled', 'public_slug')
        }),
        ('Módulos Visibles', {
            'fields': ('show_schedule', 'show_pricing', 'show_services', 'show_shop')
        }),
        ('Auto-Registro de Clientes', {
            'fields': ('allow_self_registration', 'require_email_verification', 'require_staff_approval')
        }),
        ('Reservas Online', {
            'fields': ('allow_online_booking', 'booking_requires_login', 'booking_requires_payment')
        }),
        ('SEO y Personalización', {
            'fields': ('meta_title', 'meta_description', 'og_image'),
            'classes': ('collapse',)
        }),
        ('Widgets Embebibles', {
            'fields': ('allow_embedding', 'embed_domains'),
            'classes': ('collapse',)
        }),
    )
