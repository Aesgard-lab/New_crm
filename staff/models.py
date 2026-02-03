from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import re


# Validador para asegurar que el PIN solo contenga dígitos
pin_validator = RegexValidator(
    regex=r'^\d{4,6}$',
    message='El PIN debe contener solo dígitos (4-6 caracteres)',
    code='invalid_pin'
)


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
    pin_code = models.CharField(
        max_length=6, 
        blank=True, 
        null=True, 
        validators=[pin_validator],
        help_text="PIN de 4-6 dígitos para fichar en Tablet (debe ser único en el gimnasio)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("view_staffkiosk", "Ver Kiosco de Fichaje"),
            ("access_staffkiosk", "Acceder al Kiosco de Fichaje"),
            ("manage_roles", "Gestionar Roles y Permisos"),
            ("view_incentive", "Ver Incentivos y Comisiones"),
        ]
        # Restricción única compuesta: PIN + Gimnasio
        constraints = [
            models.UniqueConstraint(
                fields=['gym', 'pin_code'],
                name='unique_pin_per_gym',
                condition=models.Q(pin_code__isnull=False) & ~models.Q(pin_code=''),
                violation_error_message='Este PIN ya está en uso por otro empleado de este gimnasio.'
            )
        ]

    def clean(self):
        """Validación personalizada para el PIN"""
        super().clean()
        
        if self.pin_code:
            # Validar que el PIN solo contenga dígitos
            if not re.match(r'^\d{4,6}$', self.pin_code):
                raise ValidationError({
                    'pin_code': 'El PIN debe contener solo dígitos (4-6 caracteres).'
                })
            
            # Validar que no sea un PIN "fácil" (repetitivos o secuenciales)
            if self._is_weak_pin(self.pin_code):
                raise ValidationError({
                    'pin_code': 'El PIN es demasiado fácil. Evita secuencias (1234) o números repetidos (1111).'
                })
            
            # Validar unicidad del PIN dentro del mismo gimnasio
            qs = StaffProfile.objects.filter(
                gym=self.gym,
                pin_code=self.pin_code
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            
            if qs.exists():
                raise ValidationError({
                    'pin_code': 'Este PIN ya está en uso por otro empleado de este gimnasio.'
                })
    
    def _is_weak_pin(self, pin):
        """Detecta PINs débiles como secuencias o números repetidos"""
        # Todos los dígitos iguales (1111, 2222, etc.)
        if len(set(pin)) == 1:
            return True
        
        # Secuencias comunes ascendentes y descendentes
        weak_sequences = [
            '0123', '1234', '2345', '3456', '4567', '5678', '6789',
            '9876', '8765', '7654', '6543', '5432', '4321', '3210',
            '0000', '1111', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999',
            '012345', '123456', '234567', '345678', '456789',
            '987654', '876543', '765432', '654321', '543210',
        ]
        
        return pin in weak_sequences

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
    
    # Filtros de Actividad (Opcionales - Criterios independientes)
    activity = models.ForeignKey(
        "activities.Activity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incentive_rules",
        help_text="Actividad específica (dejar vacío para cualquier actividad)"
    )
    activity_category = models.ForeignKey(
        "activities.ActivityCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incentive_rules",
        help_text="Categoría completa (dejar vacío si seleccionas actividad específica)"
    )
    
    # Filtros de Horario (Opcionales)
    time_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Hora inicio de la franja (ej: 06:00)"
    )
    time_end = models.TimeField(
        null=True,
        blank=True,
        help_text="Hora fin de la franja (ej: 12:00)"
    )
    
    # Filtros de Días de la Semana (Opcional)
    weekdays = models.JSONField(
        default=list,
        blank=True,
        help_text="Array de días: ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']. Vacío = todos los días"
    )
    
    criteria = models.JSONField(default=dict, blank=True, help_text="Otros filtros JSON (ej: product_type='membership')")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()}: {self.value})"
    
    def get_filters_summary(self):
        """Retorna resumen legible de los filtros aplicados"""
        filters = []
        
        if self.activity:
            filters.append(f"Actividad: {self.activity.name}")
        elif self.activity_category:
            filters.append(f"Categoría: {self.activity_category.name}")
        
        if self.time_start and self.time_end:
            filters.append(f"Horario: {self.time_start.strftime('%H:%M')}-{self.time_end.strftime('%H:%M')}")
        
        if self.weekdays:
            days_map = {
                'MON': 'Lun', 'TUE': 'Mar', 'WED': 'Mié',
                'THU': 'Jue', 'FRI': 'Vie', 'SAT': 'Sáb', 'SUN': 'Dom'
            }
            days_str = ', '.join([days_map.get(d, d) for d in self.weekdays])
            filters.append(f"Días: {days_str}")
        
        return ' | '.join(filters) if filters else 'Sin filtros específicos'
    
    def matches_session(self, session):
        """Verifica si una sesión cumple con los criterios de este incentivo"""
        # Verificar actividad
        if self.activity and session.activity_id != self.activity_id:
            return False
        
        # Verificar categoría
        if self.activity_category and session.activity.category_id != self.activity_category_id:
            return False
        
        # Verificar horario
        if self.time_start and self.time_end:
            session_time = session.start_datetime.time()
            if not (self.time_start <= session_time <= self.time_end):
                return False
        
        # Verificar día de la semana
        if self.weekdays:
            weekday_map = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
            session_weekday = weekday_map[session.start_datetime.weekday()]
            if session_weekday not in self.weekdays:
                return False
        
        return True
    
    class Meta:
        permissions = [
            ("view_all_incentives", "Ver Incentivos de Todo el Staff"),
            ("view_own_incentives", "Ver Solo Incentivos Propios"),
        ]


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
    
    @staticmethod
    def calculate_for_session(session):
        """
        Calcula y crea comisiones para una sesión de clase completada.
        Busca todas las reglas activas que coincidan con la sesión.
        
        Args:
            session: ActivitySession instance
            
        Returns:
            list: Lista de StaffCommission creadas
        """
        if not session.staff:
            return []
        
        commissions_created = []
        gym = session.gym
        staff = session.staff
        
        # Buscar reglas activas que apliquen (globales o específicas del staff)
        rules = IncentiveRule.objects.filter(
            gym=gym,
            is_active=True,
            type__in=['CLASS_FIXED', 'CLASS_ATTENDANCE']  # Solo reglas de clases
        ).filter(
            models.Q(staff__isnull=True) | models.Q(staff=staff)
        )
        
        for rule in rules:
            # Verificar si la sesión cumple los criterios
            if not rule.matches_session(session):
                continue
            
            # Calcular monto según tipo
            amount = 0
            if rule.type == 'CLASS_FIXED':
                amount = rule.value
            elif rule.type == 'CLASS_ATTENDANCE':
                attendee_count = session.attendee_count
                amount = rule.value * attendee_count
            
            if amount > 0:
                # Crear comisión
                commission = StaffCommission.objects.create(
                    staff=staff,
                    rule=rule,
                    concept=f"Clase: {session.activity.name} - {session.start_datetime.strftime('%d/%m/%Y %H:%M')}",
                    amount=amount
                )
                commissions_created.append(commission)
        
        return commissions_created


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


