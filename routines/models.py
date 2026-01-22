from django.db import models
from django.utils.translation import gettext_lazy as _
from organizations.models import Gym

class Exercise(models.Model):
    MUSCLE_GROUPS = [
        ('CHEST', 'Pecho'),
        ('BACK', 'Espalda'),
        ('LEGS', 'Piernas'),
        ('ARMS', 'Brazos'),
        ('SHOULDERS', 'Hombros'),
        ('CORE', 'Core'),
        ('CARDIO', 'Cardio'),
        ('FULL_BODY', 'Cuerpo Completo'),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='exercises', default=1)
    name = models.CharField(_("Nombre"), max_length=100)
    description = models.TextField(_("Descripción/Técnica"), blank=True)
    muscle_group = models.CharField(_("Grupo Muscular"), max_length=20, choices=MUSCLE_GROUPS, default='FULL_BODY')
    video_url = models.URLField(_("Video URL"), blank=True, help_text="YouTube/Vimeo")
    tags = models.ManyToManyField('ExerciseTag', blank=True, related_name='exercises')
    
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Ejercicio"
        verbose_name_plural = "Ejercicios"

class ExerciseTag(models.Model):
    name = models.CharField(max_length=50)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='exercise_tags')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Etiqueta de Ejercicio"
        verbose_name_plural = "Etiquetas de Ejercicio"


class WorkoutRoutine(models.Model):
    GOALS = [
        ('STRENGTH', 'Fuerza'),
        ('HYPERTROPHY', 'Hipertrofia'),
        ('ENDURANCE', 'Resistencia'),
        ('WEIGHT_LOSS', 'Pérdida Peso'),
        ('GENERAL', 'General'),
    ]
    DIFFICULTY = [
        ('BEGINNER', 'Principiante'),
        ('INTERMEDIATE', 'Intermedio'),
        ('ADVANCED', 'Avanzado'),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='routines', default=1)
    name = models.CharField(_("Nombre Rutina"), max_length=100)
    description = models.TextField(_("Descripción"), blank=True)
    goal = models.CharField(_("Objetivo"), max_length=20, choices=GOALS, default='GENERAL')
    difficulty = models.CharField(_("Nivel"), max_length=20, choices=DIFFICULTY, default='BEGINNER')
    
    is_template = models.BooleanField(_("Es Plantilla"), default=True, help_text="Si es True, puede asignarse a múltiples clientes.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = "Rutina"
        verbose_name_plural = "Rutinas"

class RoutineDay(models.Model):
    routine = models.ForeignKey(WorkoutRoutine, on_delete=models.CASCADE, related_name='days')
    name = models.CharField(_("Nombre Día"), max_length=50, default="Día 1")
    order = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return f"{self.routine.name} - {self.name}"
    
    class Meta:
        ordering = ['order']
        verbose_name = "Día de Rutina"
        verbose_name_plural = "Días de Rutina"

class RoutineExercise(models.Model):
    day = models.ForeignKey(RoutineDay, on_delete=models.CASCADE, related_name='exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)
    
    sets = models.CharField(_("Series"), max_length=50, blank=True, help_text="Ej: 3, 4, o '3-4'")
    reps = models.CharField(_("Repeticiones"), max_length=50, blank=True, help_text="Ej: 8-12, 10, 'Fallo'")
    rest = models.CharField(_("Descanso"), max_length=50, blank=True, help_text="Ej: 60s, 2m")
    notes = models.CharField(_("Notas"), max_length=255, blank=True)
    
    def __str__(self):
        return f"{self.exercise.name} ({self.sets}x{self.reps})"
    
    class Meta:
        ordering = ['order']
        verbose_name = "Ejercicio de Rutina"
        verbose_name_plural = "Ejercicios de Rutina"
        
class ClientRoutine(models.Model):
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='routines')
    routine = models.ForeignKey(WorkoutRoutine, on_delete=models.CASCADE)
    
    start_date = models.DateField(_("Fecha Inicio"), auto_now_add=True)
    end_date = models.DateField(_("Fecha Fin"), null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.client} - {self.routine}"
    
    class Meta:
        verbose_name = "Asignación de Rutina"
        verbose_name_plural = "Asignaciones de Rutina"
