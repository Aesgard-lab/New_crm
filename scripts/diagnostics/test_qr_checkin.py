"""
Test script para verificar el flujo completo de Check-in por QR de sesión.

1. Crea actividades en Qombo Madrid Central
2. Crea sesiones de clase para hoy
3. Crea un cliente demo
4. Reserva el cliente en una sesión
5. Genera el QR de la sesión
6. Simula el check-in del cliente escaneando el QR
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

# Models
from organizations.models import Gym
from activities.models import (
    Activity, ActivityCategory, Room, ActivitySession, 
    ActivitySessionBooking, SessionCheckin, AttendanceSettings
)
from clients.models import Client
from accounts.models import User
from staff.models import StaffProfile

# Para generar el QR token
from activities.checkin_views import generate_qr_token, verify_qr_token
import time


def run_test():
    print("=" * 60)
    print("🧪 TEST: Check-in por QR de Sesión")
    print("=" * 60)
    
    # 1. Obtener el gimnasio Qombo Madrid Central
    print("\n📍 Buscando gimnasio Qombo Madrid Central...")
    gym = Gym.objects.filter(name__icontains="Madrid Central").first()
    if gym:
        print(f"   ✅ Encontrado: {gym.name} (ID: {gym.id})")
    else:
        print("   ❌ No se encontró el gimnasio. Creando uno...")
        from organizations.models import Franchise
        franchise = Franchise.objects.first()
        gym = Gym.objects.create(
            name="Qombo Madrid Central",
            franchise=franchise,
            address="Calle Test 123",
            city="Madrid",
            country="España"
        )
        print(f"   ✅ Creado: {gym.name}")
    
    # 2. Crear configuración de asistencia si no existe
    print("\n⚙️ Configurando settings de asistencia...")
    att_settings, created = AttendanceSettings.objects.get_or_create(
        gym=gym,
        defaults={
            'qr_checkin_minutes_before': 30,  # 30 minutos antes
            'qr_checkin_minutes_after': 60,   # 60 minutos después
            'qr_refresh_seconds': 30,
        }
    )
    if created:
        print("   ✅ Configuración creada")
    else:
        print("   ✅ Configuración existente")
    
    # 3. Crear categoría y actividades
    print("\n🏋️ Creando actividades...")
    category, _ = ActivityCategory.objects.get_or_create(
        gym=gym,
        name="Fitness"
    )
    
    # Crear sala
    room, _ = Room.objects.get_or_create(
        gym=gym,
        name="Sala Principal",
        defaults={'capacity': 20}
    )
    
    # Crear actividades con QR habilitado
    activities_data = [
        {"name": "Spinning", "duration": 45, "color": "#ef4444"},
        {"name": "Yoga", "duration": 60, "color": "#8b5cf6"},
        {"name": "CrossFit", "duration": 50, "color": "#f59e0b"},
        {"name": "Body Pump", "duration": 55, "color": "#3b82f6"},
    ]
    
    activities = []
    for data in activities_data:
        activity, created = Activity.objects.get_or_create(
            gym=gym,
            name=data["name"],
            defaults={
                'category': category,
                'duration': data["duration"],
                'color': data["color"],
                'base_capacity': 15,
                'qr_checkin_enabled': True,  # ¡Importante! Habilitar QR
                'is_visible_online': True,
            }
        )
        if not activity.qr_checkin_enabled:
            activity.qr_checkin_enabled = True
            activity.save()
        activities.append(activity)
        status = "creada" if created else "existente"
        print(f"   ✅ {activity.name} ({status}) - QR: {activity.qr_checkin_enabled}")
    
    # 4. Obtener o crear un staff
    print("\n👤 Buscando/creando staff...")
    staff = StaffProfile.objects.filter(gym=gym, is_active=True).first()
    if not staff:
        # Crear usuario para staff
        staff_user, _ = User.objects.get_or_create(
            email="trainer@qombo.com",
            defaults={
                'first_name': 'Carlos',
                'last_name': 'Trainer',
            }
        )
        staff_user.set_password('trainer123')
        staff_user.save()
        
        staff = StaffProfile.objects.create(
            user=staff_user,
            gym=gym,
            role='TRAINER',
            is_active=True
        )
    print(f"   ✅ Staff: {staff}")
    
    # 5. Crear sesiones para hoy
    print("\n📅 Creando sesiones para hoy...")
    now = timezone.now()
    today = now.date()
    
    # Crear sesiones a diferentes horas
    session_times = [
        now - timedelta(minutes=10),  # Empezó hace 10 min (dentro de ventana)
        now + timedelta(minutes=30),  # Empieza en 30 min
        now + timedelta(hours=2),     # Empieza en 2 horas
    ]
    
    sessions = []
    for i, (activity, start_time) in enumerate(zip(activities[:3], session_times)):
        end_time = start_time + timedelta(minutes=activity.duration)
        session, created = ActivitySession.objects.get_or_create(
            gym=gym,
            activity=activity,
            start_datetime=start_time,
            defaults={
                'end_datetime': end_time,
                'room': room,
                'staff': staff,
                'max_capacity': 15,
                'status': 'SCHEDULED'
            }
        )
        sessions.append(session)
        status = "creada" if created else "existente"
        print(f"   ✅ {activity.name} a las {start_time.strftime('%H:%M')} ({status})")
    
    # 6. Crear cliente demo
    print("\n🙋 Creando cliente demo...")
    demo_email = "demo.test@example.com"
    
    # Crear usuario
    demo_user, user_created = User.objects.get_or_create(
        email=demo_email,
        defaults={
            'first_name': 'Demo',
            'last_name': 'Test',
        }
    )
    if user_created:
        demo_user.set_password('demo123')
        demo_user.save()
    
    # Crear cliente
    demo_client, client_created = Client.objects.get_or_create(
        user=demo_user,
        gym=gym,
        defaults={
            'first_name': 'Demo',
            'last_name': 'Test',
            'email': demo_email,
            'phone_number': '+34600000000',
            'status': 'ACTIVE',
        }
    )
    status = "creado" if client_created else "existente"
    print(f"   ✅ Cliente: {demo_client.first_name} {demo_client.last_name} ({status})")
    print(f"      Email: {demo_email}")
    print(f"      Password: demo123")
    
    # 7. Reservar al cliente en la primera sesión (la que ya empezó)
    print("\n🎫 Creando reserva...")
    target_session = sessions[0]  # La sesión que ya empezó
    
    booking, booking_created = ActivitySessionBooking.objects.get_or_create(
        client=demo_client,
        session=target_session,
        defaults={
            'status': 'CONFIRMED',
            'attended': False
        }
    )
    if not booking_created:
        booking.status = 'CONFIRMED'
        booking.attended = False
        booking.save()
    
    print(f"   ✅ Reserva para: {target_session.activity.name}")
    print(f"      Hora: {target_session.start_datetime.strftime('%H:%M')}")
    print(f"      Estado: {booking.status}")
    
    # 8. Generar el QR token de la sesión
    print("\n🔐 Generando token QR de la sesión...")
    current_timestamp = int(time.time())
    qr_token = generate_qr_token(target_session.id, current_timestamp)
    
    print(f"   ✅ Token generado: {qr_token[:20]}...")
    print(f"      Session ID: {target_session.id}")
    
    # Verificar que el token es válido
    is_valid = verify_qr_token(qr_token, target_session.id, max_age_seconds=120)
    print(f"      Token válido: {is_valid}")
    
    # 9. Simular el check-in
    print("\n📱 Simulando CHECK-IN por QR...")
    print("-" * 40)
    
    # Verificar que no hay check-in previo
    existing_checkin = SessionCheckin.objects.filter(
        client=demo_client,
        session=target_session
    ).first()
    
    if existing_checkin:
        print(f"   ⚠️ Ya existía un check-in a las {existing_checkin.checkin_time.strftime('%H:%M')}")
        existing_checkin.delete()
        print("   🗑️ Check-in anterior eliminado para la prueba")
    
    # Verificar ventana de tiempo
    window_start = target_session.start_datetime - timedelta(minutes=att_settings.qr_checkin_minutes_before)
    window_end = target_session.start_datetime + timedelta(minutes=att_settings.qr_checkin_minutes_after)
    
    print(f"\n   📊 Ventana de check-in:")
    print(f"      Desde: {window_start.strftime('%H:%M')}")
    print(f"      Hasta: {window_end.strftime('%H:%M')}")
    print(f"      Ahora: {now.strftime('%H:%M')}")
    
    in_window = window_start <= now <= window_end
    print(f"      Dentro de ventana: {'✅ SÍ' if in_window else '❌ NO'}")
    
    if in_window:
        # Crear el check-in
        checkin = SessionCheckin.objects.create(
            session=target_session,
            client=demo_client,
            method='QR_CLIENT',
            qr_token=qr_token[:20]  # Guardamos parte del token usado
        )
        
        # Actualizar la reserva
        booking.attended = True
        booking.attendance_status = 'ATTENDED'
        booking.save()
        
        # Agregar cliente a asistentes
        target_session.attendees.add(demo_client)
        
        print(f"\n   ✅ ¡CHECK-IN EXITOSO!")
        print(f"      ID: {checkin.id}")
        print(f"      Método: {checkin.method}")
        print(f"      Hora: {checkin.checked_in_at.strftime('%H:%M:%S')}")
        print(f"      Sesión: {target_session.activity.name}")
        
    else:
        print(f"\n   ❌ Check-in fuera de ventana de tiempo")
    
    # 10. Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN DEL TEST")
    print("=" * 60)
    print(f"""
    Gimnasio: {gym.name}
    
    Actividades creadas: {len(activities)}
    Sesiones creadas: {len(sessions)}
    
    Cliente de prueba:
      - Email: {demo_email}
      - Password: demo123
    
    Sesión de prueba:
      - Actividad: {target_session.activity.name}
      - Hora: {target_session.start_datetime.strftime('%H:%M')}
      - ID: {target_session.id}
    
    Check-in:
      - Método: QR_CLIENT (cliente escaneó QR de sesión)
      - Estado: {'✅ COMPLETADO' if in_window else '⏳ PENDIENTE (fuera de ventana)'}
    
    🔗 URLs para probar:
      - Portal público: http://127.0.0.1:8000/public/gym/{gym.slug}/
      - Login cliente: http://127.0.0.1:8000/public/gym/{gym.slug}/login/
      - Escáner QR: http://127.0.0.1:8000/public/gym/{gym.slug}/qr-scanner/
      - QR de sesión (backoffice): http://127.0.0.1:8000/activities/session/{target_session.id}/qr/
    """)
    
    print("=" * 60)
    print("✅ TEST COMPLETADO")
    print("=" * 60)


if __name__ == '__main__':
    run_test()
