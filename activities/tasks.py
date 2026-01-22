"""
Tareas asíncronas para el sistema de valoraciones.
"""
from celery import shared_task
from django.utils import timezone


@shared_task
def send_review_request_notification(request_id):
    """
    Envía notificación (email + popup) para solicitar review de clase.
    """
    from activities.models import ReviewRequest, ReviewSettings
    from marketing.models import Popup
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    try:
        request_obj = ReviewRequest.objects.get(id=request_id)
    except ReviewRequest.DoesNotExist:
        return
    
    # Verificar que no esté expirada
    if request_obj.status != 'PENDING':
        return
    
    if timezone.now() > request_obj.expires_at:
        request_obj.status = 'EXPIRED'
        request_obj.save()
        return
    
    client = request_obj.client
    session = request_obj.session
    gym = request_obj.gym
    
    try:
        settings = ReviewSettings.objects.get(gym=gym, enabled=True)
    except ReviewSettings.DoesNotExist:
        return
    
    # Crear popup
    if not request_obj.popup_created:
        try:
            instructor_name = f"{session.staff.user.first_name} {session.staff.user.last_name}"
            
            Popup.objects.create(
                gym=gym,
                title="💭 ¿Cómo estuvo tu clase?",
                content=f'<p>Nos gustaría saber tu opinión sobre la clase de <strong>{session.activity.name}</strong> con {instructor_name}.</p><p><a href="/app/review/{request_obj.id}/" class="inline-block px-4 py-2 bg-indigo-600 text-white rounded-lg mt-2">Dejar Valoración</a></p>',
                priority='INFO',
                audience_type='SPECIFIC_CLIENT',
                target_client=client,
                is_active=True,
                start_date=timezone.now(),
                end_date=request_obj.expires_at,
            )
            request_obj.popup_created = True
            request_obj.save()
        except Exception as e:
            print(f"Error creando popup de review: {e}")
    
    # Enviar email
    if not request_obj.email_sent and client.email:
        try:
            instructor_name = f"{session.staff.user.first_name} {session.staff.user.last_name}"
            
            subject = f"¿Cómo estuvo tu clase de {session.activity.name}?"
            
            message = f"""
Hola {client.first_name},

Esperamos que hayas disfrutado tu clase de {session.activity.name} con {instructor_name}.

Tu opinión es muy importante para nosotros. Por favor, tómate un momento para valorar tu experiencia:

👉 Deja tu valoración aquí: {gym.website or 'http://tu-gimnasio.com'}/app/review/{request_obj.id}/

¡Gracias por tu tiempo!

Equipo de {gym.name}
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=gym.email or 'noreply@gym.com',
                recipient_list=[client.email],
                fail_silently=True,
            )
            
            request_obj.email_sent = True
            request_obj.save()
        except Exception as e:
            print(f"Error enviando email de review: {e}")


def send_review_request_notification_sync(request_id):
    """
    Versión síncrona del envío de notificación (fallback si Celery no disponible).
    """
    send_review_request_notification(request_id)
