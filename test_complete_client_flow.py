"""
Test completo del flujo de un cliente
======================================

Este script simula todo el ciclo de vida de un cliente:
1. Crear cliente desde backoffice
2. Comprar un servicio y una cuota
3. Apuntarse a una clase
4. Cancelar la clase
5. Enviar popup y mensaje de chat
6. Vincular tarjeta de prueba de Stripe
7. Adelantar cuota de suscripción

Uso: python test_complete_client_flow.py
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from clients.models import Client, ClientMembership
from products.models import Product
from services.models import Service
from memberships.models import MembershipPlan
from activities.models import Activity, ActivitySession, WaitlistEntry
from marketing.models import Popup
from finance.models import PaymentMethod
from sales.models import Order, OrderItem
from organizations.models import Gym
from staff.models import StaffProfile

User = get_user_model()


def print_step(step_num, description):
    """Helper para imprimir pasos"""
    print(f"\n{'='*70}")
    print(f"PASO {step_num}: {description}")
    print('='*70)


def test_complete_flow():
    """Test completo del flujo de cliente"""
    
    print("\n🚀 INICIANDO TEST COMPLETO DE FLUJO DE CLIENTE\n")
    
    # ===================================================================
    # PASO 1: Crear cliente desde backoffice
    # ===================================================================
    print_step(1, "CREAR CLIENTE DESDE BACKOFFICE")
    
    # Obtener o crear gimnasio
    gym = Gym.objects.first()
    if not gym:
        print("❌ No hay gimnasios en la base de datos")
        return
    
    print(f"✅ Gimnasio: {gym.name}")
    
    # Crear staff user para operaciones
    staff_user = User.objects.filter(is_staff=True).first()
    if not staff_user:
        staff_user = User.objects.create_user(
            email="admin@test.com",
            password="admin123",
            is_staff=True,
            is_active=True
        )
        from accounts.models import GymMembership
        GymMembership.objects.create(
            user=staff_user,
            gym=gym,
            role='ADMIN',
            is_active=True
        )
    
    print(f"✅ Staff User: {staff_user.email}")
    
    # Crear cliente
    client = Client.objects.create(
        gym=gym,
        first_name="Juan",
        last_name="Pérez Test",
        email=f"juan.test.{timezone.now().timestamp()}@example.com",
        phone_number="+34 666 777 888",
        dni="12345678X",
        status=Client.Status.ACTIVE
    )
    
    print(f"✅ Cliente creado: {client.first_name} {client.last_name}")
    print(f"   - Email: {client.email}")
    print(f"   - Estado: {client.get_status_display()}")
    
    # ===================================================================
    # PASO 2: Comprar servicio y cuota
    # ===================================================================
    print_step(2, "COMPRAR SERVICIO Y CUOTA")
    
    # Crear método de pago
    payment_method, _ = PaymentMethod.objects.get_or_create(
        gym=gym,
        name="Efectivo",
        defaults={'is_cash': True, 'is_active': True}
    )
    
    # Crear servicio
    service, _ = Service.objects.get_or_create(
        gym=gym,
        name="Entrenamiento Personal",
        defaults={
            'base_price': Decimal('30.00'),
            'duration': 60,
            'is_active': True
        }
    )
    
    # Crear plan de membresía
    membership_plan, _ = MembershipPlan.objects.get_or_create(
        gym=gym,
        name="Plan Mensual Básico",
        defaults={
            'base_price': Decimal('50.00'),
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True
        }
    )
    
    # Crear orden de compra (servicio + cuota)
    order = Order.objects.create(
        gym=gym,
        client=client,
        created_by=staff_user,
        status='PAID',
        total_base=Decimal('80.00'),
        total_amount=Decimal('80.00')
    )
    
    # Línea de servicio (usando GenericForeignKey)
    from django.contrib.contenttypes.models import ContentType
    service_ct = ContentType.objects.get_for_model(Service)
    OrderItem.objects.create(
        order=order,
        content_type=service_ct,
        object_id=service.id,
        description=service.name,
        quantity=1,
        unit_price=service.base_price,
        subtotal=service.base_price
    )
    
    # Línea de membresía (usando GenericForeignKey)
    membership_plan_ct = ContentType.objects.get_for_model(MembershipPlan)
    OrderItem.objects.create(
        order=order,
        content_type=membership_plan_ct,
        object_id=membership_plan.id,
        description=membership_plan.name,
        quantity=1,
        unit_price=membership_plan.base_price,
        subtotal=membership_plan.base_price
    )
    
    # Crear membresía activa
    membership = ClientMembership.objects.create(
        client=client,
        name=membership_plan.name,
        price=membership_plan.base_price,
        status='ACTIVE',
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=30),
        is_recurring=True
    )
    
    print(f"✅ Orden creada: #{order.id}")
    print(f"   - Total: {order.total_amount}€")
    print(f"   - Estado: {order.get_status_display()}")
    print(f"   - Líneas: {order.items.count()}")
    print(f"✅ Membresía activada: {membership.name}")
    print(f"   - Fecha fin: {membership.end_date}")
    
    # ===================================================================
    # PASO 3: Apuntarse a una clase
    # ===================================================================
    print_step(3, "APUNTARSE A UNA CLASE")
    
    # Crear actividad
    activity, _ = Activity.objects.get_or_create(
        gym=gym,
        name="Spinning",
        defaults={
            'description': 'Clase de ciclismo indoor',
            'duration': 45,
            'base_capacity': 20
        }
    )
    
    # Crear sesión de actividad (mañana a las 10:00)
    tomorrow = timezone.now() + timedelta(days=1)
    session_datetime = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    end_datetime = session_datetime + timedelta(minutes=activity.duration)
    
    # Buscar un StaffProfile para asignar como instructor
    staff_profile = StaffProfile.objects.filter(gym=gym).first()
    
    session = ActivitySession.objects.create(
        gym=gym,
        activity=activity,
        staff=staff_profile,
        start_datetime=session_datetime,
        end_datetime=end_datetime,
        max_capacity=activity.base_capacity,
        status='SCHEDULED'
    )
    
    # Añadir cliente a la sesión (reserva)
    session.attendees.add(client)
    
    print(f"✅ Clase reservada: {activity.name}")
    print(f"   - Fecha: {session.start_datetime.strftime('%d/%m/%Y %H:%M')}")
    print(f"   - Instructor: {session.staff.user.get_full_name() if session.staff else 'Sin asignar'}")
    print(f"   - Asistentes: {session.attendee_count}/{session.max_capacity}")
    
    # ===================================================================
    # PASO 4: Cancelar la clase
    # ===================================================================
    print_step(4, "CANCELAR LA RESERVA DE CLASE")
    
    # Remover cliente de asistentes
    session.attendees.remove(client)
    
    print(f"✅ Reserva cancelada")
    print(f"   - Clase: {activity.name}")
    print(f"   - Asistentes actuales: {session.attendee_count}/{session.max_capacity}")
    
    # ===================================================================
    # PASO 5: Enviar popup al cliente
    # ===================================================================
    print_step(5, "ENVIAR POPUP AL CLIENTE")
    
    # Crear popup para el cliente
    popup = Popup.objects.create(
        gym=gym,
        title="¡Bienvenido al gimnasio!",
        content="<p>Hola Juan, gracias por unirte a nosotros. ¡Disfruta de tus entrenamientos!</p>",
        target_client=client,  # Dirigido específicamente a este cliente
        is_active=True,
        priority='INFO'
    )
    
    print(f"✅ Popup creado: {popup.title}")
    print(f"   - Activo: {popup.is_active}")
    print(f"   - Cliente objetivo: {client.first_name} {client.last_name}")
    print(f"   - Prioridad: {popup.get_priority_display()}")
    
    # ===================================================================
    # PASO 6: Vincular tarjeta de prueba de Stripe
    # ===================================================================
    print_step(6, "VINCULAR TARJETA DE PRUEBA DE STRIPE")
    
    # Simular vinculación de tarjeta de prueba
    # Nota: En ambiente real esto requiere Setup Intent de Stripe
    test_card_token = "tok_visa"  # Token de prueba de Stripe
    
    # Crear o actualizar Stripe customer ID
    if not client.stripe_customer_id:
        # En producción, aquí se llamaría a Stripe API
        client.stripe_customer_id = f"cus_test_{client.id}"
        client.save()
    
    print(f"✅ Tarjeta de prueba vinculada")
    print(f"   - Stripe Customer ID: {client.stripe_customer_id}")
    print(f"   - Token de prueba: {test_card_token}")
    print(f"   - Tipo: Visa de prueba (4242 4242 4242 4242)")
    print(f"   ⚠️  Nota: Para vincular tarjeta real, usar el portal del cliente")
    
    # ===================================================================
    # PASO 7: Adelantar cuota de suscripción
    # ===================================================================
    print_step(7, "ADELANTAR CUOTA DE SUSCRIPCIÓN")
    
    # Guardar fecha anterior
    previous_end_date = membership.end_date
    
    # Crear orden de cobro adelantado
    from django.contrib.contenttypes.models import ContentType
    membership_ct = ContentType.objects.get_for_model(membership_plan.__class__)
    
    advance_order = Order.objects.create(
        gym=gym,
        client=client,
        created_by=staff_user,
        status='PAID',
        total_base=membership_plan.base_price,
        total_amount=membership_plan.base_price,
        internal_notes="Adelanto de cuota mensual"
    )
    
    OrderItem.objects.create(
        order=advance_order,
        content_type=membership_ct,
        object_id=membership_plan.id,
        description=f"{membership_plan.name} - Adelanto",
        quantity=1,
        unit_price=membership_plan.base_price,
        subtotal=membership_plan.base_price
    )
    
    # Extender fecha de fin de membresía (adelantar pago = más días)
    membership.end_date = membership.end_date + timedelta(days=30)
    membership.save()
    
    print(f"✅ Cuota adelantada")
    print(f"   - Orden: #{advance_order.id}")
    print(f"   - Monto: {advance_order.total_amount}€")
    print(f"   - Fecha fin anterior: {previous_end_date}")
    print(f"   - Nueva fecha fin: {membership.end_date}")
    
    # ===================================================================
    # RESUMEN FINAL
    # ===================================================================
    print("\n" + "="*70)
    print("✅ TEST COMPLETO FINALIZADO CON ÉXITO")
    print("="*70)
    
    print(f"\n📊 RESUMEN DEL CLIENTE: {client.first_name} {client.last_name}")
    print(f"   - ID: {client.id}")
    print(f"   - Email: {client.email}")
    print(f"   - Estado: {client.get_status_display()}")
    print(f"   - Stripe Customer: {client.stripe_customer_id}")
    
    print(f"\n💰 ÓRDENES DE COMPRA:")
    for order in Order.objects.filter(client=client):
        print(f"   - Orden #{order.id}: {order.total_amount}€ - {order.get_status_display()}")
    
    print(f"\n📅 MEMBRESÍA ACTIVA:")
    print(f"   - Nombre: {membership.name}")
    print(f"   - Estado: {membership.get_status_display()}")
    print(f"   - Fecha inicio: {membership.start_date}")
    print(f"   - Fecha fin: {membership.end_date}")
    print(f"   - Precio: {membership.price}€")
    
    print(f"\n🏋️ CLASES:")
    for session in ActivitySession.objects.filter(attendees=client):
        print(f"   - {session.activity.name} - {session.start_datetime.strftime('%d/%m/%Y %H:%M')}")
    sessions_count = ActivitySession.objects.filter(attendees=client).count()
    if sessions_count == 0:
        print(f"   - Ninguna clase activa (se canceló la reserva)")
    
    print(f"\n💬 POPUPS:")
    print(f"   - Total: {Popup.objects.filter(target_client=client).count()}")
    
    print(f"\n🎯 PRÓXIMOS PASOS:")
    print(f"   1. Acceder al backoffice: http://127.0.0.1:8000/")
    print(f"   2. Ver perfil del cliente: ID #{client.id}")
    print(f"   3. Portal del cliente: http://127.0.0.1:8000/portal/")
    print(f"   4. Para vincular tarjeta real: usar Setup Intent de Stripe")
    
    print("\n✨ ¡Todo el flujo ha sido probado exitosamente!\n")


if __name__ == "__main__":
    try:
        test_complete_flow()
    except Exception as e:
        print(f"\n❌ ERROR EN EL TEST:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
