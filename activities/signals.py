"""
Signals para el sistema de valoraciones de clases.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import random


@receiver(post_save, sender='clients.ClientVisit')
def create_review_request_after_attendance(sender, instance, created, **kwargs):
    """
    Crea una solicitud de review cuando un cliente marca asistencia a clase.
    """
    if not created:
        return
    
    # Solo si el estado es ATTENDED (asistido)
    if instance.status != 'ATTENDED':
        return
    
    from activities.models import ReviewSettings, ReviewRequest, ActivitySession
    
    gym = instance.client.gym
    
    # Verificar si el sistema de reviews está activado
    try:
        settings = ReviewSettings.objects.get(gym=gym, enabled=True)
    except ReviewSettings.DoesNotExist:
        return  # Sistema desactivado
    
    # Obtener la sesión asociada
    if not instance.session:
        return
    
    session = instance.session
    
    # Si no hay instructor, no solicitamos review
    if not session.staff:
        return
    
    # Modo aleatorio: verificar probabilidad
    if settings.request_mode == 'RANDOM':
        if random.randint(1, 100) > settings.random_probability:
            return  # No solicitar esta vez
    
    # Verificar que no exista ya una solicitud
    if ReviewRequest.objects.filter(session=session, client=instance.client).exists():
        return
    
    # Calcular fecha de expiración (7 días para completar)
    expires_at = timezone.now() + timedelta(days=7)
    
    # Crear solicitud de review
    request_obj = ReviewRequest.objects.create(
        gym=gym,
        session=session,
        client=instance.client,
        expires_at=expires_at
    )
    
    # Programar notificación con delay
    from activities.tasks import send_review_request_notification
    
    # Calcular cuándo enviar (X horas después)
    eta = timezone.now() + timedelta(hours=settings.delay_hours)
    
    try:
        send_review_request_notification.apply_async(
            args=[request_obj.id],
            eta=eta
        )
    except Exception as e:
        print(f"Error programando notificación de review: {e}")
        # Si Celery no está disponible, enviar inmediatamente
        from activities.tasks import send_review_request_notification_sync
        send_review_request_notification_sync(request_obj.id)


@receiver(post_save, sender='activities.ClassReview')
def award_points_for_review(sender, instance, created, **kwargs):
    """
    Otorga puntos de fidelidad al cliente por dejar una review.
    """
    if not created:
        return
    
    from activities.models import ReviewSettings
    
    try:
        settings = ReviewSettings.objects.get(gym=instance.gym, enabled=True)
    except ReviewSettings.DoesNotExist:
        return
    
    if settings.points_per_review <= 0:
        return
    
    # Otorgar puntos al cliente
    try:
        from clients.models import LoyaltyPoints
        
        LoyaltyPoints.objects.create(
            client=instance.client,
            points=settings.points_per_review,
            reason=f"Review de clase: {instance.session.activity.name}",
            related_session=instance.session
        )
    except Exception as e:
        print(f"Error otorgando puntos por review: {e}")
