from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class ClientGroup(models.Model):
    """Grupos de clientes (ej: 'Mañanas', 'Empresas') con jerarquía"""
    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="client_groups")
    name = models.CharField(max_length=100)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="subgroups")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("gym", "name")

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

class ClientTag(models.Model):
    """Etiquetas rápidas (ej: 'VIP', 'Lesionado', 'Moroso')"""
    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="client_tags")
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#94a3b8") # Slate 400 default
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("gym", "name")

    def __str__(self):
        return self.name

class Client(models.Model):
    class Status(models.TextChoices):
        LEAD = "LEAD", "Prospecto"
        ACTIVE = "ACTIVE", "Activo"
        INACTIVE = "INACTIVE", "Inactivo" # Baja > 24h
        BLOCKED = "BLOCKED", "Bloqueado"
        PAUSED = "PAUSED", "Excedencia"

    class Gender(models.TextChoices):
        MALE = "M", "Masculino"
        FEMALE = "F", "Femenino"
        OTHER = "O", "Otro"
        NOT_SPECIFIED = "X", "No especificado"

    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="clients")
    
    # Vinculación opcional a usuario real (Login)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="client_profile"
    )

    # Estado
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.LEAD)

    # Datos principales
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True, null=True) # Opcional en Lead, obligatorio si tiene usuario
    phone_number = models.CharField(max_length=50, blank=True)
    
    # Datos secundarios
    dni = models.CharField(max_length=20, blank=True, help_text="DNI/NIE/Pasaporte")
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=2, choices=Gender.choices, default=Gender.NOT_SPECIFIED)
    address = models.TextField(blank=True)
    photo = models.ImageField(upload_to="clients/photos/", blank=True, null=True)

    # Access Control
    access_code = models.CharField(max_length=50, blank=True, help_text="Código de acceso o PIN simplificado")

    # Clasificación
    groups = models.ManyToManyField(ClientGroup, blank=True, related_name="clients")
    tags = models.ManyToManyField(ClientTag, blank=True, related_name="clients")
    is_company_client = models.BooleanField(default=False, help_text="Marca si el cliente pertenece a una empresa")

    # Campos extra (JSON)
    extra_data = models.JSONField(default=dict, blank=True) # Ej: {"como_nos_conocio": "Google"}

    # Stripe Integration
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID de cliente en Stripe (cus_...)")
    
    # Payment Gateway Preference
    GATEWAY_PREFERENCE_CHOICES = [
        ('AUTO', 'Automático (según configuración del gym)'),
        ('STRIPE', 'Stripe'),
        ('REDSYS', 'Redsys'),
    ]
    preferred_gateway = models.CharField(
        max_length=20, 
        choices=GATEWAY_PREFERENCE_CHOICES, 
        default='AUTO',
        help_text="Pasarela de pago preferida para este cliente"
    )
    
    # Preferencias de comunicación
    email_notifications_enabled = models.BooleanField(default=True, help_text="Si el cliente quiere recibir emails del gimnasio")

    # App/Portal Activity Tracking
    last_app_access = models.DateTimeField(null=True, blank=True, help_text="Última vez que accedió a la app o portal")
    app_access_count = models.IntegerField(default=0, help_text="Número de veces que ha accedido")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.status})".strip()

    @property
    def has_portal_access(self):
        """Indica si el cliente tiene acceso al portal (tiene usuario vinculado)"""
        return self.user is not None

    def save(self, *args, **kwargs):
        # Lógica simple de DNI: Si falta letra para formato español estándar, calcularla (simplificado)
        # Esto es un placeholder, la lógica real de DNI es más compleja.
        if self.dni:
            self.dni = self.dni.upper().strip()
        super().save(*args, **kwargs)


class ClientField(models.Model):
    class FieldType(models.TextChoices):
        SELECT = "SELECT", "Selección"
        TOGGLE = "TOGGLE", "Interruptor"

    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="client_fields")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=60)
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.SELECT)
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Auto-registro público
    show_in_registration = models.BooleanField(
        default=False,
        verbose_name="Mostrar en Registro Público",
        help_text="Si está activo, este campo aparecerá en el formulario de auto-registro"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Orden de aparición en el formulario (menor = primero)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]
        unique_together = ("gym", "slug")

    def __str__(self):
        return self.name


class ClientFieldOption(models.Model):
    field = models.ForeignKey(ClientField, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=120)
    value = models.SlugField(max_length=80)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("field", "value")

    def __str__(self):
        return f"{self.label} ({self.field.name})"

class ClientNote(models.Model):
    """Notas internas sobre el cliente"""
    class Type(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        VIP = "VIP", "VIP (Dorado)"
        WARNING = "WARNING", "Alerta Amarilla"
        DANGER = "DANGER", "Alerta Roja"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    text = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.NORMAL)
    is_popup = models.BooleanField(default=False, help_text="Si activo, salta alerta al abrir ficha")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Nota ({self.type}) sobre {self.client}"


