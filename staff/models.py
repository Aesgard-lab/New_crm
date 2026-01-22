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

    class Meta:
        permissions = [
            ("view_staffkiosk", "Ver Kiosco de Fichaje"),
            ("access_staffkiosk", "Acceder al Kiosco de Fichaje"),
            ("manage_roles", "Gestionar Roles y Permisos"),
            ("view_incentive", "Ver Incentivos y Comisiones"),
        ]

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


