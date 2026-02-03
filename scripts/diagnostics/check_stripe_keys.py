import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from organizations.models import Gym
from finance.models import FinanceSettings

gym = Gym.objects.get(slug='qombo-arganzuela')
finance_settings = FinanceSettings.objects.get(gym=gym)

print(f"\n=== Stripe Keys ===")
print(f"Public Key Length: {len(finance_settings.stripe_public_key or '')}")
print(f"Public Key: {finance_settings.stripe_public_key[:20]}..." if finance_settings.stripe_public_key else "None")
print(f"\nSecret Key Length: {len(finance_settings.stripe_secret_key or '')}")
print(f"Secret Key: {finance_settings.stripe_secret_key[:20]}..." if finance_settings.stripe_secret_key else "None")
