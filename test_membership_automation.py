"""
Script para probar la automatización de email cuando se compra una cuota.
"""
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from django.utils import timezone
from datetime import date, timedelta
from clients.models import Client, ClientMembership
from memberships.models import MembershipPlan
from marketing.models import EmailWorkflow, EmailWorkflowStep, EmailTemplate
from organizations.models import Gym
from organizations.email_utils import send_gym_email

def main():
    # Obtener el gimnasio
    gym = Gym.objects.get(name='Qombo Arganzuela')
    print(f"✅ Gimnasio: {gym.name}")
    
    # 1. CREAR O OBTENER CLIENTE DE PRUEBA
    print("\n--- Creando cliente de prueba ---")
    client, created = Client.objects.get_or_create(
        gym=gym,
        email='gestionydeporte@hotmail.com',
        defaults={
            'first_name': 'Cliente',
            'last_name': 'Prueba Automatización',
            'phone_number': '600000000',
            'status': 'ACTIVE',
        }
    )
    if created:
        print(f"✅ Cliente creado: {client.first_name} {client.last_name} ({client.email})")
    else:
        print(f"✅ Cliente existente: {client.first_name} {client.last_name} ({client.email})")
    
    # 2. CREAR O OBTENER UN PLAN DE MEMBRESÍA
    print("\n--- Verificando plan de membresía ---")
    plan, created = MembershipPlan.objects.get_or_create(
        gym=gym,
        name='Plan Mensual Test',
        defaults={
            'description': 'Plan mensual para pruebas de automatización',
            'base_price': 49.99,
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
        }
    )
    if created:
        print(f"✅ Plan creado: {plan.name} - {plan.base_price}€")
    else:
        print(f"✅ Plan existente: {plan.name} - {plan.base_price}€")
    
    # 3. CREAR LA PLANTILLA DE EMAIL
    print("\n--- Creando plantilla de email ---")
    template, created = EmailTemplate.objects.get_or_create(
        gym=gym,
        name='Bienvenida Nueva Cuota',
        defaults={
            'description': 'Email de bienvenida cuando un cliente compra una cuota',
            'content_html': '''
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0;">¡Bienvenido/a!</h1>
    </div>
    
    <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
        <p style="font-size: 16px; color: #333;">Hola <strong>{{client_name}}</strong>,</p>
        
        <p style="font-size: 16px; color: #333;">
            ¡Gracias por confiar en <strong>{{gym_name}}</strong>! Tu cuota ya está activa y lista para usar.
        </p>
        
        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea;">
            <h3 style="margin-top: 0; color: #333;">📋 Detalles de tu cuota:</h3>
            <ul style="color: #555; line-height: 1.8;">
                <li><strong>Plan:</strong> {{membership_name}}</li>
                <li><strong>Fecha de inicio:</strong> {{start_date}}</li>
                <li><strong>Precio:</strong> {{price}}€</li>
            </ul>
        </div>
        
        <p style="font-size: 16px; color: #333;">
            Ya puedes empezar a disfrutar de todas las instalaciones y servicios.
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="#" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold;">
                Ver mi cuenta
            </a>
        </div>
        
        <p style="color: #777; font-size: 14px;">
            Si tienes alguna pregunta, no dudes en contactarnos.
        </p>
    </div>
</div>
''',
        }
    )
    if created:
        print(f"✅ Plantilla creada: {template.name}")
    else:
        print(f"✅ Plantilla existente: {template.name}")
    
    # 4. CREAR EL WORKFLOW DE AUTOMATIZACIÓN
    print("\n--- Creando workflow de automatización ---")
    workflow, created = EmailWorkflow.objects.get_or_create(
        gym=gym,
        trigger_event='MEMBERSHIP_CREATED',
        name='Email Bienvenida Nueva Cuota',
        defaults={
            'description': 'Envía un email de bienvenida cuando un cliente compra una cuota',
            'is_active': True,
        }
    )
    if created:
        print(f"✅ Workflow creado: {workflow.name}")
    else:
        print(f"✅ Workflow existente: {workflow.name}")
    
    # 5. CREAR EL PASO DEL WORKFLOW (enviar inmediatamente)
    step, created = EmailWorkflowStep.objects.get_or_create(
        workflow=workflow,
        order=1,
        defaults={
            'delay_days': 0,  # Inmediato
            'subject': '¡Bienvenido/a a {{gym_name}}! Tu cuota está activa',
            'template': template,
            'is_active': True,
        }
    )
    if created:
        print(f"✅ Paso del workflow creado: Envío inmediato")
    else:
        print(f"✅ Paso del workflow existente")
    
    # 6. SIMULAR COMPRA DE CUOTA
    print("\n--- Simulando compra de cuota ---")
    
    # Eliminar membresías anteriores de prueba para este cliente
    ClientMembership.objects.filter(
        client=client,
        name__icontains='Test'
    ).delete()
    
    # Crear la membresía
    membership = ClientMembership.objects.create(
        client=client,
        gym=gym,
        plan=plan,
        name=plan.name,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        price=plan.base_price,
        status='ACTIVE',
        is_recurring=plan.is_recurring,
        current_period_start=date.today(),
        current_period_end=date.today() + timedelta(days=30),
        next_billing_date=date.today() + timedelta(days=30),
    )
    print(f"✅ Membresía creada: {membership.name} para {client.first_name}")
    
    # 7. ENVIAR EMAIL DE BIENVENIDA MANUALMENTE (simulando el trigger)
    print("\n--- Enviando email de bienvenida ---")
    
    # Preparar el contenido del email con las variables reemplazadas
    html_content = template.content_html
    html_content = html_content.replace('{{gym_name}}', gym.commercial_name or gym.name)
    html_content = html_content.replace('{{client_name}}', client.first_name)
    html_content = html_content.replace('{{membership_name}}', membership.name)
    html_content = html_content.replace('{{start_date}}', membership.start_date.strftime('%d/%m/%Y'))
    html_content = html_content.replace('{{price}}', str(membership.price))
    
    subject = step.subject
    subject = subject.replace('{{gym_name}}', gym.commercial_name or gym.name)
    
    try:
        result = send_gym_email(
            gym=gym,
            subject=subject,
            body=f"Hola {client.first_name}, gracias por unirte a {gym.commercial_name or gym.name}. Tu cuota {membership.name} ya está activa.",
            to_emails=client.email,
            html_body=html_content,
            base_url='http://127.0.0.1:8000'
        )
        
        if result:
            print(f"✅ ¡EMAIL ENVIADO CORRECTAMENTE a {client.email}!")
            print(f"   Asunto: {subject}")
        else:
            print(f"❌ Error: El email no se pudo enviar")
    except Exception as e:
        print(f"❌ Error al enviar email: {e}")
    
    print("\n" + "="*60)
    print("RESUMEN:")
    print("="*60)
    print(f"✓ Cliente: {client.first_name} {client.last_name}")
    print(f"✓ Email: {client.email}")
    print(f"✓ Cuota: {membership.name}")
    print(f"✓ Precio: {membership.price}€")
    print(f"✓ Workflow: {workflow.name}")
    print(f"✓ Email enviado a: {client.email}")
    print("="*60)

if __name__ == '__main__':
    main()