class StaffExpectedSchedule(models.Model):
    """
    Horario esperado/programado para el staff.
    Define cuándo se espera que un empleado fiche.
    """
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, "Lunes"
        TUESDAY = 1, "Martes"
        WEDNESDAY = 2, "Miércoles"
        THURSDAY = 3, "Jueves"
        FRIDAY = 4, "Viernes"
        SATURDAY = 5, "Sábado"
        SUNDAY = 6, "Domingo"
    
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="expected_schedules")
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    
    start_time = models.TimeField(help_text="Hora esperada de entrada")
    end_time = models.TimeField(help_text="Hora esperada de salida")
    
    is_active = models.BooleanField(default=True)
    
    # Tolerancia para alertas
    grace_minutes = models.IntegerField(
        default=15, 
        help_text="Minutos de tolerancia antes de generar alerta"
    )
    
    class Meta:
        verbose_name = "Horario Esperado"
        verbose_name_plural = "Horarios Esperados"
        unique_together = ['staff', 'day_of_week']
        ordering = ['staff', 'day_of_week']
    
    def __str__(self):
        return f"{self.staff} - {self.get_day_of_week_display()} ({self.start_time}-{self.end_time})"


class MissingCheckinAlert(models.Model):
    """
    Registro de alertas cuando un empleado no fichó según su horario esperado.
    """
    class AlertType(models.TextChoices):
        NO_CHECKIN = "NO_CHECKIN", "No fichó entrada"
        LATE_CHECKIN = "LATE_CHECKIN", "Fichaje tardío"
        NO_CHECKOUT = "NO_CHECKOUT", "No fichó salida"
        EARLY_CHECKOUT = "EARLY_CHECKOUT", "Salida anticipada"
    
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="checkin_alerts")
    date = models.DateField()
    alert_type = models.CharField(max_length=20, choices=AlertType.choices)
    
    expected_time = models.TimeField(null=True, blank=True, help_text="Hora esperada según horario")
    actual_time = models.TimeField(null=True, blank=True, help_text="Hora real del fichaje (si aplica)")
    
    is_resolved = models.BooleanField(default=False, help_text="El manager revisó/justificó esta alerta")
    resolution_notes = models.TextField(blank=True, help_text="Notas del manager sobre la resolución")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="resolved_checkin_alerts"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Alerta de Fichaje"
        verbose_name_plural = "Alertas de Fichaje"
        ordering = ["-date", "-created_at"]
        unique_together = ['staff', 'date', 'alert_type']
    
    def __str__(self):
        return f"{self.staff} - {self.date} - {self.get_alert_type_display()}"


