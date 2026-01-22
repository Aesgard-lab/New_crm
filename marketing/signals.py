"""
Django Signals for Lead Management Automations
Triggers Celery tasks when relevant events occur.
"""
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone


# =============================================================================
# HELPER FUNCTIONS FOR CLASS NOTIFICATIONS
# =============================================================================

def send_class_notification(client, event_type, session=None, **context):
    """
    Env\u00eda notificaciones (popup + email) para eventos de clases.
    
    Args:
        client: Cliente a notificar
        event_type: Tipo de evento (ej: 'CLASS_BOOKED', 'WAITLIST_JOINED')
        session: ActivitySession relacionada (opcional)
        **context: Variables adicionales para las plantillas
    """
    from .models import ClassNotificationSettings, Popup
    from django.template.loader import render_to_string
    from django.core.mail import send_mail
    
    gym = client.gym
    
    # Obtener configuraci\u00f3n (crear si no existe)
    settings, _ = ClassNotificationSettings.objects.get_or_create(gym=gym)
    
    # Preparar contexto base
    base_context = {
        'client': client,
        'client_name': client.first_name,
        'gym': gym,
        'gym_name': gym.name,
    }
    
    if session:
        instructor_name = f"{session.staff.user.first_name} {session.staff.user.last_name}" if session.staff else "Staff"
        room_name = session.room.name if session.room else "Por determinar"
        
        base_context.update({
            'class_name': session.activity.name,
            'class_date': session.start_datetime.strftime('%d/%m/%Y'),
            'class_time': session.start_datetime.strftime('%H:%M'),
            'class_datetime': session.start_datetime,
            'instructor': instructor_name,
            'room': room_name,
        })
    
    base_context.update(context)
    
    # Configuración por tipo de evento
    class_name = base_context.get('class_name', 'la clase')
    class_date = base_context.get('class_date', '')
    class_time = base_context.get('class_time', '')
    
    notifications_config = {
        'CLASS_BOOKED': {
            'popup_enabled': settings.popup_booking_confirmation,
            'email_enabled': settings.email_booking_confirmation,
            'popup_title': '✅ Clase Reservada',
            'popup_content': f"Has reservado tu plaza para {class_name} el {class_date} a las {class_time}",
            'email_subject': f"Confirmación de Reserva - {class_name}",
            'email_template': 'emails/class_booked.html',
        },
        'CLASS_CANCELLED': {
            'popup_enabled': settings.popup_cancellation_confirmation,
            'email_enabled': settings.email_cancellation_confirmation,
            'popup_title': '❌ Reserva Cancelada',
            'popup_content': f"Tu reserva para {class_name} ha sido cancelada",
            'email_subject': f"Cancelación Confirmada - {class_name}",
            'email_template': 'emails/class_cancelled.html',
        },
        'WAITLIST_JOINED': {
            'popup_enabled': settings.popup_waitlist_joined,
            'email_enabled': settings.email_waitlist_joined,
            'popup_title': '⏳ En Lista de Espera',
            'popup_content': f"Estás en lista de espera para {class_name}. Te notificaremos si se libera una plaza",
            'email_subject': f"Lista de Espera - {class_name}",
            'email_template': 'emails/waitlist_joined.html',
        },
        'WAITLIST_SPOT_AVAILABLE': {
            'popup_enabled': settings.popup_spot_available,
            'email_enabled': settings.email_spot_available,
            'popup_title': '🎉 ¡Plaza Disponible!',
            'popup_content': f"Se ha liberado una plaza en {class_name}. Tienes {settings.waitlist_claim_timeout_minutes} minutos para confirmar",
            'email_subject': f"🚨 Plaza Disponible - {class_name}",
            'email_template': 'emails/spot_available.html',
            'priority': 'HIGH',
        },
        'WAITLIST_PROMOTED': {
            'popup_enabled': settings.popup_promoted,
            'email_enabled': settings.email_booking_confirmation,
            'popup_title': '✅ ¡Promovido a Clase!',
            'popup_content': f"Has sido promovido automáticamente a {class_name}",
            'email_subject': f"Promoción a Clase - {class_name}",
            'email_template': 'emails/waitlist_promoted.html',
        },
    }
    
    config = notifications_config.get(event_type, {})
    if not config:
        return
    
    # Enviar Popup
    if config.get('popup_enabled') and client.user:  # Solo si tiene usuario de portal
        try:
            Popup.objects.create(
                gym=gym,
                title=config['popup_title'],
                content=config['popup_content'],
                priority=config.get('priority', 'NORMAL'),
                audience_type='SPECIFIC_CLIENT',
                target_client=client,
                is_active=True,
                start_date=timezone.now(),
            )
        except Exception as e:
            print("Error creando popup:", str(e))
    
    # Enviar Email
    if config.get('email_enabled') and client.email:
        try:
            # Por ahora un email simple, luego se puede usar template
            send_mail(
                subject=config['email_subject'],
                message=config['popup_content'],
                from_email=gym.email or 'noreply@mygym.com',
                recipient_list=[client.email],
                fail_silently=True,
            )
        except Exception as e:
            print("Error enviando email:", str(e))


@receiver(post_save, sender='clients.ClientVisit')
def on_client_visit_created(sender, instance, created, **kwargs):
    """
    When a client visit is created, check for FIRST_VISIT automation.
    Also update lead scoring.
    """
    if not created:
        return
    
    client = instance.client
    
    # Update lead scoring
    from .tasks import calculate_lead_score
    calculate_lead_score.delay(client.id, 'VISIT_REGISTERED')
    
    # Only process if client is a LEAD
    if client.status != 'LEAD':
        return
    
    # Check if this is the first visit
    visit_count = client.visits.count()
    if visit_count == 1:
        from .tasks import process_lead_automation
        process_lead_automation.delay(client.id, 'FIRST_VISIT')


