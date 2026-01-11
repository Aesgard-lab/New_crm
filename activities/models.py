from django.db import models
from django.utils.translation import gettext_lazy as _
from organizations.models import Gym
from staff.models import StaffProfile

class Room(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='rooms')
    name = models.CharField(_("Nombre de la Sala"), max_length=100)
    capacity = models.PositiveIntegerField(_("Aforo Máximo"))
    layout_configuration = models.JSONField(_("Configuración de Diseño"), default=dict, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.gym.name})"

class ActivityCategory(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='activity_categories', null=True, blank=True)
    name = models.CharField(_("Nombre"), max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    icon = models.ImageField(upload_to='activity_icons/', null=True, blank=True)
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

class Activity(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='activities')
    category = models.ForeignKey(ActivityCategory, on_delete=models.SET_NULL, null=True, related_name='activities')
    name = models.CharField(_("Nombre de la Actividad"), max_length=100)
    description = models.TextField(_("Descripción"), blank=True)
    image = models.ImageField(upload_to='activity_images/', null=True, blank=True)
    color = models.CharField(_("Color en Calendario"), max_length=7, default="#3B82F6", help_text="Código HEX (ej: #3B82F6)")
    duration = models.PositiveIntegerField(_("Duración (min)"), default=60)
    base_capacity = models.PositiveIntegerField(_("Aforo Base"), help_text=_("El aforo final dependerá de la sala"))
    intensity_level = models.CharField(_("Intensidad"), max_length=20, choices=[
        ('LOW', 'Baja'), ('MEDIUM', 'Media'), ('HIGH', 'Alta')
    ], default='MEDIUM')
    video_url = models.URLField(_("Video URL"), blank=True)
    
    eligible_staff = models.ManyToManyField(StaffProfile, related_name='qualified_activities', blank=True)
    cancellation_policy = models.ForeignKey('CancellationPolicy', on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')

    def __str__(self):
        return self.name

class CancellationPolicy(models.Model):
    PENALTY_CHOICES = [
        ('STRIKE', 'Strike (Falta)'),
        ('FEE', 'Cobro Monetario'),
        ('FORFEIT', 'Pérdida de Crédito'),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='cancellation_policies')
    name = models.CharField(_("Nombre de la Política"), max_length=100)
    window_hours = models.PositiveIntegerField(_("Ventana de Cancelación (Horas)"), help_text=_("Horas antes de la clase para cancelar sin penalización"))
    
    penalty_type = models.CharField(_("Tipo de Penalización"), max_length=20, choices=PENALTY_CHOICES, default='FORFEIT')
    fee_amount = models.DecimalField(_("Monto de Multa"), max_digits=6, decimal_places=2, null=True, blank=True, help_text=_("Solo si el tipo es Cobro Monetario"))
    
    
    def __str__(self):
        return f"{self.name} ({self.window_hours}h)"

class ScheduleRule(models.Model):
    """
    Defines a recurring schedule pattern (e.g. Yoga every Mon/Wed at 10:00).
    Used to generate ActivitySessions.
    """
    DAYS_OF_WEEK = [
        (0, _("Lunes")), (1, _("Martes")), (2, _("Miércoles")), 
        (3, _("Jueves")), (4, _("Viernes")), (5, _("Sábado")), (6, _("Domingo"))
    ]

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='schedule_rules')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='rules')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True)
    
    day_of_week = models.IntegerField(_("Día de la Semana"), choices=DAYS_OF_WEEK)
    start_time = models.TimeField(_("Hora Inicio"))
    end_time = models.TimeField(_("Hora Fin"))
    
    start_date = models.DateField(_("Vigente desde"), auto_now_add=True)
    end_date = models.DateField(_("Vigente hasta"), null=True, blank=True)
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        day_label = dict(self.DAYS_OF_WEEK).get(self.day_of_week, 'N/A')
        return f"{self.activity.name} - {day_label} {self.start_time}"

class ActivitySession(models.Model):
    """
    A specific instance of a class (e.g. Yoga on Jan 12th at 10:00).
    """
    STATUS_CHOICES = [
        ('SCHEDULED', _("Programada")),
        ('CANCELLED', _("Cancelada")),
        ('COMPLETED', _("Completada")),
    ]

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='sessions')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='sessions')
    rule = models.ForeignKey(ScheduleRule, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_sessions')
    
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True)
    
    start_datetime = models.DateTimeField(_("Inicio"))
    end_datetime = models.DateTimeField(_("Fin"))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    
    # Capacity management (snapshot from Activity/Room, but editable per session)
    max_capacity = models.PositiveIntegerField(_("Aforo Máximo"), default=0)
    
    attendees = models.ManyToManyField('clients.Client', related_name='attended_sessions', blank=True)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_datetime']

    def __str__(self):
        return f"{self.activity.name} - {self.start_datetime.strftime('%d/%m %H:%M')}"
    
    @property
    def attendee_count(self):
        return self.attendees.count()
    
    @property
    def utilization_percent(self):
        if self.max_capacity == 0: return 0
        return (self.attendees.count() / self.max_capacity) * 100

