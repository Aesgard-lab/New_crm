from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from organizations.models import Gym
from clients.models import Client

class GamificationSettings(models.Model):
    """Configuración del sistema de gamificación por gimnasio"""
    gym = models.OneToOneField(Gym, on_delete=models.CASCADE, related_name='gamification_settings')
    
    # Activación
    enabled = models.BooleanField(default=False, help_text="Activar sistema de gamificación")
    
    # XP por acciones
    xp_per_attendance = models.IntegerField(default=10, help_text="XP por asistir a una clase")
    xp_per_routine_completion = models.IntegerField(default=15, help_text="XP por completar rutina del día")
    xp_per_review = models.IntegerField(default=10, help_text="XP por dejar review")
    xp_per_referral = models.IntegerField(default=100, help_text="XP por traer un amigo")
    
    # Configuración de niveles
    xp_per_level = models.IntegerField(default=100, help_text="XP necesario por nivel (escala lineal)")
    max_level = models.IntegerField(default=50, help_text="Nivel máximo alcanzable")
    
    # Visibilidad
    show_leaderboard = models.BooleanField(default=True, help_text="Mostrar tabla de clasificación")
    show_on_portal = models.BooleanField(default=True, help_text="Mostrar en portal del cliente")
    show_on_app = models.BooleanField(default=True, help_text="Mostrar en app móvil")
    hide_leaderboard_names = models.BooleanField(default=False, help_text="Ocultar nombres de otros clientes en el ranking (solo mostrar iniciales)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Gamificación {self.gym.name} - {'✅ Activo' if self.enabled else '❌ Inactivo'}"
    
    class Meta:
        verbose_name = "Configuración de Gamificación"
        verbose_name_plural = "Configuraciones de Gamificación"


class ClientProgress(models.Model):
    """Progreso individual de cada cliente"""
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='progress')
    
    # XP y Nivel
    total_xp = models.IntegerField(default=0, help_text="Puntos de experiencia totales")
    current_level = models.IntegerField(default=1, help_text="Nivel actual")
    
    # Estadísticas
    total_visits = models.IntegerField(default=0, help_text="Total de asistencias")
    total_reviews = models.IntegerField(default=0, help_text="Total de reviews dejadas")
    total_referrals = models.IntegerField(default=0, help_text="Total de amigos referidos")
    total_routines_completed = models.IntegerField(default=0, help_text="Rutinas completadas")
    
    # Racha actual
    current_streak = models.IntegerField(default=0, help_text="Días consecutivos con asistencia")
    longest_streak = models.IntegerField(default=0, help_text="Récord personal de racha")
    last_visit_date = models.DateField(null=True, blank=True, help_text="Última fecha de asistencia")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.client.first_name} - Nivel {self.current_level} ({self.total_xp} XP)"
    
    def add_xp(self, amount, reason=""):
        """Añade XP y calcula si sube de nivel"""
        from .signals import client_leveled_up
        
        old_level = self.current_level
        self.total_xp += amount
        
        # Calcular nuevo nivel
        settings = self.client.gym.gamification_settings
        self.current_level = min(
            (self.total_xp // settings.xp_per_level) + 1,
            settings.max_level
        )
        
        self.save()
        
        # Si subió de nivel, disparar señal
        if self.current_level > old_level:
            client_leveled_up.send(
                sender=self.__class__,
                instance=self,
                old_level=old_level,
                new_level=self.current_level
            )
        
        # Registrar transacción
        XPTransaction.objects.create(
            client=self.client,
            amount=amount,
            reason=reason,
            balance_after=self.total_xp
        )
        
        return self.current_level > old_level  # True si subió de nivel
    
    def xp_to_next_level(self):
        """Calcula XP necesario para el siguiente nivel"""
        settings = self.client.gym.gamification_settings
        next_level_xp = self.current_level * settings.xp_per_level
        return next_level_xp - self.total_xp
    
    def level_progress_percentage(self):
        """Porcentaje de progreso hacia el siguiente nivel"""
        settings = self.client.gym.gamification_settings
        current_level_xp = (self.current_level - 1) * settings.xp_per_level
        next_level_xp = self.current_level * settings.xp_per_level
        level_xp_range = next_level_xp - current_level_xp
        xp_in_level = self.total_xp - current_level_xp
        return int((xp_in_level / level_xp_range) * 100) if level_xp_range > 0 else 0
    
    def update_streak(self, visit_date):
        """Actualiza la racha de asistencia"""
        if not self.last_visit_date:
            self.current_streak = 1
            self.longest_streak = 1
        else:
            days_diff = (visit_date - self.last_visit_date).days
            
            if days_diff == 1:
                # Día consecutivo
                self.current_streak += 1
                self.longest_streak = max(self.longest_streak, self.current_streak)
            elif days_diff == 0:
                # Mismo día, no hacer nada
                pass
            else:
                # Se rompió la racha
                self.current_streak = 1
        
        self.last_visit_date = visit_date
        self.save()
    
    def get_rank_badge(self):
        """Retorna el badge/rango según el nivel"""
        if self.current_level >= 31:
            return {'name': 'Leyenda', 'icon': '💎', 'color': 'text-purple-600'}
        elif self.current_level >= 21:
            return {'name': 'Maestro', 'icon': '🏆', 'color': 'text-yellow-500'}
        elif self.current_level >= 11:
            return {'name': 'Experto', 'icon': '⭐', 'color': 'text-yellow-600'}
        elif self.current_level >= 6:
            return {'name': 'Aprendiz', 'icon': '🥈', 'color': 'text-slate-400'}
        else:
            return {'name': 'Novato', 'icon': '🥉', 'color': 'text-amber-600'}
    
    class Meta:
        verbose_name = "Progreso del Cliente"
        verbose_name_plural = "Progresos de Clientes"
        ordering = ['-total_xp']


class Achievement(models.Model):
    """Plantillas de logros/insignias disponibles"""
    CATEGORY_CHOICES = [
        ('ATTENDANCE', 'Asistencia'),
        ('STREAK', 'Rachas'),
        ('SOCIAL', 'Social'),
        ('VARIETY', 'Variedad'),
        ('REVIEWS', 'Reviews'),
        ('SPECIAL', 'Especial'),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='achievements')
    
    # Identificador único
    code = models.CharField(max_length=50, help_text="Código único (ej: FIRST_CLASS, WEEK_WARRIOR)")
    
    # Información
    name = models.CharField(max_length=100, help_text="Nombre del logro")
    description = models.TextField(help_text="Descripción de cómo conseguirlo")
    icon = models.CharField(max_length=10, default="🏅", help_text="Emoji del logro")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='ATTENDANCE')
    
    # Recompensa
    xp_reward = models.IntegerField(default=50, help_text="XP que otorga al desbloquearlo")
    
    # Condiciones (almacenadas como JSON o campos específicos)
    requirement_type = models.CharField(max_length=50, help_text="Tipo de requisito (ej: total_visits, current_streak)")
    requirement_value = models.IntegerField(help_text="Valor necesario para desbloquear")
    
    # Visibilidad
    is_active = models.BooleanField(default=True)
    is_secret = models.BooleanField(default=False, help_text="Logro secreto (no visible hasta desbloquearlo)")
    
    # Orden
    order = models.IntegerField(default=0, help_text="Orden de visualización")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.icon} {self.name}"
    
    class Meta:
        verbose_name = "Logro"
        verbose_name_plural = "Logros"
        ordering = ['order', 'name']
        unique_together = ['gym', 'code']