@receiver(post_save, sender='clients.ClientMembership')
def on_membership_created(sender, instance, created, **kwargs):
    """
    When a membership is created, check for MEMBERSHIP_CREATED automation.
    Also converts the lead to ACTIVE status.
    """
    if not created:
        return
    
    client = instance.client
    
    # Only process if client is a LEAD
    if client.status != 'LEAD':
        return
    
    from .tasks import process_lead_automation
    process_lead_automation.delay(client.id, 'MEMBERSHIP_CREATED')
    
    # Convert to active client
    client.status = 'ACTIVE'
    client.save()


@receiver(post_save, sender='sales.Order')
def on_order_created(sender, instance, created, **kwargs):
    """
    When an order is created, check for ORDER_CREATED automation.
    Also update lead scoring.
    """
    if not created:
        return
    
    if not instance.client:
        return
    
    client = instance.client
    
    # Update lead scoring
    from .tasks import calculate_lead_score
    calculate_lead_score.delay(client.id, 'PURCHASE_MADE')
    
    # Only process if client is a LEAD
    if client.status != 'LEAD':
        return
    
    from .tasks import process_lead_automation
    process_lead_automation.delay(client.id, 'ORDER_CREATED')


@receiver(post_save, sender='clients.Client')
def on_client_created(sender, instance, created, **kwargs):
    """
    When a new client with status=LEAD is created, create a lead card and start workflow.
    """
    if not created:
        return
    
    if instance.status != 'LEAD':
        return
    
    from .tasks import create_lead_card_for_client
    create_lead_card_for_client.delay(instance.id)
    
    # Check if there's an active workflow for LEAD_CREATED trigger
    from .models import EmailWorkflow
    workflows = EmailWorkflow.objects.filter(
        gym=instance.gym,
        trigger_event='LEAD_CREATED',
        is_active=True
    )
    
    for workflow in workflows:
        from .tasks import start_workflow_for_client
        start_workflow_for_client.delay(workflow.id, instance.id)


# =============================================================================
# LEAD SCORING SIGNALS
# =============================================================================

# Comentado temporalmente - verificar si existe modelo ActivitySessionBooking
# @receiver(post_save, sender='activities.ActivitySessionBooking')
# def on_class_booked(sender, instance, created, **kwargs):
#     """
#     When a client books a class, update lead scoring.
#     """
#     if not created:
#         return
#     
#     if not instance.client:
#         return
#     
#     from .tasks import calculate_lead_score
#     calculate_lead_score.delay(instance.client.id, 'CLASS_BOOKED')


# Signal para email opens (requeriría tracking pixel)
# Por ahora dejamos la estructura preparada
def track_email_opened(client_id):
    """
    Llamar esta función cuando se detecte apertura de email.
    """
    from .tasks import calculate_lead_score
    calculate_lead_score.delay(client_id, 'EMAIL_OPENED')


# =============================================================================
# CLASS BOOKING & WAITLIST SIGNALS
# =============================================================================

# En lugar de usar m2m_changed (que es complejo), llamaremos estas funciones
# directamente desde los API endpoints

def on_client_added_to_class(client, session):
    """Llamar cuando un cliente se añade a una clase"""
    send_class_notification(
        client=client,
        event_type='CLASS_BOOKED',
        session=session
    )


def on_client_removed_from_class(client, session, cancellation_type='EARLY'):
    """Llamar cuando un cliente se elimina de una clase"""
    send_class_notification(
        client=client,
        event_type='CLASS_CANCELLED',
        session=session,
        cancellation_type=cancellation_type
    )


@receiver(post_save, sender='activities.WaitlistEntry')
def on_waitlist_entry_changed(sender, instance, created, **kwargs):
    """
    Detecta cambios en entradas de lista de espera.
    """
    client = instance.client
    session = instance.session
    
    if created and instance.status == 'WAITING':
        # Cliente añadido a lista de espera
        send_class_notification(
            client=client,
            event_type='WAITLIST_JOINED',
            session=session,
            position=session.waitlist_entries.filter(
                status='WAITING',
                joined_at__lt=instance.joined_at
            ).count() + 1
        )
    
    elif instance.status == 'PROMOTED':
        # Cliente promovido de lista de espera a clase
        send_class_notification(
            client=client,
            event_type='WAITLIST_PROMOTED',
            session=session
        )


def notify_waitlist_spot_available(session, exclude_client_id=None):
    """
    Notifica a las primeras X personas de la lista de espera que hay una plaza disponible.
    Usa el modo Broadcast configurado en settings.
    """
    from .models import ClassNotificationSettings
    from activities.models import WaitlistEntry
    
    gym = session.gym
    settings, _ = ClassNotificationSettings.objects.get_or_create(gym=gym)
    
    # Obtener los primeros X en lista de espera
    waitlist = WaitlistEntry.objects.filter(
        session=session,
        status='WAITING'
    ).order_by('joined_at')
    
    if exclude_client_id:
        waitlist = waitlist.exclude(client_id=exclude_client_id)
    
    waitlist = waitlist[:settings.waitlist_broadcast_count]
    
    for entry in waitlist:
        send_class_notification(
            client=entry.client,
            event_type='WAITLIST_SPOT_AVAILABLE',
            session=session,
            timeout_minutes=settings.waitlist_claim_timeout_minutes
        )


