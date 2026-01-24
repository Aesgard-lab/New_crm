"""Script para crear datos de demostración completos para el cliente demo."""
import os
import django
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from clients.models import Client, ClientMembership
from organizations.models import Gym
from activities.models import Activity, ActivitySession, ActivitySessionBooking
from memberships.models import MembershipPlan

User = get_user_model()

# Obtener el cliente demo
try:
    user = User.objects.get(email='demo@qombo.com')
    client = Client.objects.get(user=user)
    gym = client.gym
    print(f"✅ Cliente encontrado: {client.first_name} {client.last_name}")
    print(f"   Gimnasio: {gym.name}")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# 1. Crear Plan de Membresía si no existe
print("\n📋 Creando plan de membresía...")
plan, created = MembershipPlan.objects.get_or_create(
    gym=gym,
    name="Plan Premium",
    defaults={
        'description': 'Acceso ilimitado a todas las instalaciones y clases',
        'base_price': Decimal('49.99'),
        'frequency_amount': 1,
        'frequency_unit': 'MONTH',
        'is_recurring': True,
        'is_active': True
    }
)
print(f"   Plan: {plan.name} - {'Creado' if created else 'Ya existía'}")

# 2. Crear Membresía activa para el cliente
print("\n💳 Creando membresía activa...")
membership, created = ClientMembership.objects.get_or_create(
    client=client,
    defaults={
        'gym': gym,
        'plan': plan,
        'name': plan.name,
        'start_date': timezone.now().date() - timedelta(days=15),
        'end_date': timezone.now().date() + timedelta(days=15),
        'price': plan.base_price,
        'status': 'ACTIVE',
        'is_recurring': True
    }
)
if not created:
    membership.status = 'ACTIVE'
    membership.end_date = timezone.now().date() + timedelta(days=15)
    membership.save()
print(f"   Membresía: {membership.name} - {'Creada' if created else 'Actualizada'}")
print(f"   Válida hasta: {membership.end_date}")

# 3. Crear Actividades si no existen
print("\n🏋️ Creando actividades...")
activities_data = [
    {'name': 'Spinning', 'duration': 45, 'capacity': 20, 'color': '#ef4444'},
    {'name': 'Yoga', 'duration': 60, 'capacity': 15, 'color': '#22c55e'},
    {'name': 'CrossFit', 'duration': 50, 'capacity': 12, 'color': '#3b82f6'},
    {'name': 'Pilates', 'duration': 55, 'capacity': 10, 'color': '#a855f7'},
    {'name': 'Boxeo', 'duration': 45, 'capacity': 16, 'color': '#f97316'},
]

activities = []
for act_data in activities_data:
    activity, created = Activity.objects.get_or_create(
        gym=gym,
        name=act_data['name'],
        defaults={
            'description': f"Clase de {act_data['name']}",
            'duration': act_data['duration'],
            'base_capacity': act_data['capacity'],
            'color': act_data['color'],
            'is_visible_online': True
        }
    )
    activities.append(activity)
    print(f"   {activity.name} - {'Creado' if created else 'Ya existía'}")

# 4. Crear Sesiones de actividades (próximos días)
print("\n📅 Creando sesiones de actividades...")
now = timezone.now()
sessions_created = 0

for i, activity in enumerate(activities):
    # Crear sesiones para los próximos 7 días
    for day_offset in range(7):
        session_date = now.date() + timedelta(days=day_offset)
        # Horarios variados
        hours = [9, 11, 17, 19]
        hour = hours[i % len(hours)]
        
        session_datetime = timezone.make_aware(
            datetime.combine(session_date, datetime.min.time().replace(hour=hour, minute=0))
        )
        
        session, created = ActivitySession.objects.get_or_create(
            gym=gym,
            activity=activity,
            start_datetime=session_datetime,
            defaults={
                'end_datetime': session_datetime + timedelta(minutes=activity.duration),
                'max_capacity': activity.base_capacity,
                'status': 'SCHEDULED'
            }
        )
        if created:
            sessions_created += 1

print(f"   {sessions_created} sesiones creadas")

# 5. Crear Reservas para el cliente
print("\n📝 Creando reservas...")
# Reservas futuras
future_sessions = ActivitySession.objects.filter(
    activity__gym=gym,
    start_datetime__gte=now
).order_by('start_datetime')[:5]

bookings_created = 0
for session in future_sessions:
    booking, created = ActivitySessionBooking.objects.get_or_create(
        client=client,
        session=session,
        defaults={
            'status': 'CONFIRMED',
            'attendance_status': 'PENDING'
        }
    )
    if created:
        bookings_created += 1
        print(f"   ✓ {session.activity.name} - {session.start_datetime.strftime('%d/%m %H:%M')}")

print(f"   {bookings_created} reservas futuras creadas")

# Reservas pasadas (historial)
print("\n📜 Creando historial de asistencias...")
past_sessions = []
for activity in activities[:3]:
    for day_offset in range(1, 15):  # Últimos 14 días
        session_date = now.date() - timedelta(days=day_offset)
        session_datetime = timezone.make_aware(
            datetime.combine(session_date, datetime.min.time().replace(hour=10, minute=0))
        )
        
        session, created = ActivitySession.objects.get_or_create(
            gym=gym,
            activity=activity,
            start_datetime=session_datetime,
            defaults={
                'end_datetime': session_datetime + timedelta(minutes=activity.duration),
                'max_capacity': activity.base_capacity,
                'status': 'COMPLETED'
            }
        )
        past_sessions.append(session)

# Crear algunas reservas pasadas completadas
attended = 0
for i, session in enumerate(past_sessions[:20]):
    if i % 3 == 0:  # Asistió a 1 de cada 3
        booking, created = ActivitySessionBooking.objects.get_or_create(
            client=client,
            session=session,
            defaults={
                'status': 'CONFIRMED',
                'attendance_status': 'ATTENDED',
                'attended': True
            }
        )
        if created:
            attended += 1

print(f"   {attended} asistencias históricas creadas")

# 6. Actualizar estado del cliente a ACTIVE
client.status = 'ACTIVE'
client.save()
print(f"\n✅ Cliente actualizado a estado: ACTIVO")

print("\n" + "="*50)
print("🎉 DATOS DE DEMOSTRACIÓN CREADOS EXITOSAMENTE")
print("="*50)
print(f"\n📊 Resumen:")
print(f"   • Membresía: {plan.name} (válida hasta {membership.end_date})")
print(f"   • Actividades: {len(activities)}")
print(f"   • Reservas futuras: {bookings_created}")
print(f"   • Historial de asistencias: {attended}")
print(f"\n🔐 Credenciales:")
print(f"   Email: demo@qombo.com")
print(f"   Password: demo1234")
