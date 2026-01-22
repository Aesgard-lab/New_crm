"""
Script de prueba: Crear sesiones de clase y calcular comisiones automáticamente

Este script demuestra el sistema completo de comisiones:
1. Crea reglas de incentivos
2. Crea sesiones de clases
3. Calcula comisiones automáticamente
4. Muestra el resumen en la ficha del empleado

Ejecutar:
python manage.py shell < create_test_commissions.py
"""

from django.utils import timezone
from datetime import datetime, timedelta, time
from decimal import Decimal

from staff.models import StaffProfile, IncentiveRule, StaffCommission
from activities.models import Activity, ActivitySession, ActivityCategory, Room
from organizations.models import Gym

print("\n" + "="*70)
print("🧪 TEST: SISTEMA DE COMISIONES AUTOMÁTICAS")
print("="*70 + "\n")

# Obtener gym y staff
gym = Gym.objects.first()
staff = StaffProfile.objects.filter(gym=gym, is_active=True).first()

if not gym or not staff:
    print("❌ No hay gym o staff disponible. Crea primero un gimnasio y empleado.")
    exit()

print(f"🏋️ Gym: {gym.name}")
print(f"👤 Staff: {staff}")
print()

# ========================================
# PASO 1: Crear Reglas de Incentivos
# ========================================
print("📋 PASO 1: Creando Reglas de Incentivos...")
print("-" * 70)

# Regla 1: Bonus fijo por cualquier clase
rule1, created = IncentiveRule.objects.get_or_create(
    gym=gym,
    staff=staff,
    name="Bonus General Clases",
    defaults={
        'type': 'CLASS_FIXED',
        'value': Decimal('5.00'),
        'is_active': True,
    }
)
print(f"✓ Regla 1: {rule1.name} - {rule1.value}€ fijo")

# Regla 2: Bonus extra por clases nocturnas
rule2, created = IncentiveRule.objects.get_or_create(
    gym=gym,
    staff=staff,
    name="Bonus Clases Nocturnas",
    defaults={
        'type': 'CLASS_FIXED',
        'value': Decimal('3.00'),
        'time_start': time(20, 0),
        'time_end': time(23, 0),
        'is_active': True,
    }
)
print(f"✓ Regla 2: {rule2.name} - {rule2.value}€ extra (20:00-23:00)")

# Regla 3: Por asistente en clases de fin de semana
rule3, created = IncentiveRule.objects.get_or_create(
    gym=gym,
    staff=staff,
    name="Variable Fin de Semana",
    defaults={
        'type': 'CLASS_ATTENDANCE',
        'value': Decimal('0.50'),
        'weekdays': ['SAT', 'SUN'],
        'is_active': True,
    }
)
print(f"✓ Regla 3: {rule3.name} - {rule3.value}€ por asistente (Sáb/Dom)")

print()

# ========================================
# PASO 2: Crear Actividades si no existen
# ========================================
print("🎯 PASO 2: Verificando Actividades...")
print("-" * 70)

activity = Activity.objects.filter(gym=gym).first()
if not activity:
    print("⚠️ No hay actividades. Creando actividad de prueba...")
    activity = Activity.objects.create(
        gym=gym,
        name="Clase de Prueba",
        duration=60,
        base_capacity=20,
    )
    print(f"✓ Creada: {activity.name}")
else:
    print(f"✓ Usando: {activity.name}")

room = Room.objects.filter(gym=gym).first()
print()

# ========================================
# PASO 3: Crear Sesiones de Clase
# ========================================
print("📅 PASO 3: Creando Sesiones de Clase...")
print("-" * 70)

now = timezone.now()

# Sesión 1: Clase normal (mañana)
session1_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
session1, created = ActivitySession.objects.get_or_create(
    gym=gym,
    activity=activity,
    staff=staff,
    start_datetime=session1_time,
    defaults={
        'end_datetime': session1_time + timedelta(hours=1),
        'room': room,
        'max_capacity': 20,
        'status': 'COMPLETED',
    }
)

if created:
    # Simular 12 asistentes
    from clients.models import Client
    clients = Client.objects.filter(gym=gym)[:12]
    session1.attendees.set(clients)
    print(f"✓ Sesión 1: {session1} - {session1.attendee_count} asistentes")