class DocumentTemplate(models.Model):
    """Plantilla de documento reutilizable a nivel de gimnasio"""
    
    class DocumentType(models.TextChoices):
        CONTRACT = "CONTRACT", "Contrato"
        TERMS = "TERMS", "Términos y Condiciones"
        WAIVER = "WAIVER", "Exención de Responsabilidad"
        CONSENT = "CONSENT", "Consentimiento"
        MEDICAL = "MEDICAL", "Certificado Médico"
        OTHER = "OTHER", "Otro Documento"
    
    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="document_templates")
    name = models.CharField(max_length=200, help_text="Ej: Contrato de Adhesión 2024")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER)
    content = models.TextField(help_text="Contenido HTML del documento")
    requires_signature = models.BooleanField(default=True, help_text="¿Requiere firma del cliente?")
    is_active = models.BooleanField(default=True, help_text="¿Está disponible para enviar?")
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_templates")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Plantilla de Documento"
        verbose_name_plural = "Plantillas de Documentos"
    
    def __str__(self):
        return f"{self.name} ({self.get_document_type_display()})"


class ClientDocument(models.Model):
    """Gestión de documentos y contratos"""
    
    class DocumentType(models.TextChoices):
        CONTRACT = "CONTRACT", "Contrato"
        TERMS = "TERMS", "Términos y Condiciones"
        WAIVER = "WAIVER", "Exención de Responsabilidad"
        CONSENT = "CONSENT", "Consentimiento"
        MEDICAL = "MEDICAL", "Certificado Médico"
        OTHER = "OTHER", "Otro Documento"
    
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        PENDING = "PENDING", "Pendiente de Firma"
        SIGNED = "SIGNED", "Firmado"
        EXPIRED = "EXPIRED", "Caducado"
        REJECTED = "REJECTED", "Rechazado"
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="documents")
    template = models.ForeignKey(DocumentTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_documents", help_text="Plantilla origen")
    name = models.CharField(max_length=200, help_text="Ej: Contrato de Adhesión")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER)
    
    # Documento puede ser archivo o contenido generado
    file = models.FileField(upload_to="clients/documents/", blank=True, null=True)
    content = models.TextField(blank=True, help_text="Contenido HTML/texto del documento")
    
    # Firma
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_signed = models.BooleanField(default=False)
    signature_image = models.ImageField(upload_to="clients/signatures/", blank=True, null=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    signed_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Metadata
    requires_signature = models.BooleanField(default=True, help_text="¿Requiere que el cliente lo firme?")
    expires_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True, help_text="Cuándo se envió al cliente")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Link to membership contract
    membership_plan = models.ForeignKey('memberships.MembershipPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name="membership_documents")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.client.first_name} ({self.get_status_display()})"



class ChatRoom(models.Model):
    """Sala de chat entre un cliente y el gimnasio"""
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name="chat_room")
    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="chat_rooms")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Último mensaje para ordenar
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_message_at']
    
    def __str__(self):
        return f"Chat: {self.client.first_name} {self.client.last_name}"


