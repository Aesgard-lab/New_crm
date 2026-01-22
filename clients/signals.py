"""
Signals para auto-generar documentos y enviar emails cuando se crean membresías
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import ClientMembership, ClientDocument


@receiver(post_save, sender=ClientMembership)
def create_contract_document(sender, instance, created, **kwargs):
    """
    Auto-genera un documento de contrato cuando se crea una membresía
    que tiene un plan con contract_required=True
    """
    if not created:
        return
    
    # Intentar obtener el plan original desde OrderItem o similar
    # Por ahora, vamos a buscar si el nombre de la membresía corresponde a un plan
    from memberships.models import MembershipPlan
    
    # Buscar plan por nombre (puede no ser exacto)
    try:
        plan = MembershipPlan.objects.filter(
            name__icontains=instance.name,
            gym=instance.client.gym,
            contract_required=True
        ).first()
        
        if plan and plan.contract_content:
            # Verificar si ya existe un documento para esta membresía
            existing = ClientDocument.objects.filter(
                client=instance.client,
                membership_plan=plan,
                document_type='CONTRACT'
            ).exists()
            
            if not existing:
                # Crear documento
                doc = ClientDocument.objects.create(
                    client=instance.client,
                    name=f"Contrato: {plan.name}",
                    document_type='CONTRACT',
                    content=plan.contract_content,
                    requires_signature=True,
                    status='PENDING',
                    sent_at=timezone.now(),
                    membership_plan=plan
                )
                print(f"✅ Documento de contrato creado automáticamente: {doc.name}")
    except Exception as e:
        print(f"⚠️ Error al crear documento automático: {e}")


@receiver(post_save, sender=ClientMembership)
def send_membership_welcome_email(sender, instance, created, **kwargs):
    """
    Envía un email de bienvenida cuando se crea una nueva membresía,
    si existe un workflow activo para MEMBERSHIP_CREATED.
    """
    if not created:
        return
    
    # Verificar que el cliente tenga email
    client = instance.client
    if not client.email:
        return
    
    # Verificar preferencias de notificación del cliente
    if not client.email_notifications_enabled:
        return
    
    try:
        from marketing.models import EmailWorkflow, EmailWorkflowStep, EmailWorkflowExecution, EmailWorkflowStepLog
        from organizations.email_utils import send_gym_email
        
        gym = instance.gym or client.gym
        
        # Buscar workflow activo para MEMBERSHIP_CREATED
        workflow = EmailWorkflow.objects.filter(
            gym=gym,
            trigger_event='MEMBERSHIP_CREATED',
            is_active=True
        ).first()
        
        if not workflow:
            return
        
        # Obtener el primer paso del workflow (delay_days=0 para envío inmediato)
        step = workflow.steps.filter(is_active=True, delay_days=0).order_by('order').first()
        
        if not step:
            return
        
        # Crear registro de ejecución del workflow
        execution, exec_created = EmailWorkflowExecution.objects.get_or_create(
            workflow=workflow,
            client=client,
            defaults={'status': 'ACTIVE', 'current_step': step}
        )
        
        # Preparar contenido del email
        gym_name = gym.commercial_name or gym.name
        
        # Obtener HTML del template o del step
        if step.template and step.template.content_html:
            html_content = step.template.content_html
        elif step.content_html:
            html_content = step.content_html
        else:
            # HTML por defecto
            html_content = f"""
            <div style="font-family: Arial, sans-serif;">
                <h2>¡Bienvenido/a a {gym_name}!</h2>
                <p>Hola {client.first_name},</p>
                <p>Tu cuota <strong>{instance.name}</strong> ya está activa.</p>
                <p>Fecha de inicio: {instance.start_date.strftime('%d/%m/%Y')}</p>
                <p>¡Te esperamos!</p>
            </div>
            """
        
        # Reemplazar variables
        html_content = html_content.replace('{{gym_name}}', gym_name)
        html_content = html_content.replace('{{client_name}}', client.first_name)
        html_content = html_content.replace('{{membership_name}}', instance.name)
        html_content = html_content.replace('{{start_date}}', instance.start_date.strftime('%d/%m/%Y'))
        html_content = html_content.replace('{{price}}', str(instance.price))
        
        subject = step.subject.replace('{{gym_name}}', gym_name)
        
        # Enviar email
        result = send_gym_email(
            gym=gym,
            subject=subject,
            body=f"Hola {client.first_name}, tu cuota {instance.name} ya está activa en {gym_name}.",
            to_emails=client.email,
            html_body=html_content
        )
        
        # Registrar el log del step
        EmailWorkflowStepLog.objects.create(
            execution=execution,
            step=step,
            scheduled_for=timezone.now(),
            success=bool(result),
            error_message='' if result else 'Error al enviar email'
        )
        
        if result:
            print(f"✅ Email de bienvenida enviado a {client.email} para membresía {instance.name}")
        
    except Exception as e:
        print(f"⚠️ Error al enviar email de bienvenida: {e}")
