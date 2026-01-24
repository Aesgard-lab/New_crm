"""
Script para crear datos de ejemplo de automatizaciones.
Ejecutar: python seed_automations.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from marketing.models import (
    EmailWorkflow, EmailWorkflowStep,
    LeadScoringRule, LeadScoringAutomation,
    RetentionRule, LeadStage
)
from organizations.models import Gym

def seed_automations():
    gym = Gym.objects.first()
    if not gym:
        print("❌ No hay gym. Crea uno primero.")
        return
    
    print(f"✅ Creando automatizaciones para: {gym.name}\n")
    
    # =========================================================================
    # EMAIL WORKFLOWS
    # =========================================================================
    print("📧 Creando Email Workflows...")
    
    # Workflow 1: Bienvenida a nuevos leads
    workflow1, created = EmailWorkflow.objects.get_or_create(
        gym=gym,
        name="Bienvenida Nuevos Leads",
        defaults={
            'description': 'Secuencia de bienvenida para leads recién creados',
            'trigger_event': 'LEAD_CREATED',
            'is_active': True
        }
    )
    
    if created:
        EmailWorkflowStep.objects.create(
            workflow=workflow1,
            order=1,
            delay_days=0,
            subject="¡Bienvenido a nuestro gimnasio!",
            content_html="<h1>Hola {{client_name}}!</h1><p>Gracias por tu interés en nuestro gimnasio.</p>",
            is_active=True
        )
        EmailWorkflowStep.objects.create(
            workflow=workflow1,
            order=2,
            delay_days=2,
            subject="Conoce nuestras instalaciones",
            content_html="<h1>Hola {{client_name}}!</h1><p>Te invitamos a conocer nuestras instalaciones.</p>",
            is_active=True
        )
        EmailWorkflowStep.objects.create(
            workflow=workflow1,
            order=3,
            delay_days=5,
            subject="Oferta especial para ti",
            content_html="<h1>¡Oferta limitada!</h1><p>Descuento del 20% en tu primera membresía.</p>",
            is_active=True
        )
        print(f"  ✓ Workflow creado: {workflow1.name} (3 pasos)")
    else:
        print(f"  • Workflow ya existe: {workflow1.name}")
    
    # Workflow 2: Seguimiento membresía
    workflow2, created = EmailWorkflow.objects.get_or_create(
        gym=gym,
        name="Seguimiento Nueva Membresía",
        defaults={
            'description': 'Onboarding para nuevos miembros',
            'trigger_event': 'MEMBERSHIP_CREATED',
            'is_active': True
        }
    )
    
    if created:
        EmailWorkflowStep.objects.create(
            workflow=workflow2,
            order=1,
            delay_days=0,
            subject="¡Felicidades por tu membresía!",
            content_html="<h1>¡Bienvenido al equipo!</h1><p>Estamos emocionados de tenerte con nosotros.</p>",
            is_active=True
        )
        EmailWorkflowStep.objects.create(
            workflow=workflow2,
            order=2,
            delay_days=7,
            subject="¿Cómo va tu primera semana?",
            content_html="<h1>Hola {{client_name}}!</h1><p>Queremos saber cómo va tu experiencia.</p>",
            is_active=True
        )
        print(f"  ✓ Workflow creado: {workflow2.name} (2 pasos)")
    else:
        print(f"  • Workflow ya existe: {workflow2.name}")
    
    # =========================================================================
    # LEAD SCORING RULES
    # =========================================================================
    print("\n⭐ Creando reglas de Lead Scoring...")
    
    scoring_rules = [
        ('Visita Registrada', 'VISIT_REGISTERED', 10),
        ('Clase Reservada', 'CLASS_BOOKED', 15),
        ('Compra Realizada', 'PURCHASE_MADE', 25),
        ('Email Abierto', 'EMAIL_OPENED', 5),
        ('Formulario Enviado', 'FORM_SUBMITTED', 20),
        ('Respondió Mensaje', 'RESPONDED_MESSAGE', 15),
        ('Penalización: Sin Respuesta', 'DAYS_NO_RESPONSE', -5),
    ]
    
    for name, event_type, points in scoring_rules:
        rule, created = LeadScoringRule.objects.get_or_create(
            gym=gym,
            name=name,
            event_type=event_type,
            defaults={
                'points': points,
                'is_active': True
            }
        )
        if created:
            print(f"  ✓ Regla creada: {name} ({points:+d} pts)")
        else:
            print(f"  • Regla ya existe: {name}")
    
    # Automatización por score
    print("\n⚡ Creando automatizaciones de Lead Scoring...")
    
    # Buscar etapa "Hot Lead" o similar
    hot_stage = LeadStage.objects.filter(
        pipeline__gym=gym,
        name__icontains='hot'
    ).first() or LeadStage.objects.filter(
        pipeline__gym=gym
    ).order_by('order').last()
    
    if hot_stage:
        automation, created = LeadScoringAutomation.objects.get_or_create(
            gym=gym,
            name="Mover a Hot Leads (Score >= 70)",
            defaults={
                'min_score': 70,
                'action_type': 'MOVE_TO_STAGE',
                'target_stage': hot_stage,
                'is_active': True
            }
        )
        if created:
            print(f"  ✓ Automatización creada: {automation.name}")
        else:
            print(f"  • Automatización ya existe: {automation.name}")
    
    # =========================================================================
    # RETENTION RULES
    # =========================================================================
    print("\n⚠️ Creando reglas de Retención...")
    
    retention_rules = [
        ('Alerta: Sin Asistencia 14 días', 'NO_ATTENDANCE', 14, 70),
        ('Alerta: Sin Asistencia 30 días', 'NO_ATTENDANCE', 30, 90),
        ('Alerta: Membresía expira en 7 días', 'MEMBERSHIP_EXPIRING', 7, 50),
    ]
    
    for name, alert_type, days, risk in retention_rules:
        rule, created = RetentionRule.objects.get_or_create(
            gym=gym,
            name=name,
            alert_type=alert_type,
            days_threshold=days,
            defaults={
                'risk_score': risk,
                'send_notification': True,
                'is_active': True
            }
        )
        if created:
            print(f"  ✓ Regla creada: {name}")
        else:
            print(f"  • Regla ya existe: {name}")
    
    print("\n" + "="*60)
    print("✅ SEED COMPLETADO!")
    print("="*60)
    print("\nPuedes acceder a:")
    print("  • Dashboard: /marketing/automation/")
    print("  • Workflows: /marketing/automation/workflows/")
    print("  • Scoring: /marketing/automation/scoring/")
    print("  • Retención: /marketing/automation/retention/")
    print("\n💡 Tip: Configura Celery Beat para ejecutar las tareas periódicas")
    print("   celery -A config beat -l info")

if __name__ == '__main__':
    seed_automations()
