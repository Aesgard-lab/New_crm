"""Script para crear planes de test"""
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from organizations.models import Gym
from memberships.models import MembershipPlan
from clients.models import Client, ClientPaymentMethod

gym = Gym.objects.get(id=1)
print(f"Gimnasio: {gym.name}")

# Crear un segundo plan
plan2, created = MembershipPlan.objects.get_or_create(
    gym=gym,
    name='Plan Premium Mensual',
    defaults={
        'description': 'Acceso ilimitado a todas las clases y gimnasio',
        'base_price': 59.00,
        'is_recurring': True,
        'frequency_amount': 1,
        'frequency_unit': 'MONTH',
        'is_active': True,
        'is_visible_online': True,
    }
)
print(f"Plan Premium: {'Creado' if created else 'Ya existe'}")

# Crear tercer plan más barato
plan3, created = MembershipPlan.objects.get_or_create(
    gym=gym,
    name='Plan Basico',
    defaults={
        'description': '4 sesiones al mes - Ideal para empezar',
        'base_price': 35.00,
        'is_recurring': True,
        'frequency_amount': 1,
        'frequency_unit': 'MONTH',
        'is_active': True,
        'is_visible_online': True,
    }
)
print(f"Plan Basico: {'Creado' if created else 'Ya existe'}")

# Verificar cliente
client = Client.objects.filter(user__email='demo@example.com', gym=gym).first()
print(f"\nCliente: {client.user.email}")

memberships = client.memberships.filter(status__in=['ACTIVE', 'PENDING'])
print(f"Membresias activas: {memberships.count()}")
for m in memberships:
    print(f"  - {m.name}: {m.status}, fin: {m.end_date}")

# Verificar/crear método de pago para el test
pms = client.payment_methods.all()
print(f"Tarjetas guardadas: {pms.count()}")
if pms.count() == 0:
    # Crear tarjeta de test
    pm = ClientPaymentMethod.objects.create(
        client=client,
        card_type='visa',
        last_4='4242',
        expiry_month=12,
        expiry_year=2028,
        cardholder_name='Cliente Demo',
        is_default=True
    )
    print(f"  Creada tarjeta de test: VISA ****4242")
else:
    for pm in pms:
        print(f"  - {pm.card_type.upper()} ****{pm.last_4}")

print("\n--- Planes disponibles en tienda ---")
for p in MembershipPlan.objects.filter(gym=gym, is_active=True, is_visible_online=True):
    print(f"  {p.id}: {p.name} - {p.base_price}€")

# Verificar configuración del portal
from organizations.models import PublicPortalSettings
portal, _ = PublicPortalSettings.objects.get_or_create(
    gym=gym,
    defaults={'public_slug': 'qombo-madrid-central'}
)
print(f"\n--- Configuración Portal ---")
print(f"  allow_duplicate_membership_purchase: {portal.allow_duplicate_membership_purchase}")
print(f"  allow_membership_change_at_renewal: {portal.allow_membership_change_at_renewal}")
print(f"  duplicate_membership_message: {portal.duplicate_membership_message[:50]}...")

print("\n✅ Setup completado!")
