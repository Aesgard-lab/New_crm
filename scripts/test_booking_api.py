"""
Test de la API de reservas con el flujo completo.
Simula llamadas reales a la API BookSessionView.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIRequestFactory
from api.schedule_views import BookSessionView
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


def run_api_tests():
    """Ejecuta tests usando la API real"""
    print_header("PREPARANDO DATOS PARA TEST DE API")
    
    # Obtener el gimnasio
    gym = Gym.objects.first()
    if not gym:
        print("❌ No hay gimnasios")
        return
    
    print(f"📍 Gimnasio: {gym.name}")
    
    # Buscar cliente con usuario vinculado y membresía PENDING_PAYMENT
    client_pending = Client.objects.filter(
        gym=gym,
        user__isnull=False,
        memberships__status='PENDING_PAYMENT'
    ).first()
    
    if not client_pending:
        # Crear uno
        client_with_user = Client.objects.filter(gym=gym, user__isnull=False).first()
        if client_with_user:
            # Poner todas sus membresías en PENDING_PAYMENT
            client_with_user.memberships.update(status='PENDING_PAYMENT')
            if not client_with_user.memberships.exists():
                ClientMembership.objects.create(
                    client=client_with_user,
                    gym=gym,
                    name="Plan API Test",
                    start_date=timezone.now().date() - timedelta(days=30),
                    end_date=timezone.now().date() + timedelta(days=30),
                    price=50,
                    status='PENDING_PAYMENT',
                    is_recurring=True
                )
            client_pending = client_with_user
            print(f"👤 Cliente configurado: {client_pending} (User: {client_pending.user})")
        else:
            print("❌ No hay clientes con usuario")
            return
    else:
        print(f"👤 Cliente con PENDING_PAYMENT: {client_pending}")
    
    # Buscar sesión futura
    session = ActivitySession.objects.filter(
        activity__gym=gym,
        start_datetime__gt=timezone.now()
    ).first()
    
    if not session:
        activity = Activity.objects.filter(gym=gym).first()
        if activity:
            session = ActivitySession.objects.create(
                activity=activity,
                start_datetime=timezone.now() + timedelta(hours=3),
                end_datetime=timezone.now() + timedelta(hours=4),
                max_capacity=20,
                status='SCHEDULED'
            )
        else:
            print("❌ No hay actividades")
            return
    
    print(f"📅 Sesión: {session.activity.name} - {session.start_datetime}")
    
    # Limpiar reservas previas del test
    ActivitySessionBooking.objects.filter(client=client_pending, session=session).delete()
    
    # Crear factory y view
    factory = APIRequestFactory()
    view = BookSessionView.as_view()
    
    # ========================================
    # TEST API 1: Opción DESACTIVADA
    # ========================================
    print_header("TEST API 1: Opción DESACTIVADA + PENDING_PAYMENT")
    
    gym.allow_booking_with_pending_payment = False
    gym.save()
    print(f"⚙️  allow_booking_with_pending_payment = {gym.allow_booking_with_pending_payment}")
    
    # Hacer request
    request = factory.post('/api/schedule/book/', {'session_id': session.id}, format='json')
    request.user = client_pending.user
    
    response = view(request)
    
    print(f"   Response status: {response.status_code}")
    print(f"   Response data: {response.data}")
    
    print_result(
        "API debe rechazar reserva (403)",
        response.status_code == 403,
        f"Status: {response.status_code}, Error: {response.data.get('error', 'N/A')}"
    )
    
    # ========================================
    # TEST API 2: Opción ACTIVADA
    # ========================================
    print_header("TEST API 2: Opción ACTIVADA + PENDING_PAYMENT")
    
    gym.allow_booking_with_pending_payment = True
    gym.save()
    print(f"⚙️  allow_booking_with_pending_payment = {gym.allow_booking_with_pending_payment}")
    
    # Limpiar reservas previas
    ActivitySessionBooking.objects.filter(client=client_pending, session=session).delete()
    
    request = factory.post('/api/schedule/book/', {'session_id': session.id}, format='json')
    request.user = client_pending.user
    
    response = view(request)
    
    print(f"   Response status: {response.status_code}")
    print(f"   Response data: {response.data}")
    
    print_result(
        "API debe aceptar reserva (201)",
        response.status_code == 201,
        f"Status: {response.status_code}"
    )
    
    # Verificar que se creó la reserva
    booking_exists = ActivitySessionBooking.objects.filter(
        client=client_pending,
        session=session,
        status='CONFIRMED'
    ).exists()
    
    print_result(
        "Reserva existe en la base de datos",
        booking_exists,
        "Reserva confirmada en DB" if booking_exists else "No se encontró la reserva"
    )
    
    # ========================================
    # Cleanup
    # ========================================
    print_header("LIMPIEZA Y RESUMEN")
    
    # Restaurar configuración
    gym.allow_booking_with_pending_payment = False
    gym.save()
    
    # Limpiar reservas de test
    ActivitySessionBooking.objects.filter(client=client_pending, session=session).delete()
    
    print("✅ Configuración restaurada")
    print("✅ Reservas de prueba eliminadas")
    print("\n🏁 Tests de API completados")


if __name__ == "__main__":
    run_api_tests()