class ChatMessage(models.Model):
    """Mensajes del chat"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    message = models.TextField()
    
    # Archivos adjuntos (opcional)
    attachment = models.FileField(upload_to="chat_attachments/", null=True, blank=True)
    
    # Metadata
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender.email}: {self.message[:50]}"
    
    @property
    def is_from_client(self):
        """True si el mensaje es del cliente"""
        return hasattr(self.sender, 'client_profile')


class ClientMembership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activa"
        EXPIRED = "EXPIRED", "Caducada"
        CANCELLED = "CANCELLED", "Cancelada"
        PENDING = "PENDING", "Pendiente"
        PAUSED = "PAUSED", "Pausada"
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pendiente de pago"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="memberships")
    gym = models.ForeignKey('organizations.Gym', on_delete=models.CASCADE, related_name="client_memberships", null=True)
    plan = models.ForeignKey('memberships.MembershipPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name="active_memberships")
    payment_method = models.ForeignKey('finance.PaymentMethod', on_delete=models.SET_NULL, null=True, blank=True)
    
    name = models.CharField(max_length=150) # Ej: "Plan Anual", "Bono 10"
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_recurring = models.BooleanField(default=True)
    
    # Billing dates for recurring memberships
    current_period_start = models.DateField(null=True, blank=True, help_text="Inicio del periodo de facturación actual")
    current_period_end = models.DateField(null=True, blank=True, help_text="Fin del periodo de facturación actual")
    next_billing_date = models.DateField(null=True, blank=True, help_text="Fecha del próximo cobro")
    
    # Session tracking for pack/limited plans
    sessions_total = models.IntegerField(null=True, blank=True, help_text="Total de sesiones (0 o None = ilimitado)")
    sessions_used = models.IntegerField(default=0, help_text="Sesiones consumidas")
    
    # Billing tracking
    failed_charge_attempts = models.IntegerField(default=0, help_text="Intentos de cobro fallidos consecutivos")
    last_charge_attempt = models.DateTimeField(null=True, blank=True, help_text="Última fecha de intento de cobro")
    last_charge_error = models.CharField(max_length=255, blank=True, help_text="Último error de cobro")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_memberships')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.client}"
    
    @property
    def sessions_remaining(self):
        """Retorna sesiones restantes, None si es ilimitado"""
        if self.sessions_total is None or self.sessions_total == 0:
            return None  # Ilimitado
        return max(0, self.sessions_total - self.sessions_used)
    
    @property
    def is_unlimited(self):
        """Retorna True si el plan es ilimitado"""
        return self.sessions_total is None or self.sessions_total == 0
    
    @property
    def usage_percentage(self):
        """Porcentaje de uso (0-100), None si es ilimitado"""
        if self.is_unlimited:
            return None
        if self.sessions_total == 0:
            return 0
        return min(100, int((self.sessions_used / self.sessions_total) * 100))


class ClientMembershipAccessRule(models.Model):
    """Reglas de acceso personalizadas para una membresía de cliente"""
    PERIODS = [
        ('TOTAL', "Total (Bono)"),
        ('PER_CYCLE', "Por Ciclo (Recurrente)"),
    ]
    
    membership = models.ForeignKey(ClientMembership, on_delete=models.CASCADE, related_name='access_rules')
    
    # Targets: Can be broadly (Category) or Specific (Activity/Service)
    activity_category = models.ForeignKey('activities.ActivityCategory', on_delete=models.CASCADE, null=True, blank=True)
    activity = models.ForeignKey('activities.Activity', on_delete=models.CASCADE, null=True, blank=True)
    
    service_category = models.ForeignKey('services.ServiceCategory', on_delete=models.CASCADE, null=True, blank=True)
    service = models.ForeignKey('services.Service', on_delete=models.CASCADE, null=True, blank=True)
    
    quantity = models.IntegerField("Cantidad", default=0, help_text="0 = Ilimitado")
    quantity_used = models.IntegerField("Cantidad usada", default=0)
    period = models.CharField(max_length=20, choices=PERIODS, default='PER_CYCLE')
    
    class Meta:
        verbose_name = "Regla de acceso de membresía"
        verbose_name_plural = "Reglas de acceso de membresías"
    
    def __str__(self):
        if self.activity: target = f"Actividad: {self.activity.name}"
        elif self.activity_category: target = f"Cat. Act.: {self.activity_category.name}"
        elif self.service: target = f"Servicio: {self.service.name}"
        elif self.service_category: target = f"Cat. Serv.: {self.service_category.name}"
        else: target = "Todo"
        
        qty = "Ilimitado" if self.quantity == 0 else str(self.quantity)
        return f"{qty} x {target}"
    
    @property
    def quantity_remaining(self):
        """Cantidad restante, None si es ilimitado"""
        if self.quantity == 0:
            return None
        return max(0, self.quantity - self.quantity_used)


# Alias para compatibilidad con las vistas del portal público
Membership = ClientMembership


class ClientVisit(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Reservada"
        ATTENDED = "ATTENDED", "Asistió"
        NOSHOW = "NOSHOW", "No presentado"
        CANCELLED = "CANCELLED", "Cancelada"
    
    class CancellationType(models.TextChoices):
        EARLY = "EARLY", "Cancelación temprana"
        LATE = "LATE", "Cancelación tardía con penalización"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="visits")
    staff = models.ForeignKey("staff.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="attended_visits", help_text="Staff que atendió/impartió")
    date = models.DateField()
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ATTENDED)
    cancellation_type = models.CharField(max_length=20, choices=CancellationType.choices, null=True, blank=True, help_text="Tipo de cancelación si el estado es CANCELLED")
    
    concept = models.CharField(max_length=100, blank=True) # Ej: "Clase de Crossfit", "Acceso Libre"

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client} - {self.date}"


class ClientSale(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="sales")
    staff = models.ForeignKey("staff.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="sales_made", help_text="Vendedor")
    concept = models.CharField(max_length=200) # Ej: "Botella Agua", "Camiseta"
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.concept} ({self.amount}€)"


class ClientPaymentMethod(models.Model):
    """
    Stores payment method information for a client (tokenized, not actual card numbers).
    In production, this should integrate with a payment gateway like Stripe.
    """
    CARD_TYPES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
        ('other', 'Otra'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="payment_methods")
    card_type = models.CharField(max_length=20, choices=CARD_TYPES, default='other')
    last_4 = models.CharField(max_length=4, help_text="Últimos 4 dígitos de la tarjeta")
    expiry_month = models.IntegerField()
    expiry_year = models.IntegerField()
    cardholder_name = models.CharField(max_length=100, blank=True)
    is_default = models.BooleanField(default=False)
    
    # In production, you'd store a payment gateway token here
    # stripe_payment_method_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"

    def __str__(self):
        return f"{self.card_type.upper()} ****{self.last_4}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default per client
        if self.is_default:
            ClientPaymentMethod.objects.filter(
                client=self.client, 
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