class AuditLog(models.Model):
    """
    Simple system audit log to track user actions.
    """
    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="audit_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    
    action = models.CharField(max_length=50) # LOGIN, CREATE, UPDATE, DELETE
    module = models.CharField(max_length=50) # Clients, Billing, Staff...
    target = models.CharField(max_length=255, blank=True) # "Client: John Doe"
    
    details = models.TextField(blank=True, help_text="JSON or text details")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"

    def __str__(self):
        return f"[{self.timestamp}] {self.user} - {self.action} {self.module}"


class RatingIncentive(models.Model):
    """
    Incentive configuration based on class review ratings.
    Allows setting bonuses for instructors based on their average ratings.
    """
    class Level(models.TextChoices):
        BRONZE = "BRONZE", "Bronce (4.0-4.29)"
        SILVER = "SILVER", "Plata (4.3-4.49)"
        GOLD = "GOLD", "Oro (4.5-4.79)"
        PLATINUM = "PLATINUM", "Platino (4.8-5.0)"
    
    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="rating_incentives")
    staff = models.ForeignKey(
        StaffProfile, 
        on_delete=models.CASCADE, 
        related_name="rating_incentives", 
        null=True, 
        blank=True,
        help_text="Si se especifica, aplica solo a este empleado. Si no, es global del gym."
    )
    
    # Bonus configuration
    min_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        help_text="Rating mínimo requerido (ej: 4.5)"
    )
    bonus_type = models.CharField(
        max_length=20,
        choices=[
            ('PERCENTAGE', 'Porcentaje del Salario Base'),
            ('FIXED', 'Cantidad Fija')
        ],
        default='PERCENTAGE'
    )
    bonus_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Porcentaje (5-15) o Cantidad Fija en euros"
    )
    
    # Performance tier
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        null=True,
        blank=True,
        help_text="Nivel de rendimiento asociado"
    )
    
    # Requirements
    min_reviews = models.IntegerField(
        default=10,
        help_text="Mínimo de reviews necesarias para aplicar el incentivo"
    )
    
    period_days = models.IntegerField(
        default=30,
        help_text="Período en días para calcular el promedio (30 = último mes)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-min_rating"]
        verbose_name = "Incentivo por Rating"
        verbose_name_plural = "Incentivos por Rating"
    
    def __str__(self):
        staff_name = self.staff.user.first_name if self.staff else "Global"
        return f"{staff_name} - Rating ≥{self.min_rating}: {self.bonus_value}{'%' if self.bonus_type == 'PERCENTAGE' else '€'}"
    
    def calculate_bonus(self, base_salary, avg_rating, total_reviews):
        """
        Calculate bonus amount for given parameters
        """
        if not self.is_active:
            return 0
        
        if total_reviews < self.min_reviews:
            return 0
        
        if avg_rating < float(self.min_rating):
            return 0
        
        if self.bonus_type == 'PERCENTAGE':
            return float(base_salary) * (float(self.bonus_value) / 100)
        else:
            return float(self.bonus_value)


# ==========================================
# VACATION & ABSENCE MANAGEMENT
# ==========================================

