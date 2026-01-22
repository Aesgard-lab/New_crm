"""
Módulo de Control de Acceso
===========================
Sistema preparado para integrarse con hardware de control de acceso:
- Tornos
- Puertas automáticas
- Lectores RFID/NFC
- Lectores biométricos
- Escáneres QR

Proveedores compatibles (a configurar):
- Gantner, Salto, Kaba, Dormakaba
- ZKTeco, Hikvision, Suprema
- Custom/genérico via API REST
"""

from django.db import models
from django.utils import timezone
from datetime import timedelta


class AccessDevice(models.Model):
    """
    Dispositivo de control de acceso (torno, puerta, lector).
    Cada gimnasio puede tener múltiples dispositivos.
    """
    DEVICE_TYPES = [
        ('TURNSTILE', 'Torno'),
        ('DOOR', 'Puerta Automática'),
        ('BARRIER', 'Barrera'),
        ('RFID_READER', 'Lector RFID/NFC'),
        ('QR_SCANNER', 'Escáner QR'),
        ('BIOMETRIC', 'Biométrico'),
        ('COMBINED', 'Combinado'),
    ]
    
    DIRECTION_TYPES = [
        ('ENTRY', 'Solo Entrada'),
        ('EXIT', 'Solo Salida'),
        ('BIDIRECTIONAL', 'Bidireccional'),
    ]
    
    STATUS_CHOICES = [
        ('ONLINE', 'En línea'),
        ('OFFLINE', 'Desconectado'),
        ('MAINTENANCE', 'En mantenimiento'),
        ('ERROR', 'Error'),
    ]
    
    gym = models.ForeignKey(
        'organizations.Gym',
        on_delete=models.CASCADE,
        related_name='access_devices'
    )
    name = models.CharField(max_length=100, help_text="Nombre del dispositivo (ej: Torno Principal)")
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, default='TURNSTILE')
    direction = models.CharField(max_length=20, choices=DIRECTION_TYPES, default='BIDIRECTIONAL')
    location = models.CharField(max_length=100, blank=True, help_text="Ubicación física (ej: Entrada principal)")
    
    # Zona de acceso (para control por áreas)
    zone = models.ForeignKey(
        'AccessZone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devices',
        help_text="Zona a la que da acceso este dispositivo"
    )
    
    # Configuración de conexión con el hardware
    device_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="ID único del dispositivo (proporcionado por el fabricante)"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="IP del dispositivo en la red local")
    api_endpoint = models.URLField(blank=True, help_text="URL de la API del dispositivo (si aplica)")
    api_key = models.CharField(max_length=255, blank=True, help_text="API Key para autenticación")
    
    # Configuración del proveedor
    PROVIDER_CHOICES = [
        ('GENERIC', 'Genérico/API REST'),
        ('GANTNER', 'Gantner'),
        ('SALTO', 'Salto'),
        ('ZKTECO', 'ZKTeco'),
        ('HIKVISION', 'Hikvision'),
        ('SUPREMA', 'Suprema'),
        ('DORMAKABA', 'Dormakaba'),
        ('CUSTOM', 'Personalizado'),
    ]
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='GENERIC')
    provider_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuración específica del proveedor en formato JSON"
    )
    
    # Estado y monitoreo
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OFFLINE')
    last_heartbeat = models.DateTimeField(null=True, blank=True, help_text="Última comunicación con el dispositivo")
    last_error = models.TextField(blank=True, help_text="Último mensaje de error")
    
    # Configuración de operación
    is_active = models.BooleanField(default=True)
    allow_offline_mode = models.BooleanField(
        default=False,
        help_text="Permitir acceso cuando el dispositivo está offline (usa caché local)"
    )
    timeout_seconds = models.IntegerField(default=5, help_text="Timeout de conexión en segundos")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Dispositivo de Acceso"
        verbose_name_plural = "Dispositivos de Acceso"
        ordering = ['gym', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_device_type_display()})"
    
    def update_heartbeat(self):
        """Actualiza el timestamp de última comunicación."""
        self.last_heartbeat = timezone.now()
        self.status = 'ONLINE'
        self.save(update_fields=['last_heartbeat', 'status'])
    
    def set_error(self, error_message):
        """Registra un error en el dispositivo."""
        self.status = 'ERROR'
        self.last_error = error_message
        self.save(update_fields=['status', 'last_error'])
    
    @property
    def is_online(self):
        """Verifica si el dispositivo está en línea (heartbeat en últimos 5 min)."""
        if not self.last_heartbeat:
            return False
        return (timezone.now() - self.last_heartbeat) < timedelta(minutes=5)


