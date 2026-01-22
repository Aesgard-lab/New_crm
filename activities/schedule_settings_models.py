from django.db import models
from django.utils.translation import gettext_lazy as _
from organizations.models import Gym


class ScheduleSettings(models.Model):
    """
    Configuración del sistema de horarios y programación de clases.
    Controla validaciones y restricciones para evitar conflictos.
    """
    gym = models.OneToOneField(
        Gym,
        on_delete=models.CASCADE,
        related_name='schedule_settings',
        verbose_name=_("Gimnasio")
    )
    
    # === VALIDACIONES DE CONFLICTOS ===
    allow_room_overlaps = models.BooleanField(
        default=False,
        verbose_name=_("Permitir solapamiento de salas"),
        help_text=_("Si está desactivado, no se podrán crear clases simultáneas en la misma sala")
    )
    
    allow_staff_overlaps = models.BooleanField(
        default=False,
        verbose_name=_("Permitir solapamiento de instructores"),
        help_text=_("Si está desactivado, un instructor no podrá impartir dos clases a la vez")
    )
    
    # === RESTRICCIONES DE TIEMPO ===
    min_break_between_classes = models.IntegerField(
        default=0,
        verbose_name=_("Descanso mínimo entre clases (minutos)"),
        help_text=_("Tiempo mínimo que debe pasar entre dos clases del mismo instructor")
    )
    
    max_consecutive_classes = models.IntegerField(
        default=0,
        verbose_name=_("Máximo de clases consecutivas"),
        help_text=_("Número máximo de clases seguidas que puede impartir un instructor (0 = sin límite)")
    )
    
    # === RESTRICCIONES DE CAPACIDAD ===
    min_capacity_to_run = models.IntegerField(
        default=1,
        verbose_name=_("Capacidad mínima para realizar clase"),
        help_text=_("Número mínimo de reservas necesarias para que la clase se realice")
    )
    
    auto_cancel_low_attendance = models.BooleanField(
        default=False,
        verbose_name=_("Cancelar automáticamente clases con baja asistencia"),
        help_text=_("Cancelar clases que no alcancen la capacidad mínima")
    )
    
    hours_before_auto_cancel = models.IntegerField(
        default=24,
        verbose_name=_("Horas antes para auto-cancelar"),
        help_text=_("Cuántas horas antes de la clase verificar la asistencia mínima")
    )
    
    # === RESERVAS Y CANCELACIONES ===
    max_advance_booking_days = models.IntegerField(
        default=30,
        verbose_name=_("Días máximos de antelación para reservar"),
        help_text=_("Cuántos días de antelación pueden reservar los clientes (0 = sin límite)")
    )
    
    min_advance_booking_hours = models.IntegerField(
        default=0,
        verbose_name=_("Horas mínimas de antelación para reservar"),
        help_text=_("Mínimo de horas de antelación para hacer una reserva")
    )
    
    allow_cancellation = models.BooleanField(
        default=True,
        verbose_name=_("Permitir cancelación de reservas"),
        help_text=_("Los clientes pueden cancelar sus reservas")
    )
    
    cancellation_deadline_hours = models.IntegerField(
        default=2,
        verbose_name=_("Plazo para cancelar (horas)"),
        help_text=_("Horas mínimas de antelación para cancelar sin penalización")
    )
    
    # === LISTAS DE ESPERA ===
    enable_waitlist = models.BooleanField(
        default=True,
        verbose_name=_("Habilitar lista de espera"),
        help_text=_("Permitir lista de espera cuando una clase está llena")
    )
    
    max_waitlist_size = models.IntegerField(
        default=10,
        verbose_name=_("Tamaño máximo de lista de espera"),
        help_text=_("Número máximo de personas en lista de espera (0 = sin límite)")
    )
    
    auto_assign_from_waitlist = models.BooleanField(
        default=True,
        verbose_name=_("Asignar automáticamente desde lista de espera"),
        help_text=_("Asignar plaza automáticamente cuando alguien cancela")
    )
    
    # === NOTIFICACIONES ===
    notify_class_changes = models.BooleanField(
        default=True,
        verbose_name=_("Notificar cambios de clases"),
        help_text=_("Enviar notificaciones cuando se modifica o cancela una clase")
    )
    
    notify_instructor_assignments = models.BooleanField(
        default=True,
        verbose_name=_("Notificar asignaciones a instructores"),
        help_text=_("Notificar a instructores cuando se les asigna una clase")
    )
    
    reminder_hours_before = models.IntegerField(
        default=2,
        verbose_name=_("Recordatorio (horas antes)"),
        help_text=_("Enviar recordatorio X horas antes de la clase (0 = desactivado)")
    )
    
    # === RESTRICCIONES DE HORARIO ===
    enforce_opening_hours = models.BooleanField(
        default=True,
        verbose_name=_("Respetar horario de apertura"),
        help_text=_("Las clases deben estar dentro del horario de apertura del gimnasio")
    )
    
    allow_late_checkin = models.BooleanField(
        default=True,
        verbose_name=_("Permitir check-in tardío"),
        help_text=_("Permitir check-in después de que haya empezado la clase")
    )
    
    late_checkin_grace_minutes = models.IntegerField(
        default=10,
        verbose_name=_("Minutos de gracia para llegar tarde"),
        help_text=_("Cuántos minutos después del inicio se permite el check-in")
    )
    
    # === METADATOS ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Configuración de Horarios")
        verbose_name_plural = _("Configuraciones de Horarios")
        
    def __str__(self):
        return f"Configuración de horarios - {self.gym.name}"
    
    @classmethod
    def get_for_gym(cls, gym):
        """Obtener o crear configuración para un gimnasio"""
        config, created = cls.objects.get_or_create(gym=gym)
        return config
