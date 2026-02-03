import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from organizations.models import Gym
from finance.models import FinanceSettings

gym = Gym.objects.get(slug='qombo-arganzuela')
fs = gym.finance_settings

print("=== Configuración de Pasarelas ===")
print(f"Stripe Public Key: {fs.stripe_public_key[:30] if fs.stripe_public_key else 'None'}...")
print(f"Stripe Secret Key: {'✓ Configurada' if fs.stripe_secret_key else '✗ No configurada'}")
print(f"Redsys Merchant Code: {fs.redsys_merchant_code}")
print(f"Redsys Secret Key: {'✓ Configurada' if fs.redsys_secret_key else '✗ No configurada'}")
print(f"\nApp Gateway Strategy: {fs.app_gateway_strategy}")
print(f"POS Gateway Strategy: {fs.pos_gateway_strategy}")
print(f"\nhas_stripe: {fs.has_stripe}")
print(f"has_redsys: {fs.has_redsys}")

# Simular la lógica de la vista
gateway_strategy = fs.app_gateway_strategy
show_stripe = False
show_redsys = False
show_choice = False

if gateway_strategy == 'STRIPE_ONLY':
    show_stripe = fs.has_stripe
elif gateway_strategy == 'REDSYS_ONLY':
    show_redsys = fs.has_redsys
elif gateway_strategy == 'STRIPE_PRIMARY':
    show_stripe = fs.has_stripe
    show_redsys = fs.has_redsys and not fs.has_stripe
elif gateway_strategy == 'REDSYS_PRIMARY':
    show_redsys = fs.has_redsys
    show_stripe = fs.has_stripe and not fs.has_redsys
elif gateway_strategy == 'CLIENT_CHOICE':
    show_stripe = fs.has_stripe
    show_redsys = fs.has_redsys
    show_choice = True

print(f"\n=== Vista mostrará ===")
print(f"show_stripe: {show_stripe}")
print(f"show_redsys: {show_redsys}")
print(f"show_choice: {show_choice}")
