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

    # Campos extra (JSON)
    extra_data = models.JSONField(default=dict, blank=True) # Ej: {"como_nos_conocio": "Google"}

    # Stripe Integration
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID de cliente en Stripe (cus_...)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.status})".strip()

    def save(self, *args, **kwargs):
        # Lógica simple de DNI: Si falta letra para formato español estándar, calcularla (simplificado)
        # Esto es un placeholder, la lógica real de DNI es más compleja.
        if self.dni:
            self.dni = self.dni.upper().strip()
        super().save(*args, **kwargs)

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


class ClientDocument(models.Model):
    """Gestión de documentos y contratos"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(max_length=200, help_text="Ej: Contrato de Adhesión")
    file = models.FileField(upload_to="clients/documents/")
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ClientMembership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activa"
        EXPIRED = "EXPIRED", "Caducada"
        CANCELLED = "CANCELLED", "Cancelada"
        PENDING = "PENDING", "Pendiente"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="memberships")
    name = models.CharField(max_length=150) # Ej: "Plan Anual", "Bono 10"
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_recurring = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.client}"


class ClientVisit(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Reservada"
        ATTENDED = "ATTENDED", "Asistió"
        NOSHOW = "NOSHOW", "No presentado"
        CANCELLED = "CANCELLED", "Cancelada"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="visits")
    staff = models.ForeignKey("staff.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="attended_visits", help_text="Staff que atendió/impartió")
    date = models.DateField()
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ATTENDED)
    
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
