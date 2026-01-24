"""
Test script para verificar la funcionalidad de reservas con pago pendiente.

Este script prueba:
1. Cliente con membresía PENDING_PAYMENT y opción DESACTIVADA -> No puede reservar
2. Cliente con membresía PENDING_PAYMENT y opción ACTIVADA -> Puede reservar
3. Cliente con membresía ACTIVE -> Siempre puede reservar
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from clients.models import Client, ClientMembership
from organizations.models import Gym
from activities.models import Activity, ActivitySession, ActivitySessionBooking
from accounts.models import User


def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_result(test_name, passed, message=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if message:
        print(f"       {message}")


def setup_test_data():
    """Prepara datos de prueba"""
    print_header("PREPARANDO DATOS DE PRUEBA")
    
    # Obtener el primer gimnasio
    gym = Gym.objects.first()
    if not gym:
        print("❌ No hay gimnasios en la base de datos")
        return None, None, None, None
    
    print(f"📍 Gimnasio: {gym.name} (ID: {gym.id})")
    print(f"   allow_booking_with_pending_payment: {gym.allow_booking_with_pending_payment}")
    
    # Buscar o crear un cliente con membresía PENDING_PAYMENT
    client_pending = None
    membership_pending = ClientMembership.objects.filter(
        status='PENDING_PAYMENT',
        client__gym=gym
    ).select_related('client').first()
    
    if membership_pending:
        client_pending = membership_pending.client
        print(f"👤 Cliente con PENDING_PAYMENT encontrado: {client_pending}")
    else:
        # Crear uno si no existe
        client_pending = Client.objects.filter(gym=gym, user__isnull=False).first()
        if client_pending:
            # Crear membresía PENDING_PAYMENT
            membership_pending = ClientMembership.objects.create(
                client=client_pending,
                gym=gym,
                name="Plan Test Pending",
                start_date=timezone.now().date() - timedelta(days=30),
                end_date=timezone.now().date() + timedelta(days=30),
                price=50,
                status='PENDING_PAYMENT',
                is_recurring=True
            )
            print(f"👤 Cliente configurado con PENDING_PAYMENT: {client_pending}")
        else:
            print("❌ No hay clientes con usuario vinculado")
            return None, None, None, None
    
    # Buscar o crear un cliente con membresía ACTIVE
    client_active = None
    membership_active = ClientMembership.objects.filter(
        status='ACTIVE',
        client__gym=gym
    ).exclude(client=client_pending).select_related('client').first()
    
    if membership_active:
        client_active = membership_active.client
        print(f"👤 Cliente con ACTIVE encontrado: {client_active}")
    else:
        client_active = Client.objects.filter(gym=gym, user__isnull=False).exclude(id=client_pending.id).first()
        if client_active:
            membership_active = ClientMembership.objects.create(
                client=client_active,
                gym=gym,
                name="Plan Test Active",
                start_date=timezone.now().date() - timedelta(days=30),
                end_date=timezone.now().date() + timedelta(days=30),
                price=50,
                status='ACTIVE',
                is_recurring=True
            )
            print(f"👤 Cliente configurado con ACTIVE: {client_active}")
    
    # Buscar una sesión futura disponible
    session = ActivitySession.objects.filter(
        activity__gym=gym,
        start_datetime__gte=timezone.now()
    ).first()
    
    if not session:
        # Crear una actividad y sesión de prueba
        activity = Activity.objects.filter(gym=gym).first()
        if activity:
            session = ActivitySession.objects.create(
                activity=activity,
                start_datetime=timezone.now() + timedelta(hours=2),
                end_datetime=timezone.now() + timedelta(hours=3),
                max_capacity=20,
                status='SCHEDULED'
            )
            print(f"📅 Sesión creada: {session}")
        else:
            print("❌ No hay actividades para crear sesión")
            return None, None, None, None
    else:
        print(f"📅 Sesión encontrada: {session.activity.name} - {session.start_datetime}")
    
    return gym, client_pending, client_active, session


def cleanup_test_bookings(client, session):
    """Limpia reservas de prueba anteriores"""
    ActivitySessionBooking.objects.filter(
        client=client,
        session=session
    ).delete()


def test_booking(client, session, gym, expected_success):
    """Simula una reserva y verifica el resultado"""
    # Limpiar reservas previas
    cleanup_test_bookings(client, session)
    
    # Verificar si tiene membresía válida según la configuración
    valid_statuses = ['ACTIVE']
    if gym.allow_booking_with_pending_payment:
        valid_statuses.append('PENDING_PAYMENT')
    
    has_valid_membership = client.memberships.filter(status__in=valid_statuses).exists()
    
    if has_valid_membership:
        # Crear reserva
        booking = ActivitySessionBooking.objects.create(
            session=session,
            client=client,
            status='CONFIRMED',
            booked_at=timezone.now()
        )
        return True, f"Reserva creada (ID: {booking.id})"
    else:
        # No tiene membresía válida
        has_pending = client.memberships.filter(status='PENDING_PAYMENT').exists()
        if has_pending:
            return False, "Membresía con pago pendiente - reserva bloqueada"
        return False, "Sin membresía activa"


def run_tests():
    """Ejecuta todos los tests"""
    gym, client_pending, client_active, session = setup_test_data()
    
    if not all([gym, client_pending, session]):
        print("\n❌ No se pudieron preparar los datos de prueba")
        return
    
    # ========================================
    # TEST 1: Opción DESACTIVADA + PENDING_PAYMENT
    # ========================================
    print_header("TEST 1: Opción DESACTIVADA + Cliente PENDING_PAYMENT")
    
    gym.allow_booking_with_pending_payment = False
    gym.save()
    print(f"⚙️  allow_booking_with_pending_payment = {gym.allow_booking_with_pending_payment}")
    
    success, message = test_booking(client_pending, session, gym, expected_success=False)
    print_result(
        "Cliente con PENDING_PAYMENT NO debe poder reservar",
        success == False,
        message
    )
    
    # ========================================
    # TEST 2: Opción ACTIVADA + PENDING_PAYMENT
    # ========================================
    print_header("TEST 2: Opción ACTIVADA + Cliente PENDING_PAYMENT")
    
    gym.allow_booking_with_pending_payment = True
    gym.save()
    print(f"⚙️  allow_booking_with_pending_payment = {gym.allow_booking_with_pending_payment}")
    
    success, message = test_booking(client_pending, session, gym, expected_success=True)
    print_result(
        "Cliente con PENDING_PAYMENT SÍ debe poder reservar",
        success == True,
        message
    )
    
    # Limpiar la reserva creada
    cleanup_test_bookings(client_pending, session)
    
    # ========================================
    # TEST 3: Cliente ACTIVE (siempre puede reservar)
    # ========================================
    if client_active:
        print_header("TEST 3: Cliente ACTIVE (Opción irrelevante)")
        
        # Con opción desactivada
        gym.allow_booking_with_pending_payment = False
        gym.save()
        print(f"⚙️  allow_booking_with_pending_payment = {gym.allow_booking_with_pending_payment}")
        
        success, message = test_booking(client_active, session, gym, expected_success=True)
        print_result(
            "Cliente ACTIVE siempre debe poder reservar",
            success == True,
            message
        )
        cleanup_test_bookings(client_active, session)
    
    # ========================================
    # Restaurar configuración original
    # ========================================
    print_header("RESUMEN")
    gym.allow_booking_with_pending_payment = False
    gym.save()
    print("⚙️  Configuración restaurada: allow_booking_with_pending_payment = False")
    
    print("\n🏁 Tests completados")


if __name__ == "__main__":
    run_tests()
