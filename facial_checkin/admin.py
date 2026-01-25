from django.contrib import admin
from .models import ClientFaceEncoding, FaceRecognitionLog, FaceRecognitionSettings


@admin.register(ClientFaceEncoding)
class ClientFaceEncodingAdmin(admin.ModelAdmin):
    list_display = ['client', 'registered_at', 'last_used_at', 'quality_score', 'consent_given']
    list_filter = ['consent_given', 'registered_at']
    search_fields = ['client__first_name', 'client__last_name', 'client__email']
    readonly_fields = ['encoding', 'registered_at', 'updated_at', 'last_used_at']
    date_hierarchy = 'registered_at'


@admin.register(FaceRecognitionLog)
class FaceRecognitionLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'gym', 'client', 'result', 'confidence', 'processing_time_ms']
    list_filter = ['result', 'gym', 'created_at']
    search_fields = ['client__first_name', 'client__last_name']
    readonly_fields = ['gym', 'client', 'result', 'confidence', 'activity_session', 
                       'processing_time_ms', 'error_message', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(FaceRecognitionSettings)
class FaceRecognitionSettingsAdmin(admin.ModelAdmin):
    list_display = ['gym', 'enabled', 'allow_face_checkin', 'allow_qr_checkin', 
                    'kiosk_mode_enabled', 'updated_at']
    list_filter = ['enabled', 'allow_face_checkin', 'kiosk_mode_enabled']
    search_fields = ['gym__name']
    fieldsets = (
        ('General', {
            'fields': ('gym', 'enabled')
        }),
        ('Métodos de Check-in', {
            'fields': ('allow_qr_checkin', 'allow_face_checkin', 'allow_manual_checkin')
        }),
        ('Configuración de Precisión', {
            'fields': ('confidence_threshold',),
            'description': 'Mayor umbral = más estricto (menos falsos positivos, más rechazos)'
        }),
        ('Modo Kiosko', {
            'fields': ('kiosk_mode_enabled', 'kiosk_welcome_message', 'auto_open_turnstile'),
            'classes': ('collapse',)
        }),
    )
