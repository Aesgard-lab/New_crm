import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from organizations.models import Gym
from finance.models import FinanceSettings

# Pega aquí tus claves reales de Stripe
STRIPE_PUBLIC_KEY = "pk_test_TU_CLAVE_PUBLICA_AQUI"
STRIPE_SECRET_KEY = "sk_test_TU_CLAVE_SECRETA_AQUI"

gym = Gym.objects.get(slug='qombo-arganzuela')
finance_settings = FinanceSettings.objects.get(gym=gym)

finance_settings.stripe_public_key = STRIPE_PUBLIC_KEY
finance_settings.stripe_secret_key = STRIPE_SECRET_KEY
finance_settings.save()

print(f"\n✓ Claves de Stripe actualizadas para {gym.name}")
print(f"Public Key: {finance_settings.stripe_public_key[:20]}...")
print(f"Secret Key: {finance_settings.stripe_secret_key[:20]}...")