class AbsenceType(models.Model):
    """
    Types of absences: Vacation, Sick Leave, Personal Days, etc.
    """
    class Category(models.TextChoices):
        VACATION = "VACATION", "Vacaciones"
        SICK = "SICK", "Enfermedad / Baja Médica"
        PERSONAL = "PERSONAL", "Asuntos Propios"
        MATERNITY = "MATERNITY", "Maternidad / Paternidad"
        UNPAID = "UNPAID", "Permiso Sin Sueldo"
        TRAINING = "TRAINING", "Formación"
        OTHER = "OTHER", "Otro"
    
    gym = models.ForeignKey(
        "organizations.Gym", 
        on_delete=models.CASCADE, 
        related_name="absence_types"
    )
    name = models.CharField(max_length=100, help_text="Ej: Vacaciones, Baja Médica")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.VACATION)
    
    # Configuration
    is_paid = models.BooleanField(default=True, help_text="¿Se remunera este tipo de ausencia?")
    requires_approval = models.BooleanField(default=True, help_text="¿Requiere aprobación del manager?")
    requires_documentation = models.BooleanField(default=False, help_text="¿Requiere justificante?")
    deducts_from_balance = models.BooleanField(default=True, help_text="¿Descuenta del saldo de vacaciones?")
    
    color = models.CharField(max_length=7, default="#3b82f6", help_text="Color en calendario (HEX)")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Tipo de Ausencia"
        verbose_name_plural = "Tipos de Ausencia"
        ordering = ["name"]
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class VacationPolicy(models.Model):
    """
    Vacation policy configuration per gym.
    Defines how many days employees get and rules for requesting.
    """
    gym = models.OneToOneField(
        "organizations.Gym", 
        on_delete=models.CASCADE, 
        related_name="vacation_policy"
    )
    
    # Base allowance
    base_days_per_year = models.PositiveIntegerField(
        default=22, 
        help_text="Días de vacaciones base anuales (típico España: 22-30)"
    )
    
    # Seniority bonuses
    extra_days_per_year_worked = models.PositiveIntegerField(
        default=0,
        help_text="Días extra por cada año de antigüedad (ej: 1 día extra por año)"
    )
    max_seniority_days = models.PositiveIntegerField(
        default=5,
        help_text="Máximo de días extra por antigüedad"
    )
    
    # Carry-over rules
    allow_carry_over = models.BooleanField(
        default=True,
        help_text="¿Permitir arrastrar días no usados al siguiente año?"
    )
    max_carry_over_days = models.PositiveIntegerField(
        default=5,
        help_text="Máximo de días que se pueden arrastrar"
    )
    carry_over_deadline_months = models.PositiveIntegerField(
        default=3,
        help_text="Meses para usar los días arrastrados (ej: 3 = hasta marzo)"
    )
    
    # Request rules
    min_advance_days = models.PositiveIntegerField(
        default=15,
        help_text="Días mínimos de antelación para solicitar vacaciones"
    )
    min_consecutive_days = models.PositiveIntegerField(
        default=1,
        help_text="Mínimo de días consecutivos por solicitud"
    )
    max_consecutive_days = models.PositiveIntegerField(
        default=21,
        help_text="Máximo de días consecutivos por solicitud"
    )
    
    # Calendar settings
    count_weekends = models.BooleanField(
        default=False,
        help_text="¿Contar fines de semana como días de vacaciones?"
    )
    exclude_holidays = models.BooleanField(
        default=True,
        help_text="¿Excluir festivos del recuento?"
    )
    
    # Overlap control
    max_staff_absent_percent = models.PositiveIntegerField(
        default=30,
        help_text="% máximo del equipo que puede estar ausente simultáneamente"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Política de Vacaciones"
        verbose_name_plural = "Políticas de Vacaciones"
    
    def __str__(self):
        return f"Política de {self.gym.name}"
    
    def calculate_days_for_staff(self, staff_profile):
        """
        Calculate total vacation days for a staff member based on seniority.
        """
        from django.utils import timezone
        
        # Calculate years worked
        years_worked = 0
        if staff_profile.created_at:
            delta = timezone.now() - staff_profile.created_at
            years_worked = delta.days // 365
        
        # Calculate seniority bonus
        seniority_bonus = min(
            years_worked * self.extra_days_per_year_worked,
            self.max_seniority_days
        )
        
        return self.base_days_per_year + seniority_bonus


class StaffVacationBalance(models.Model):
    """
    Tracks vacation balance per staff member per year.
    """
    staff = models.ForeignKey(
        StaffProfile, 
        on_delete=models.CASCADE, 
        related_name="vacation_balances"
    )
    year = models.PositiveIntegerField(help_text="Año fiscal")
    
    # Allocation
    days_allocated = models.DecimalField(
        max_digits=5, 
        decimal_places=1, 
        default=0,
        help_text="Días asignados para el año"
    )
    days_carried_over = models.DecimalField(
        max_digits=5, 
        decimal_places=1, 
        default=0,
        help_text="Días arrastrados del año anterior"
    )
    days_adjustment = models.DecimalField(
        max_digits=5, 
        decimal_places=1, 
        default=0,
        help_text="Ajustes manuales (+/-)"
    )
    
    # Usage tracking
    days_used = models.DecimalField(
        max_digits=5, 
        decimal_places=1, 
        default=0,
        help_text="Días ya disfrutados"
    )
    days_pending = models.DecimalField(
        max_digits=5, 
        decimal_places=1, 
        default=0,
        help_text="Días en solicitudes pendientes de aprobación"
    )
    
    notes = models.TextField(blank=True, help_text="Notas o comentarios")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Saldo de Vacaciones"
        verbose_name_plural = "Saldos de Vacaciones"
        unique_together = ["staff", "year"]
        ordering = ["-year", "staff__user__first_name"]
    
    def __str__(self):
        return f"{self.staff} - {self.year}: {self.days_available} días disponibles"
    
    @property
    def days_total(self):
        """Total days available for the year"""
        return float(self.days_allocated) + float(self.days_carried_over) + float(self.days_adjustment)
    
    @property
    def days_available(self):
        """Days remaining (not used and not pending)"""
        return self.days_total - float(self.days_used) - float(self.days_pending)
    
    @classmethod
    def get_or_create_for_year(cls, staff, year):
        """
        Get or create balance for a staff member for a specific year.
        Automatically calculates allocation based on policy.
        """
        balance, created = cls.objects.get_or_create(
            staff=staff,
            year=year,
            defaults={'days_allocated': 0}
        )
        
        if created:
            # Calculate allocation from policy
            try:
                policy = staff.gym.vacation_policy
                balance.days_allocated = policy.calculate_days_for_staff(staff)
                
                # Check for carry-over from previous year
                if policy.allow_carry_over:
                    try:
                        prev_balance = cls.objects.get(staff=staff, year=year - 1)
                        carry_over = min(
                            prev_balance.days_available,
                            policy.max_carry_over_days
                        )
                        if carry_over > 0:
                            balance.days_carried_over = carry_over
                    except cls.DoesNotExist:
                        pass
                
                balance.save()
            except VacationPolicy.DoesNotExist:
                # No policy defined, use default
                balance.days_allocated = 22
                balance.save()
        
        return balance


class VacationRequest(models.Model):
    """
    Individual vacation/absence request from a staff member.
    """
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        PENDING = "PENDING", "Pendiente de Aprobación"
        APPROVED = "APPROVED", "Aprobada"
        REJECTED = "REJECTED", "Rechazada"
        CANCELLED = "CANCELLED", "Cancelada"
    
    staff = models.ForeignKey(
        StaffProfile, 
        on_delete=models.CASCADE, 
        related_name="vacation_requests"
    )
    absence_type = models.ForeignKey(
        AbsenceType,
        on_delete=models.PROTECT,
        related_name="requests",
        help_text="Tipo de ausencia"
    )
    
    # Date range
    start_date = models.DateField(help_text="Fecha de inicio")
    end_date = models.DateField(help_text="Fecha de fin (inclusive)")
    
    # Calculated days
    working_days = models.DecimalField(
        max_digits=5, 
        decimal_places=1, 
        default=0,
        help_text="Días laborables solicitados (excluye fines de semana/festivos si aplica)"
    )
    
    # Request details
    reason = models.TextField(blank=True, help_text="Motivo o notas de la solicitud")
    documentation = models.FileField(
        upload_to="staff/vacation_docs/", 
        blank=True, 
        null=True,
        help_text="Justificante si es requerido"
    )
    
    # Status tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Approval workflow
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_vacation_requests"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, help_text="Motivo del rechazo si aplica")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Solicitud de Vacaciones"
        verbose_name_plural = "Solicitudes de Vacaciones"
        ordering = ["-created_at"]
        permissions = [
            ("approve_vacation", "Puede aprobar solicitudes de vacaciones"),
            ("view_all_vacations", "Ver vacaciones de todo el equipo"),
            ("view_own_vacations", "Ver solo sus propias vacaciones"),
        ]
    
    def __str__(self):
        return f"{self.staff} - {self.start_date} a {self.end_date} ({self.get_status_display()})"
    
    @property
    def duration_days(self):
        """Total calendar days"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0
    
    def calculate_working_days(self):
        """
        Calculate working days excluding weekends and holidays.
        """
        from django.utils import timezone
        import datetime
        
        if not self.start_date or not self.end_date:
            return 0
        
        try:
            policy = self.staff.gym.vacation_policy
        except VacationPolicy.DoesNotExist:
            policy = None
        
        working_days = 0
        current_date = self.start_date
        
        # Get holidays for the gym
        holidays = set()
        try:
            from organizations.models import GymHoliday
            gym_holidays = GymHoliday.objects.filter(
                gym=self.staff.gym,
                date__gte=self.start_date,
                date__lte=self.end_date
            )
            holidays = set(h.date for h in gym_holidays)
        except:
            pass
        
        while current_date <= self.end_date:
            is_weekend = current_date.weekday() >= 5  # Saturday = 5, Sunday = 6
            is_holiday = current_date in holidays
            
            # Count day based on policy
            count_day = True
            
            if policy:
                if not policy.count_weekends and is_weekend:
                    count_day = False
                if policy.exclude_holidays and is_holiday:
                    count_day = False
            else:
                # Default: exclude weekends
                if is_weekend:
                    count_day = False
            
            if count_day:
                working_days += 1
            
            current_date += datetime.timedelta(days=1)
        
        return working_days
    
    def save(self, *args, **kwargs):
        # Auto-calculate working days
        if not self.working_days or self.working_days == 0:
            self.working_days = self.calculate_working_days()
        super().save(*args, **kwargs)
    
    def approve(self, user):
        """Approve the request and update balance"""
        from django.utils import timezone
        
        if self.status != self.Status.PENDING:
            raise ValueError("Solo se pueden aprobar solicitudes pendientes")
        
        # Update balance
        if self.absence_type.deducts_from_balance:
            year = self.start_date.year
            balance = StaffVacationBalance.get_or_create_for_year(self.staff, year)
            balance.days_pending = float(balance.days_pending) - float(self.working_days)
            balance.days_used = float(balance.days_used) + float(self.working_days)
            balance.save()
        
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, user, reason=""):
        """Reject the request and restore pending balance"""
        from django.utils import timezone
        
        if self.status != self.Status.PENDING:
            raise ValueError("Solo se pueden rechazar solicitudes pendientes")
        
        # Restore pending balance
        if self.absence_type.deducts_from_balance:
            year = self.start_date.year
            balance = StaffVacationBalance.get_or_create_for_year(self.staff, year)
            balance.days_pending = float(balance.days_pending) - float(self.working_days)
            balance.save()
        
        self.status = self.Status.REJECTED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()
    
    def cancel(self):
        """Cancel the request"""
        if self.status == self.Status.APPROVED:
            # Restore used days
            if self.absence_type.deducts_from_balance:
                year = self.start_date.year
                balance = StaffVacationBalance.get_or_create_for_year(self.staff, year)
                balance.days_used = float(balance.days_used) - float(self.working_days)
                balance.save()
        elif self.status == self.Status.PENDING:
            # Restore pending days
            if self.absence_type.deducts_from_balance:
                year = self.start_date.year
                balance = StaffVacationBalance.get_or_create_for_year(self.staff, year)
                balance.days_pending = float(balance.days_pending) - float(self.working_days)
                balance.save()
        
        self.status = self.Status.CANCELLED
        self.save()


class BlockedVacationPeriod(models.Model):
    """
    Periods where vacations are not allowed (e.g., Christmas in retail).
    """
    gym = models.ForeignKey(
        "organizations.Gym", 
        on_delete=models.CASCADE, 
        related_name="blocked_vacation_periods"
    )
    name = models.CharField(max_length=100, help_text="Ej: Temporada Alta, Navidad")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    
    # Optional: allow for specific roles
    applies_to_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Roles afectados. Vacío = todos. Ej: ['TRAINER', 'RECEPTIONIST']"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Período Bloqueado"
        verbose_name_plural = "Períodos Bloqueados"
        ordering = ["start_date"]
    
    def __str__(self):
        return f"{self.name}: {self.start_date} - {self.end_date}"
    
    def affects_role(self, role):
        """Check if this block affects a specific role"""
        if not self.applies_to_roles:
            return True  # Empty = affects all
        return role in self.applies_to_roles