class AccessZone(models.Model):
    """
    Zonas de acceso dentro del gimnasio.
    Permite controlar acceso por áreas (musculación, piscina, spa, etc.)
    """
    gym = models.ForeignKey(
        'organizations.Gym',
        on_delete=models.CASCADE,
        related_name='access_zones'
    )
    name = models.CharField(max_length=100, help_text="Nombre de la zona (ej: Sala Musculación)")
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#6366F1', help_text="Color para identificación visual")
    
    # Capacidad y aforo
    max_capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Aforo máximo permitido (dejar vacío si no aplica)"
    )
    
    # Restricciones
    requires_specific_membership = models.BooleanField(
        default=False,
        help_text="¿Requiere membresía específica para acceder?"
    )
    allowed_membership_plans = models.ManyToManyField(
        'memberships.MembershipPlan',
        blank=True,
        related_name='allowed_zones',
        help_text="Planes de membresía que permiten acceso a esta zona"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Zona de Acceso"
        verbose_name_plural = "Zonas de Acceso"
        ordering = ['gym', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.gym.name}"
    
    def get_current_occupancy(self):
        """Obtiene el aforo actual de la zona."""
        # Contar clientes que han entrado pero no salido en las últimas 12 horas
        twelve_hours_ago = timezone.now() - timedelta(hours=12)
        
        entries = AccessLog.objects.filter(
            device__zone=self,
            direction='ENTRY',
            timestamp__gte=twelve_hours_ago,
            status='GRANTED'
        ).values_list('client_id', flat=True)
        
        exits = AccessLog.objects.filter(
            device__zone=self,
            direction='EXIT',
            timestamp__gte=twelve_hours_ago,
            status='GRANTED'
        ).values_list('client_id', flat=True)
        
        # Clientes dentro = entradas - salidas
        inside = set(entries) - set(exits)
        return len(inside)
    
    @property
    def occupancy_percentage(self):
        """Porcentaje de ocupación actual."""
        if not self.max_capacity:
            return None
        current = self.get_current_occupancy()
        return min(100, int((current / self.max_capacity) * 100))


class ClientAccessCredential(models.Model):
    """
    Credenciales de acceso del cliente.
    Un cliente puede tener múltiples credenciales (QR, tarjeta, PIN, huella).
    """
    CREDENTIAL_TYPES = [
        ('QR_DYNAMIC', 'QR Dinámico (App)'),
        ('QR_STATIC', 'QR Estático'),
        ('RFID', 'Tarjeta RFID/NFC'),
        ('BARCODE', 'Código de Barras'),
        ('PIN', 'Código PIN'),
        ('FINGERPRINT', 'Huella Dactilar'),
        ('FACE', 'Reconocimiento Facial'),
        ('BLUETOOTH', 'Bluetooth/BLE'),
    ]
    
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        related_name='access_credentials'
    )
    credential_type = models.CharField(max_length=20, choices=CREDENTIAL_TYPES)
    credential_value = models.CharField(
        max_length=255,
        help_text="Valor de la credencial (número de tarjeta, PIN, template biométrico, etc.)"
    )
    
    # Estado
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False, help_text="Credencial principal del cliente")
    
    # Vigencia
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True, help_text="Dejar vacío para sin caducidad")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, help_text="Notas internas")
    
    class Meta:
        verbose_name = "Credencial de Acceso"
        verbose_name_plural = "Credenciales de Acceso"
        ordering = ['-is_primary', '-created_at']
        # Un cliente no puede tener dos credenciales iguales del mismo tipo
        unique_together = ['client', 'credential_type', 'credential_value']
    
    def __str__(self):
        return f"{self.client} - {self.get_credential_type_display()}"
    
    @property
    def is_valid(self):
        """Verifica si la credencial es válida actualmente."""
        if not self.is_active:
            return False
        now = timezone.now()
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True


