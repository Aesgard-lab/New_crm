"""Test rápido de comisiones"""
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from staff.models import StaffProfile, IncentiveRule, StaffCommission
from activities.models import Activity, ActivitySession, Room
from organizations.models import Gym

gym = Gym.objects.first()
staff = StaffProfile.objects.filter(gym=gym, is_active=True).first()

print(f"\n🏋️ Gym: {gym.name}")
print(f"👤 Staff: {staff}\n")

# Crear regla simple
rule, created = IncentiveRule.objects.get_or_create(
    gym=gym,
    staff=staff,
    name="Test Bonus 5€",
    defaults={'type': 'CLASS_FIXED', 'value': Decimal('5.00'), 'is_active': True}
)
print(f"✅ Regla: {rule.name} - {rule.value}€")

# Buscar o crear sesión
activity = Activity.objects.filter(gym=gym).first()
room = Room.objects.filter(gym=gym).first()
now = timezone.now()

session, created = ActivitySession.objects.get_or_create(
    gym=gym,
    activity=activity,
    staff=staff,
    start_datetime=now.replace(hour=10, minute=0, second=0),
    defaults={
        'end_datetime': now.replace(hour=11, minute=0, second=0),
        'room': room,
        'max_capacity': 20,
        'status': 'COMPLETED',
    }
)
print(f"✅ Sesión: {session}\n")

# Calcular comisiones
print("💰 Calculando comisiones...")
commissions = StaffCommission.calculate_for_session(session)

if commissions:
    for comm in commissions:
        print(f"   ✅ {comm.concept} - {comm.amount}€")
else:
    print("   ⚠️ No se generaron comisiones")

# Mostrar total
from django.db.models import Sum
total = StaffCommission.objects.filter(staff=staff).aggregate(total=Sum('amount'))['total'] or 0
print(f"\n💵 Total comisiones: {total}€")
print(f"\n📱 Ver en: http://127.0.0.1:8000/staff/detail/{staff.pk}/\n")
