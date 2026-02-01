"""Script para completar el setup de test"""
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from django.utils import timezone
from datetime import timedelta
from organizations.models import Gym, PublicPortalSettings
from memberships.models import MembershipPlan
from clients.models import Client, ClientMembership

gym = Gym.objects.get(id=1)

# Eliminar plan duplicado
MembershipPlan.objects.filter(gym=gym, name='Plan Basico').delete()
print("Eliminado plan duplicado 'Plan Basico'")

# Renombrar el que tiene tilde
plan_basico = MembershipPlan.objects.filter(gym=gym, name='Plan Básico').first()
if plan_basico:
    print(f"Plan Básico existe: ID {plan_basico.id}")

# Obtener cliente
client = Client.objects.filter(user__email='demo@example.com', gym=gym).first()
print(f"\nCliente: {client.user.email}")

# Verificar si tiene membresía activa
active = client.memberships.filter(status='ACTIVE').first()
if not active:
    # Crear membresía activa
    plan = MembershipPlan.objects.filter(gym=gym, name='Cuota 8 sesiones 4 semanas').first()
    if plan:
        membership = ClientMembership.objects.create(
            client=client,
            gym=gym,
            plan=plan,
            name=plan.name,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=28),
            price=plan.base_price,
            status='ACTIVE',
            is_recurring=True,
            current_period_start=timezone.now().date(),
            current_period_end=timezone.now().date() + timedelta(days=28),
            sessions_total=8,
            sessions_used=2
        )
        print(f"  ✅ Creada membresía: {membership.name}")
        print(f"     Inicio: {membership.start_date}")
        print(f"     Fin: {membership.end_date}")
        print(f"     Sesiones: {membership.sessions_used}/{membership.sessions_total}")
else:
    print(f"  Ya tiene membresía activa: {active.name}")

# Activar las opciones de configuración para el test
portal, _ = PublicPortalSettings.objects.get_or_create(
    gym=gym,
    defaults={'public_slug': 'qombo-madrid-central'}
)

# Para probar el bloqueo: desactivamos la compra duplicada
portal.allow_duplicate_membership_purchase = False
portal.allow_membership_change_at_renewal = True
portal.save()

print("\n--- Configuración actualizada para TEST ---")
print(f"  ❌ Bloqueo compra duplicada: ACTIVADO")
print(f"  ✅ Cambio de plan al renovar: ACTIVADO")

print("\n--- Planes disponibles ---")
for p in MembershipPlan.objects.filter(gym=gym, is_active=True, is_visible_online=True):
    print(f"  • {p.name} - {p.base_price}€")

print("\n" + "="*50)
print("TEST READY!")
print("="*50)
print(f"\n1. Abre el portal del cliente: http://127.0.0.1:8000/portal/shop/")
print(f"   Login: demo@example.com")
print(f"\n2. Deberías ver:")
print(f"   - Banner amarillo: 'Ya tienes una cuota activa'")
print(f"   - Los planes con botón 'Cambiar a este plan' (verde)")
print(f"   - NO deberían tener botón 'Solicitar Información'")
print(f"\n3. Prueba hacer clic en 'Cambiar a este plan'")
print(f"   - Debería mostrar modal de confirmación")
print(f"   - Al confirmar, debería crear cambio programado")
