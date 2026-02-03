"""
Modelos para el sistema de reconocimiento facial.
"""
from django.db import models
from django.utils import timezone


class ClientFaceEncoding(models.Model):
    """
    Almacena el encoding facial de un cliente.
    El encoding es un array de 128 números que identifica únicamente una cara.
    """
    client = models.OneToOneField(
        'clients.Client',
        on_delete=models.CASCADE,
        related_name='face_encoding'
    )
    
    # El encoding se guarda como bytes (128 floats * 8 bytes = 1024 bytes)
    encoding = models.BinaryField(
        help_text="Encoding facial del cliente (128 dimensiones)"
    )
    
    # Metadatos
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Consentimiento GDPR
    consent_given = models.BooleanField(default=False)
    consent_date = models.DateTimeField(null=True, blank=True)
    
    # Calidad del registro
    quality_score = models.FloatField(
        default=0.0,
        help_text="Puntuación de calidad del encoding (0-1)"
    )
    
    class Meta:
        app_label = 'facial_checkin'
        verbose_name = "Encoding Facial"
        verbose_name_plural = "Encodings Faciales"
    
    def __str__(self):
        return f"Face encoding de {self.client}"
    
    def mark_used(self):
        """Marca el encoding como usado (para estadísticas)"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])


class FaceRecognitionLog(models.Model):
    """
    Log de intentos de reconocimiento facial.
    Útil para auditoría y debugging.
    """
    SUCCESS = 'success'
    NO_FACE = 'no_face'
    NO_MATCH = 'no_match'
    MULTIPLE_FACES = 'multiple_faces'
    ERROR = 'error'
    
    RESULT_CHOICES = [
        (SUCCESS, 'Éxito'),
        (NO_FACE, 'No se detectó rostro'),
        (NO_MATCH, 'Sin coincidencia'),
        (MULTIPLE_FACES, 'Múltiples rostros'),
        (ERROR, 'Error'),
    ]
    
    gym = models.ForeignKey(
        'organizations.Gym',
        on_delete=models.CASCADE,
        related_name='face_recognition_logs'
    )
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='face_recognition_logs'
    )
    
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    confidence = models.FloatField(null=True, blank=True)
    
    # Contexto
    activity_session = models.ForeignKey(
        'activities.ActivitySession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Info técnica
    processing_time_ms = models.IntegerField(
        null=True,
        help_text="Tiempo de procesamiento en milisegundos"
    )
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'facial_checkin'
        verbose_name = "Log de Reconocimiento"
        verbose_name_plural = "Logs de Reconocimiento"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.result} - {self.gym} - {self.created_at}"


class FaceRecognitionSettings(models.Model):
    """
    Configuración de reconocimiento facial por gimnasio.
    """
    gym = models.OneToOneField(
        'organizations.Gym',
        on_delete=models.CASCADE,
        related_name='face_recognition_settings'
    )
    
    # Activar/desactivar
    enabled = models.BooleanField(
        default=False,
        help_text="Activar reconocimiento facial para check-in"
    )
    
    # Configuración de precisión
    confidence_threshold = models.FloatField(
        default=0.6,
        help_text="Umbral de confianza (0-1). Mayor = más estricto"
    )
    
    # Opciones de check-in disponibles
    allow_qr_checkin = models.BooleanField(
        default=True,
        help_text="Permitir check-in con QR"
    )
    allow_face_checkin = models.BooleanField(
        default=False,
        help_text="Permitir check-in con reconocimiento facial"
    )
    allow_manual_checkin = models.BooleanField(
        default=True,
        help_text="Permitir check-in manual por staff"
    )
    
    # Kiosko mode
    kiosk_mode_enabled = models.BooleanField(
        default=False,
        help_text="Habilitar modo kiosko (pantalla completa para tablet)"
    )
    kiosk_welcome_message = models.CharField(
        max_length=200,
        default="Bienvenido, mira a la cámara",
        blank=True
    )
    # SECURITY: Token de autenticación para kioskos
    kiosk_token = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text="Token secreto para autenticar kioskos (dejar vacío para generar)"
    )
    kiosk_allowed_ips = models.TextField(
        blank=True,
        default='',
        help_text="IPs permitidas para el kiosko (una por línea). Vacío = permitir todas"
    )
    
    # Auto-apertura de torno
    auto_open_turnstile = models.BooleanField(
        default=False,
        help_text="Abrir torno automáticamente al reconocer"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'facial_checkin'
        verbose_name = "Configuración de Reconocimiento Facial"
        verbose_name_plural = "Configuraciones de Reconocimiento Facial"
    
    def __str__(self):
        status = "Activado" if self.enabled else "Desactivado"
        return f"Face Recognition - {self.gym} ({status})"