class ClientAchievement(models.Model):
    """Logros desbloqueados por cada cliente"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    
    unlocked_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.client.first_name} - {self.achievement.name}"
    
    class Meta:
        verbose_name = "Logro Desbloqueado"
        verbose_name_plural = "Logros Desbloqueados"
        unique_together = ['client', 'achievement']
        ordering = ['-unlocked_at']


class Challenge(models.Model):
    """Desafíos temporales/eventos especiales"""
    TARGET_TYPE_CHOICES = [
        ('ATTENDANCE_COUNT', 'Número de asistencias'),
        ('STREAK_DAYS', 'Días de racha'),
        ('SPECIFIC_ACTIVITY', 'Actividad específica'),
        ('TOTAL_XP', 'Puntos de experiencia'),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='challenges')
    
    # Información
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='challenges/', null=True, blank=True)
    
    # Fechas
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Objetivo
    target_type = models.CharField(max_length=30, choices=TARGET_TYPE_CHOICES)
    target_value = models.IntegerField(help_text="Valor objetivo del desafío")
    
    # Recompensas
    reward_xp = models.IntegerField(default=0, help_text="XP al completar")
    reward_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Descuento en euros")
    
    # Participantes
    participants = models.ManyToManyField(Client, through='ChallengeParticipation', related_name='challenges')
    
    # Estado
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} ({self.start_date} - {self.end_date})"
    
    def is_ongoing(self):
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    
    class Meta:
        verbose_name = "Desafío"
        verbose_name_plural = "Desafíos"
        ordering = ['-start_date']


class ChallengeParticipation(models.Model):
    """Participación de clientes en desafíos"""
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    
    # Progreso
    current_progress = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    joined_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.client.first_name} - {self.challenge.title} ({self.current_progress}/{self.challenge.target_value})"
    
    def progress_percentage(self):
        if self.challenge.target_value == 0:
            return 0
        return int((self.current_progress / self.challenge.target_value) * 100)
    
    class Meta:
        verbose_name = "Participación en Desafío"
        verbose_name_plural = "Participaciones en Desafíos"
        unique_together = ['challenge', 'client']


class XPTransaction(models.Model):
    """Historial de transacciones de XP"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='xp_transactions')
    
    amount = models.IntegerField(help_text="Cantidad de XP ganado (positivo) o perdido (negativo)")
    reason = models.CharField(max_length=255, help_text="Razón de la transacción")
    balance_after = models.IntegerField(help_text="Balance total después de la transacción")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.client.first_name} - {'+' if self.amount >= 0 else ''}{self.amount} XP - {self.reason}"
    
    class Meta:
        verbose_name = "Transacción de XP"
        verbose_name_plural = "Transacciones de XP"
        ordering = ['-created_at']