else:
    print(f"✓ Sesión 1: Ya existe")

# Sesión 2: Clase nocturna (debe activar bonus nocturno)
session2_time = now.replace(hour=21, minute=0, second=0, microsecond=0)
session2, created = ActivitySession.objects.get_or_create(
    gym=gym,
    activity=activity,
    staff=staff,
    start_datetime=session2_time,
    defaults={
        'end_datetime': session2_time + timedelta(hours=1),
        'room': room,
        'max_capacity': 20,
        'status': 'COMPLETED',
    }
)

if created:
    from clients.models import Client
    clients = Client.objects.filter(gym=gym)[:8]
    session2.attendees.set(clients)
    print(f"✓ Sesión 2: {session2} - {session2.attendee_count} asistentes (NOCTURNA)")
else:
    print(f"✓ Sesión 2: Ya existe")

# Sesión 3: Clase de fin de semana (debe activar bonus variable)
# Buscar el próximo sábado
days_until_saturday = (5 - now.weekday()) % 7
if days_until_saturday == 0:
    days_until_saturday = 7
next_saturday = now + timedelta(days=days_until_saturday)
session3_time = next_saturday.replace(hour=11, minute=0, second=0, microsecond=0)

session3, created = ActivitySession.objects.get_or_create(
    gym=gym,
    activity=activity,
    staff=staff,
    start_datetime=session3_time,
    defaults={
        'end_datetime': session3_time + timedelta(hours=1),
        'room': room,
        'max_capacity': 20,
        'status': 'COMPLETED',
    }
)

if created:
    from clients.models import Client
    clients = Client.objects.filter(gym=gym)[:15]
    session3.attendees.set(clients)
    print(f"✓ Sesión 3: {session3} - {session3.attendee_count} asistentes (FIN DE SEMANA)")
else:
    print(f"✓ Sesión 3: Ya existe")

print()

# ========================================
# PASO 4: Calcular Comisiones
# ========================================
print("💰 PASO 4: Calculando Comisiones Automáticamente...")
print("-" * 70)

sessions = [session1, session2, session3]
total_earned = Decimal('0.00')

for idx, session in enumerate(sessions, 1):
    print(f"\n🎯 Sesión {idx}: {session.activity.name} - {session.start_datetime.strftime('%d/%m/%Y %H:%M')}")
    print(f"   Asistentes: {session.attendee_count}")
    print(f"   Día: {['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'][session.start_datetime.weekday()]}")
    
    # Calcular comisiones
    commissions = StaffCommission.calculate_for_session(session)
    
    if commissions:
        print(f"   ✅ Generadas {len(commissions)} comisiones:")
        session_total = Decimal('0.00')
        for comm in commissions:
            print(f"      • {comm.rule.name}: +{comm.amount}€")
            session_total += comm.amount
        print(f"   💵 Subtotal sesión: {session_total}€")
        total_earned += session_total
    else:
        print(f"   ⚠️ No se generaron comisiones")

print("\n" + "-" * 70)
print(f"💰 TOTAL COMISIONES GENERADAS: {total_earned}€")
print()

# ========================================
# PASO 5: Mostrar Resumen
# ========================================
print("="*70)
print("📊 RESUMEN FINAL")
print("="*70)

from django.db.models import Sum
all_commissions = StaffCommission.objects.filter(staff=staff)
total_all_time = all_commissions.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

print(f"\n👤 Empleado: {staff}")
print(f"📋 Total comisiones históricas: {total_all_time}€")
print(f"🎯 Comisiones generadas en esta prueba: {total_earned}€")

# Mostrar últimas 5 comisiones
recent = all_commissions.order_by('-date')[:5]
if recent:
    print(f"\n💸 Últimas 5 comisiones:")
    for comm in recent:
        print(f"   • {comm.concept} - {comm.amount}€ ({comm.date.strftime('%d/%m/%Y %H:%M')})")

print("\n" + "="*70)
print("✅ TEST COMPLETADO")
print("="*70)

print("\n📱 Para ver el resultado:")
print(f"   1. Ve a: http://127.0.0.1:8000/staff/detail/{staff.pk}/")
print(f"   2. Verás la sección 'Comisiones Ganadas' con el detalle")
print(f"   3. Y el 'Total a Cobrar' sumando salario + comisiones")
print()
