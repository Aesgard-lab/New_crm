import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from organizations.models import Gym
from finance.models import FinanceSettings

# Buscar el gimnasio
gym = Gym.objects.get(slug='qombo-arganzuela')
print(f"Gimnasio: {gym.name}")

# Obtener o crear FinanceSettings
finance_settings, created = FinanceSettings.objects.get_or_create(
    gym=gym,
    defaults={
        'currency': 'EUR',
        'app_gateway_strategy': 'STRIPE_ONLY',
        'pos_gateway_strategy': 'STRIPE_ONLY',
    }
)

if created:
    print("✓ FinanceSettings creado")
else:
    print("✓ FinanceSettings existente")

# Configurar claves de Stripe de prueba desde variables de entorno
import os
finance_settings.stripe_public_key = os.environ.get('STRIPE_PUBLIC_KEY', 'pk_test_YOUR_KEY_HERE')
finance_settings.stripe_secret_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_YOUR_KEY_HERE')
finance_settings.app_gateway_strategy = 'STRIPE_ONLY'
finance_settings.pos_gateway_strategy = 'STRIPE_ONLY'
finance_settings.save()

print("\n=== Configuración Final ===")
print(f"Stripe Public Key: {finance_settings.stripe_public_key[:20]}...")
print(f"Stripe Secret Key: {'✓ Configurada' if finance_settings.stripe_secret_key else '✗ No configurada'}")
print(f"App Gateway Strategy: {finance_settings.app_gateway_strategy}")
print(f"POS Gateway Strategy: {finance_settings.pos_gateway_strategy}")
print(f"has_stripe: {finance_settings.has_stripe}")
print(f"has_redsys: {finance_settings.has_redsys}")
print(f"\n✓ Configuración de Stripe completada")
