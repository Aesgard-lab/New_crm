"""
Celery Tasks for Lead Management Automations
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


# =============================================================================
# RETRY CONFIGURATION
# =============================================================================

# Configuración estándar para reintentos
RETRY_CONFIG = {
    'autoretry_for': (Exception,),
    'retry_backoff': True,  # Exponential backoff
    'retry_backoff_max': 600,  # Max 10 minutes between retries
    'retry_jitter': True,  # Add randomness to prevent thundering herd
    'max_retries': 3,
}

# Para tasks críticas (emails, notificaciones)
CRITICAL_RETRY_CONFIG = {
    **RETRY_CONFIG,
    'max_retries': 5,
}


def safe_task_delay(task, *args, **kwargs):
    """Safely call a Celery task's delay method."""
    try:
        return task.delay(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Could not queue task {task.name}: {e}")
        # Fallback: intentar ejecutar síncronamente para tasks críticas
        try:
            if hasattr(task, 'run'):
                logger.info(f"Executing {task.name} synchronously as fallback")
                return task.run(*args, **kwargs)
        except Exception as sync_e:
            logger.error(f"Sync fallback also failed for {task.name}: {sync_e}")
        return None


@shared_task(name='marketing.check_inactive_leads', **RETRY_CONFIG)
def check_inactive_leads():
    """
    Periodic task to check for leads that have been inactive
    and move them based on automation rules.
    Runs daily via Celery Beat.
    """
    from .models import LeadCard, LeadStageAutomation, LeadStageHistory
    
    today = timezone.now()
    
    # Get all active DAYS_INACTIVE rules
    inactive_rules = LeadStageAutomation.objects.filter(
        trigger_type='DAYS_INACTIVE',
        is_active=True
    ).select_related('from_stage', 'to_stage')
    
    moved_count = 0
    
    for rule in inactive_rules:
        if not rule.trigger_value:
            continue
            
        cutoff_date = today - timedelta(days=rule.trigger_value)
        
        # Find leads in the source stage that haven't been updated
        stale_leads = LeadCard.objects.filter(
            stage=rule.from_stage,
            updated_at__lt=cutoff_date
        )
        
        for lead in stale_leads:
            old_stage = lead.stage
            time_in_stage = today - lead.updated_at if lead.updated_at else None
            
            # Record history
            LeadStageHistory.objects.create(
                lead_card=lead,
                from_stage=old_stage,
                to_stage=rule.to_stage,
                changed_by_automation=rule,
                time_in_previous_stage=time_in_stage,
                notes=f"Automatización: {rule.get_trigger_type_display()} ({rule.trigger_days} días)"
            )
            
            lead.stage = rule.to_stage
            lead.save()
            moved_count += 1
    
    return f"Moved {moved_count} inactive leads"


@shared_task(name='marketing.process_lead_automation', **RETRY_CONFIG)
def process_lead_automation(client_id, trigger_type):
    """
    Process automation rule for a specific lead/client.
    Called from signals when events occur.
    """
    from .models import LeadCard, LeadStageAutomation, LeadStageHistory
    from clients.models import Client
    
    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return f"Client {client_id} not found"
    
    # Get the lead card for this client
    try:
        lead_card = client.lead_card
    except LeadCard.DoesNotExist:
        return f"No lead card for client {client_id}"
    
    if not lead_card.stage:
        return "Lead has no stage"
    
    # Find matching automation rule
    rule = LeadStageAutomation.objects.filter(
        from_stage=lead_card.stage,
        trigger_type=trigger_type,
        is_active=True
    ).order_by('-priority').first()
    
    if rule and rule.to_stage:
        old_stage = lead_card.stage
        time_in_stage = timezone.now() - lead_card.updated_at if lead_card.updated_at else None
        
        # Record history
        LeadStageHistory.objects.create(
            lead_card=lead_card,
            from_stage=old_stage,
            to_stage=rule.to_stage,
            changed_by_automation=rule,
            time_in_previous_stage=time_in_stage,
            notes=f"Automatización: {rule.get_trigger_type_display()}"
        )
        
        lead_card.stage = rule.to_stage
        lead_card.save()
        
        # Update client status if needed
        if rule.to_stage.is_won and client.status == 'LEAD':
            client.status = 'ACTIVE'
            client.save()
        elif rule.to_stage.is_lost and client.status == 'LEAD':
            client.status = 'INACTIVE'
            client.save()
        
        return f"Moved {client} from {old_stage.name} to {rule.to_stage.name}"
    
    return f"No matching rule for {trigger_type}"


@shared_task(name='marketing.create_lead_card_for_client', **RETRY_CONFIG)
def create_lead_card_for_client(client_id, pipeline_id=None):
    """
    Create a LeadCard for a new client with status=LEAD.
    Places them in the first stage of the active pipeline.
    """
    from .models import LeadCard, LeadPipeline, LeadStage, LeadStageHistory
    from clients.models import Client
    
    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return f"Client {client_id} not found"
    
    # Check if already has a lead card
    if hasattr(client, 'lead_card'):
        return f"Client {client_id} already has a lead card"
    
    # Find the active pipeline for this gym
    if pipeline_id:
        pipeline = LeadPipeline.objects.filter(id=pipeline_id, gym=client.gym).first()
    else:
        pipeline = LeadPipeline.objects.filter(gym=client.gym, is_active=True).first()
    
    if not pipeline:
        return f"No active pipeline for gym {client.gym.name}"
    
    # Get the first stage
    first_stage = pipeline.stages.order_by('order').first()
    
    if not first_stage:
        return f"Pipeline {pipeline.name} has no stages"
    
    # Create the lead card
    lead_card = LeadCard.objects.create(
        client=client,
        stage=first_stage
    )
    
    # Record initial stage in history
    LeadStageHistory.objects.create(
        lead_card=lead_card,
        from_stage=None,  # New lead, no previous stage
        to_stage=first_stage,
        notes="Entrada inicial al pipeline"
    )
    
    return f"Created lead card for {client} in stage {first_stage.name}"


# =============================================================================
# EMAIL WORKFLOWS (Secuencias)
# =============================================================================

@shared_task(name='marketing.process_email_workflows', **CRITICAL_RETRY_CONFIG)
def process_email_workflows():
    """
    Task periódico que procesa todos los workflows activos.
    Revisa qué emails deben enviarse hoy según los delays configurados.
    Ejecutar diariamente via Celery Beat.
    """
    from .models import EmailWorkflowExecution, EmailWorkflowStepLog, EmailWorkflowStep
    from django.core.mail import send_mail
    from django.conf import settings
    
    today = timezone.now()
    processed_count = 0
    
    # Obtener todas las ejecuciones activas
    active_executions = EmailWorkflowExecution.objects.filter(
        status='ACTIVE',
        workflow__is_active=True
    ).select_related('workflow', 'client', 'current_step')
    
    for execution in active_executions:
        # Obtener pasos del workflow ordenados
        steps = execution.workflow.steps.filter(is_active=True).order_by('order')
        
        if not steps.exists():
            continue
        
        # Determinar siguiente paso a enviar
        if not execution.current_step:
            # Primer paso
            next_step = steps.first()
            scheduled_for = execution.started_at + timedelta(days=next_step.delay_days)
        else:
            # Buscar siguiente paso
            current_step_logs = execution.step_logs.filter(step=execution.current_step)
            if not current_step_logs.exists():
                continue
            
            last_log = current_step_logs.order_by('-sent_at').first()
            next_steps = steps.filter(order__gt=execution.current_step.order)
            
            if not next_steps.exists():
                # Workflow completado
                execution.status = 'COMPLETED'
                execution.completed_at = today
                execution.save()
                continue
            
            next_step = next_steps.first()
            scheduled_for = last_log.sent_at + timedelta(days=next_step.delay_days)
        
        # Verificar si es hora de enviar
        if scheduled_for <= today:
            # Verificar si el cliente tiene notificaciones activadas
            if not execution.client.email_notifications_enabled:
                # Marcar como completado sin enviar
                EmailWorkflowStepLog.objects.create(
                    execution=execution,
                    step=next_step,
                    scheduled_for=scheduled_for,
                    success=False,
                    error_message='Cliente con notificaciones desactivadas'
                )
                execution.current_step = next_step
                execution.save()
                continue
            
            try:
                # Obtener contenido del email
                if next_step.template:
                    email_html = next_step.template.content_html
                else:
                    email_html = next_step.content_html
                
                # Personalizar con datos del cliente
                email_html = email_html.replace('{{client_name}}', execution.client.first_name or execution.client.email)
                
                # Enviar email
                gym = execution.workflow.gym
                settings_obj = gym.marketing_settings if hasattr(gym, 'marketing_settings') else None
                
                from_email = settings_obj.default_sender_email if settings_obj else settings.DEFAULT_FROM_EMAIL
                
                send_mail(
                    subject=next_step.subject,
                    message='',
                    html_message=email_html,
                    from_email=from_email,
                    recipient_list=[execution.client.email],
                    fail_silently=False,
                )
                
                # Registrar envío exitoso
                EmailWorkflowStepLog.objects.create(
                    execution=execution,
                    step=next_step,
                    scheduled_for=scheduled_for,
                    success=True
                )
                
                # Actualizar current_step
                execution.current_step = next_step
                execution.save()
                
                processed_count += 1
                
            except Exception as e:
                # Registrar error
                EmailWorkflowStepLog.objects.create(
                    execution=execution,
                    step=next_step,
                    scheduled_for=scheduled_for,
                    success=False,
                    error_message=str(e)
                )
    
    return f"Processed {processed_count} workflow emails"


@shared_task(name='marketing.start_workflow_for_client', **CRITICAL_RETRY_CONFIG)
def start_workflow_for_client(workflow_id, client_id):
    """
    Inicia un workflow para un cliente específico.
    Llamado desde signals o manualmente.
    """
    from .models import EmailWorkflow, EmailWorkflowExecution
    from clients.models import Client
    
    try:
        workflow = EmailWorkflow.objects.get(id=workflow_id, is_active=True)
        client = Client.objects.get(id=client_id)
    except (EmailWorkflow.DoesNotExist, Client.DoesNotExist) as e:
        return f"Error: {str(e)}"
    
    # Verificar si ya está en este workflow
    if EmailWorkflowExecution.objects.filter(workflow=workflow, client=client, status='ACTIVE').exists():
        return f"Client {client} already in workflow {workflow.name}"
    
    # Crear ejecución
    execution = EmailWorkflowExecution.objects.create(
        workflow=workflow,
        client=client,
        status='ACTIVE'
    )
    
    return f"Started workflow '{workflow.name}' for {client}"


# =============================================================================
# LEAD SCORING
# =============================================================================

@shared_task(name='marketing.calculate_lead_score', **RETRY_CONFIG)
def calculate_lead_score(client_id, event_type, event_data=None):
    """
    Calcula y actualiza el score de un lead basado en un evento.
    """
    from .models import LeadScore, LeadScoringRule, LeadScoringAutomation
    from clients.models import Client
    
    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return f"Client {client_id} not found"
    
    # Obtener o crear LeadScore
    lead_score, created = LeadScore.objects.get_or_create(client=client)
    
    # Buscar reglas activas para este evento
    rules = LeadScoringRule.objects.filter(
        gym=client.gym,
        event_type=event_type,
        is_active=True
    )
    
    total_points = 0
    for rule in rules:
        total_points += rule.points
        lead_score.add_points(rule.points, f"{rule.get_event_type_display()}: {rule.name}")
    
    # Verificar automatizaciones basadas en score
    automations = LeadScoringAutomation.objects.filter(
        gym=client.gym,
        is_active=True,
        min_score__lte=lead_score.score
    )
    
    if automations.exists():
        for automation in automations:
            # Verificar max_score
            if automation.max_score and lead_score.score > automation.max_score:
                continue
            
            # Ejecutar acción
            if automation.action_type == 'MOVE_TO_STAGE' and automation.target_stage:
                if hasattr(client, 'lead_card') and client.lead_card.stage != automation.target_stage:
                    client.lead_card.stage = automation.target_stage
                    client.lead_card.save()
            
            elif automation.action_type == 'ASSIGN_TO_STAFF' and automation.target_staff:
                if hasattr(client, 'lead_card'):
                    client.lead_card.assigned_to = automation.target_staff
                    client.lead_card.save()
            
            elif automation.action_type == 'START_WORKFLOW' and automation.target_workflow:
                safe_task_delay(start_workflow_for_client, automation.target_workflow.id, client.id)
    
    return f"Updated score for {client}: {total_points:+d} pts (Total: {lead_score.score})"


@shared_task(name='marketing.decay_lead_scores', **RETRY_CONFIG)
def decay_lead_scores():
    """
    Task periódico para "decaer" scores de leads inactivos.
    Ejecutar semanalmente via Celery Beat.
    Resta puntos a leads que no han tenido actividad positiva recientemente.
    """
    from .models import LeadScore
    from datetime import timedelta
    
    decay_threshold = timezone.now() - timedelta(days=14)
    decay_points = -5
    
    # Leads sin actividad positiva en 14 días
    stale_scores = LeadScore.objects.filter(
        last_positive_event__lt=decay_threshold,
        score__gt=0  # Solo si tienen puntos
    )
    
    decayed_count = 0
    for lead_score in stale_scores:
        lead_score.add_points(decay_points, "Decaimiento por inactividad (14 días)")
        decayed_count += 1
    
    return f"Decayed {decayed_count} lead scores ({decay_points} pts each)"


# =============================================================================
# ALERTAS DE RETENCIÓN
# =============================================================================

@shared_task(name='marketing.check_retention_alerts', **RETRY_CONFIG)
def check_retention_alerts():
    """
    Task periódico que verifica clientes en riesgo y crea alertas.
    Ejecutar diariamente via Celery Beat.
    """
    from .models import RetentionRule, RetentionAlert
    from clients.models import Client
    from django.db.models import Max, Count
    
    today = timezone.now()
    alerts_created = 0
    
    # Obtener todas las reglas activas
    rules = RetentionRule.objects.filter(is_active=True).select_related('gym')
    
    for rule in rules:
        gym = rule.gym
        
        if rule.alert_type == 'NO_ATTENDANCE':
            # Buscar clientes activos sin visitas recientes
            threshold_date = today - timedelta(days=rule.days_threshold)
            
            # Clientes que tienen visitas pero la última es antigua
            from django.db.models import Q
            at_risk_clients = Client.objects.filter(
                gym=gym,
                status='ACTIVE'
            ).annotate(
                last_visit=Max('visits__date')
            ).filter(
                Q(last_visit__lt=threshold_date) | Q(last_visit__isnull=True)
            )
            
            for client in at_risk_clients:
                # Verificar si ya existe alerta abierta
                existing = RetentionAlert.objects.filter(
                    client=client,
                    alert_type='NO_ATTENDANCE',
                    status__in=['OPEN', 'IN_PROGRESS']
                ).exists()
                
                if not existing:
                    days_inactive = (today.date() - client.last_visit).days if client.last_visit else rule.days_threshold
                    
                    alert = RetentionAlert.objects.create(
                        gym=gym,
                        client=client,
                        alert_type='NO_ATTENDANCE',
                        title=f"{client.first_name} sin asistir {days_inactive} días",
                        description=f"El cliente no ha registrado visitas en {days_inactive} días. Acción recomendada: Contactar y ofrecer apoyo.",
                        days_inactive=days_inactive,
                        risk_score=rule.risk_score
                    )
                    
                    # Asignar automáticamente si configurado
                    if rule.auto_assign_to_staff:
                        # Asignar al staff con menos alertas pendientes
                        from staff.models import StaffProfile
                        staff = StaffProfile.objects.filter(
                            gym=gym,
                            role__in=['MANAGER', 'TRAINER']
                        ).annotate(
                            pending_alerts=Count('assigned_retention_alerts', filter=Q(assigned_retention_alerts__status='OPEN'))
                        ).order_by('pending_alerts').first()
                        
                        if staff:
                            alert.assigned_to = staff
                            alert.save()
                    
                    # Iniciar workflow si configurado
                    if rule.start_workflow:
                        safe_task_delay(start_workflow_for_client, rule.start_workflow.id, client.id)
                    
                    alerts_created += 1
        
        elif rule.alert_type == 'MEMBERSHIP_EXPIRING':
            # Buscar membresías que expiran pronto
            expiry_threshold = today + timedelta(days=rule.days_threshold)
            
            # Importar aquí para evitar circular imports
            try:
                from subscriptions.models import Subscription
                
                expiring_subs = Subscription.objects.filter(
                    client__gym=gym,
                    status='ACTIVE',
                    end_date__lte=expiry_threshold,
                    end_date__gte=today
                ).select_related('client')
                
                for sub in expiring_subs:
                    # Verificar si ya existe alerta
                    existing = RetentionAlert.objects.filter(
                        client=sub.client,
                        alert_type='MEMBERSHIP_EXPIRING',
                        status__in=['OPEN', 'IN_PROGRESS']
                    ).exists()
                    
                    if not existing:
                        days_until = (sub.end_date - today.date()).days
                        
                        RetentionAlert.objects.create(
                            gym=gym,
                            client=sub.client,
                            alert_type='MEMBERSHIP_EXPIRING',
                            title=f"Membresía de {sub.client.first_name} expira en {days_until} días",
                            description=f"Membresía expira el {sub.end_date.strftime('%d/%m/%Y')}. Contactar para renovación.",
                            risk_score=rule.risk_score
                        )
                        
                        alerts_created += 1
            except ImportError:
                pass  # Modelo Subscription no disponible
    
    return f"Created {alerts_created} retention alerts"


@shared_task(name='marketing.send_retention_notifications', **CRITICAL_RETRY_CONFIG)
def send_retention_notifications():
    """
    Envía notificaciones al staff sobre alertas de retención nuevas.
    """
    from .models import RetentionAlert
    from django.core.mail import send_mail
    from django.conf import settings
    
    # Alertas abiertas de las últimas 24h
    yesterday = timezone.now() - timedelta(days=1)
    new_alerts = RetentionAlert.objects.filter(
        status='OPEN',
        created_at__gte=yesterday
    ).select_related('client', 'gym', 'assigned_to')
    
    if not new_alerts.exists():
        return "No new retention alerts to notify"
    
    # Agrupar por gym y staff asignado
    from collections import defaultdict
    alerts_by_staff = defaultdict(list)
    
    for alert in new_alerts:
        if alert.assigned_to:
            key = (alert.gym.id, alert.assigned_to.id)
            alerts_by_staff[key].append(alert)
    
    sent_count = 0
    for (gym_id, staff_id), alerts in alerts_by_staff.items():
        staff = alerts[0].assigned_to
        gym = alerts[0].gym
        
        # Construir email
        subject = f"⚠️ {len(alerts)} Alerta(s) de Retención Asignadas"
        message = f"Hola {staff.user.first_name},\n\n"
        message += f"Tienes {len(alerts)} nuevas alertas de retención:\n\n"
        
        for alert in alerts:
            message += f"• {alert.title} (Riesgo: {alert.risk_score}/100)\n"
        
        message += f"\nRevisa el panel de retención para tomar acción.\n\nSaludos,\n{gym.name}"
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[staff.user.email],
                fail_silently=False,
            )
            sent_count += 1
        except Exception as e:
            print(f"Error sending notification: {e}")
    
    return f"Sent {sent_count} retention alert notifications"

