from django.db import models
from django.conf import settings

class StaffProfile(models.Model):
    class Role(models.TextChoices):
        MANAGER = "MANAGER", "Gerente"
        TRAINER = "TRAINER", "Entrenador"
        RECEPTIONIST = "RECEPTIONIST", "Recepción"
        CLEANER = "CLEANER", "Limpieza"
        OTHER = "OTHER", "Otro"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile")
    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="staff")
    
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TRAINER)
    bio = models.TextField(blank=True, help_text="Breve biografía o notas sobre el empleado")
    color = models.CharField(max_length=7, default="#3b82f6", help_text="Color para el calendario (HEX)")
    photo = models.ImageField(upload_to="staff/photos/", blank=True, null=True, help_text="Foto para perfil público y actividades")
    
    # Kiosk/Tablet Access
    pin_code = models.CharField(max_length=6, blank=True, null=True, help_text="PIN de 4-6 dígitos para fichar en Tablet")
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Fallback if get_full_name doesn't exist (using custom User model)
        if hasattr(self.user, 'get_full_name'):
             name = self.user.get_full_name()
        else:
             name = f"{self.user.first_name} {self.user.last_name}".strip()
        
        if not name:
            name = self.user.email
        return name


class SalaryConfig(models.Model):
    class Mode(models.TextChoices):
        MONTHLY = "MONTHLY", "Mensual (Fijo)"
        HOURLY = "HOURLY", "Por Hora"

    staff = models.OneToOneField(StaffProfile, on_delete=models.CASCADE, related_name="salary_config")
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.MONTHLY)
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Sueldo base mensual o precio/hora base")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contrato {self.staff.user.first_name} ({self.get_mode_display()})"


class IncentiveRule(models.Model):
    class Type(models.TextChoices):
        SALE_PCT = "SALE_PCT", "% Comisión Venta"
        SALE_FIXED = "SALE_FIXED", "Fijo por Venta"
        CLASS_FIXED = "CLASS_FIXED", "Fijo por Clase Impartida"
        CLASS_ATTENDANCE = "CLASS_ATTENDANCE", "Variable por Asistente a Clase"
        TASK_FIXED = "TASK_FIXED", "Fijo por Tarea (To-Do)"

    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="incentive_rules")
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="incentive_rules", null=True, blank=True, help_text="Si se especifica, aplica solo a este empleado. Si no, es global del gym.")
    name = models.CharField(max_length=150, help_text="Ej: Comisión 10% Bonos, Clase Yoga")
    
    type = models.CharField(max_length=50, choices=Type.choices)
    value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Porcentaje (0-100) o Cantidad Fija")
    
    criteria = models.JSONField(default=dict, blank=True, help_text="Filtros JSON (ej: product_type='membership')")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()}: {self.value})"


class StaffCommission(models.Model):
    """Registro de cada euro ganado por incentivos"""
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="commissions")
    rule = models.ForeignKey(IncentiveRule, on_delete=models.SET_NULL, null=True, related_name="generated_commissions")
    
    # Origen del dinero (Venta, Clase, Tarea...)
    # Usaremos GenericForeignKey más adelante si es necesario, por ahora texto descriptivo simple para no complicar migraciones
    concept = models.CharField(max_length=255, help_text="Descripción del origen (ej: Venta Bono #123)")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.user.first_name}: {self.amount}€ ({self.concept})"


class StaffTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        COMPLETED = "COMPLETED", "Completada (Revisar)"
        VERIFIED = "VERIFIED", "Verificada (Pagada)"
        CANCELLED = "CANCELLED", "Cancelada"

    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="staff_tasks")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_tasks")
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    incentive_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Recompensa al completar")
    due_date = models.DateTimeField(null=True, blank=True)
    
    # Asignación (Prioridad: Individual > Rol > Global)
    assigned_to = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks", help_text="Asignación directa")
    assigned_role = models.CharField(max_length=20, choices=StaffProfile.Role.choices, blank=True, help_text="Para todo un rol")
    is_global = models.BooleanField(default=False, help_text="Visible para todo el staff")

    # Estado
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    completed_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="completed_tasks")
    completed_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class WorkShift(models.Model):
    class Method(models.TextChoices):
        WEB = "WEB", "Web Dashboard"
        TABLET = "TABLET", "Kiosco Tablet"
        MANUAL = "MANUAL", "Manual Manager"
        MOBILE = "MOBILE", "Móvil (GPS)"
        AUTO = "AUTO", "Automático"

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="shifts")
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.WEB)
    location_info = models.JSONField(default=dict, blank=True, help_text="Snapshot de ubicación o IP")
    
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_time"]
        verbose_name = "Turno de Trabajo"
        verbose_name_plural = "Turnos de Trabajo"

    def __str__(self):
        return f"{self.staff.user.get_full_name()} - {self.start_time.strftime('%d/%m %H:%M')}"
    
    @property
    def duration_hours(self):
        if self.end_time:
            diff = self.end_time - self.start_time
            return round(diff.total_seconds() / 3600, 2)
        return 0.0
