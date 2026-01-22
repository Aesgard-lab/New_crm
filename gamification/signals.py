from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from clients.models import ClientVisit
from activities.models import ClassReview

# Señal personalizada para cuando un cliente sube de nivel
client_leveled_up = Signal()

@receiver(post_save, sender=ClientVisit)
def award_xp_for_attendance(sender, instance, created, **kwargs):
    """Otorga XP cuando un cliente asiste a una clase"""
    if not created:
        return
    
    client = instance.client
    gym = client.gym
    
    # Verificar si la gamificación está activa
    try:
        settings = gym.gamification_settings
        if not settings.enabled:
            return
    except:
        return
    
    # Obtener o crear progreso del cliente
    from .models import ClientProgress
    progress, _ = ClientProgress.objects.get_or_create(client=client)
    
    # Añadir XP
    progress.add_xp(
        amount=settings.xp_per_attendance,
        reason=f"Asistencia a clase"
    )
    
    # Actualizar estadísticas
    progress.total_visits += 1
    progress.update_streak(instance.timestamp.date())
    progress.save()
    
    # Verificar logros relacionados con asistencia
    check_achievements_for_client(client)


@receiver(post_save, sender=ClassReview)
def award_xp_for_review(sender, instance, created, **kwargs):
    """Otorga XP cuando un cliente deja una review"""
    if not created:
        return
    
    client = instance.client
    gym = client.gym
    
    # Verificar si la gamificación está activa
    try:
        settings = gym.gamification_settings
        if not settings.enabled:
            return
    except:
        return
    
    # Obtener o crear progreso del cliente
    from .models import ClientProgress
    progress, _ = ClientProgress.objects.get_or_create(client=client)
    
    # Añadir XP
    progress.add_xp(
        amount=settings.xp_per_review,
        reason=f"Review de clase"
    )
    
    # Actualizar estadísticas
    progress.total_reviews += 1
    progress.save()
    
    # Verificar logros relacionados con reviews
    check_achievements_for_client(client)


def check_achievements_for_client(client):
    """Verifica y desbloquea logros para un cliente"""
    from .models import Achievement, ClientAchievement, ClientProgress
    
    try:
        progress = client.progress
    except ClientProgress.DoesNotExist:
        return
    
    # Obtener logros activos del gimnasio
    achievements = Achievement.objects.filter(gym=client.gym, is_active=True)
    
    for achievement in achievements:
        # Verificar si ya lo tiene
        if ClientAchievement.objects.filter(client=client, achievement=achievement).exists():
            continue
        
        # Verificar si cumple los requisitos
        should_unlock = False
        
        if achievement.requirement_type == 'total_visits':
            should_unlock = progress.total_visits >= achievement.requirement_value
        elif achievement.requirement_type == 'current_streak':
            should_unlock = progress.current_streak >= achievement.requirement_value
        elif achievement.requirement_type == 'longest_streak':
            should_unlock = progress.longest_streak >= achievement.requirement_value
        elif achievement.requirement_type == 'total_reviews':
            should_unlock = progress.total_reviews >= achievement.requirement_value
        elif achievement.requirement_type == 'total_referrals':
            should_unlock = progress.total_referrals >= achievement.requirement_value
        elif achievement.requirement_type == 'current_level':
            should_unlock = progress.current_level >= achievement.requirement_value
        
        if should_unlock:
            # Desbloquear logro
            ClientAchievement.objects.create(
                client=client,
                achievement=achievement
            )
            
            # Otorgar XP de recompensa
            if achievement.xp_reward > 0:
                progress.add_xp(
                    amount=achievement.xp_reward,
                    reason=f"Logro desbloqueado: {achievement.name}"
                )