class AccessLog(models.Model):
    """
    Registro de entradas y salidas.
    Log inmutable de todos los intentos de acceso.
    """
    DIRECTION_CHOICES = [
        ('ENTRY', 'Entrada'),
        ('EXIT', 'Salida'),
    ]
    
    STATUS_CHOICES = [
        ('GRANTED', 'Acceso Concedido'),
        ('DENIED', 'Acceso Denegado'),
        ('ERROR', 'Error de Sistema'),
        ('MANUAL', 'Acceso Manual'),
        ('EMERGENCY', 'Apertura de Emergencia'),
    ]
    
    DENIAL_REASONS = [
        ('NO_MEMBERSHIP', 'Sin membresía activa'),
        ('MEMBERSHIP_EXPIRED', 'Membresía expirada'),
        ('PAYMENT_OVERDUE', 'Pago pendiente'),
        ('INVALID_CREDENTIAL', 'Credencial inválida'),
        ('CREDENTIAL_EXPIRED', 'Credencial expirada'),
        ('ZONE_NOT_ALLOWED', 'Zona no permitida'),
        ('CAPACITY_EXCEEDED', 'Aforo completo'),
        ('SCHEDULE_RESTRICTED', 'Fuera de horario permitido'),
        ('ACCOUNT_BLOCKED', 'Cuenta bloqueada'),
        ('UNKNOWN_PERSON', 'Persona no identificada'),
        ('DEVICE_ERROR', 'Error del dispositivo'),
        ('OTHER', 'Otro'),
    ]
    
    # Identificación
    gym = models.ForeignKey(
        'organizations.Gym',
        on_delete=models.CASCADE,
        related_name='access_logs'
    )
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='access_logs'
    )
    device = models.ForeignKey(
        'AccessDevice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='access_logs'
    )
    
    # Datos del acceso
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    denial_reason = models.CharField(
        max_length=30,
        choices=DENIAL_REASONS,
        blank=True,
        help_text="Razón del rechazo (si aplica)"
    )
    
    # Credencial utilizada
    credential_type = models.CharField(max_length=20, blank=True)
    credential_value_masked = models.CharField(
        max_length=50,
        blank=True,
        help_text="Valor enmascarado de la credencial (últimos 4 dígitos, etc.)"
    )
    
    # Timestamp
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Datos adicionales del hardware
    raw_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Datos crudos recibidos del dispositivo"
    )
    
    # Campos de auditoría
    processed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Usuario que procesó manualmente (si aplica)"
    )
    notes = models.TextField(blank=True, help_text="Notas adicionales")
    
    class Meta:
        verbose_name = "Registro de Acceso"
        verbose_name_plural = "Registros de Acceso"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['gym', 'timestamp']),
            models.Index(fields=['client', 'timestamp']),
            models.Index(fields=['device', 'timestamp']),
            models.Index(fields=['status', 'timestamp']),
        ]
    
    def __str__(self):
        client_name = self.client.full_name if self.client else "Desconocido"
        return f"{client_name} - {self.get_direction_display()} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def duration_inside(self):
        """
        Calcula el tiempo dentro del gimnasio.
        Solo válido para registros de SALIDA.
        """
        if self.direction != 'EXIT' or not self.client:
            return None
        
        # Buscar la entrada correspondiente
        entry = AccessLog.objects.filter(
            client=self.client,
            gym=self.gym,
            direction='ENTRY',
            status='GRANTED',
            timestamp__lt=self.timestamp,
            timestamp__gte=self.timestamp - timedelta(hours=24)
        ).order_by('-timestamp').first()
        
        if entry:
            return self.timestamp - entry.timestamp
        return None


class AccessSchedule(models.Model):
    """
    Horarios de acceso permitido.
    Define cuándo puede acceder un cliente según su plan.
    """
    DAYS_OF_WEEK = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    gym = models.ForeignKey(
        'organizations.Gym',
        on_delete=models.CASCADE,
        related_name='access_schedules'
    )
    name = models.CharField(max_length=100, help_text="Nombre del horario (ej: Horario Mañanas)")
    description = models.TextField(blank=True)
    
    # Días y horas permitidos
    days_of_week = models.JSONField(
        default=list,
        help_text="Lista de días permitidos [0=Lunes, 6=Domingo]"
    )
    start_time = models.TimeField(help_text="Hora de inicio del acceso permitido")
    end_time = models.TimeField(help_text="Hora de fin del acceso permitido")
    
    # Planes asociados
    membership_plans = models.ManyToManyField(
        'memberships.MembershipPlan',
        blank=True,
        related_name='access_schedules',
        help_text="Planes de membresía que tienen este horario"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Horario de Acceso"
        verbose_name_plural = "Horarios de Acceso"
        ordering = ['gym', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"
    
    def is_access_allowed_now(self):
        """Verifica si el acceso está permitido en este momento."""
        now = timezone.localtime()
        current_day = now.weekday()
        current_time = now.time()
        
        if current_day not in self.days_of_week:
            return False
        
        # Manejar horarios que cruzan medianoche
        if self.start_time <= self.end_time:
            return self.start_time <= current_time <= self.end_time
        else:
            return current_time >= self.start_time or current_time <= self.end_time


class AccessAlert(models.Model):
    """
    Alertas de acceso para monitoreo en tiempo real.
    """
    ALERT_TYPES = [
        ('DENIED_ACCESS', 'Acceso Denegado'),
        ('CAPACITY_WARNING', 'Aviso de Aforo'),
        ('CAPACITY_EXCEEDED', 'Aforo Excedido'),
        ('DEVICE_OFFLINE', 'Dispositivo Desconectado'),
        ('DEVICE_ERROR', 'Error de Dispositivo'),
        ('SUSPICIOUS_ACTIVITY', 'Actividad Sospechosa'),
        ('EMERGENCY', 'Emergencia'),
    ]
    
    SEVERITY_LEVELS = [
        ('LOW', 'Baja'),
        ('MEDIUM', 'Media'),
        ('HIGH', 'Alta'),
        ('CRITICAL', 'Crítica'),
    ]
    
    gym = models.ForeignKey(
        'organizations.Gym',
        on_delete=models.CASCADE,
        related_name='access_alerts'
    )
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='MEDIUM')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Relaciones opcionales
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    device = models.ForeignKey(
        'AccessDevice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    access_log = models.ForeignKey(
        'AccessLog',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Estado
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Alerta de Acceso"
        verbose_name_plural = "Alertas de Acceso"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.title}"
    
    def mark_resolved(self, user, notes=''):
        """Marca la alerta como resuelta."""
        self.is_resolved = True
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save()
