import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from organizations.models import Gym

gym = Gym.objects.get(slug='qombo-arganzuela')
fs = gym.finance_settings

print(f"Gimnasio: {gym.name}")
print(f"\nEstado ANTES:")
print(f"app_gateway_strategy: {fs.app_gateway_strategy}")

# Cambiar a CLIENT_CHOICE para que el usuario pueda elegir
fs.app_gateway_strategy = 'CLIENT_CHOICE'
fs.save()

print(f"\nEstado DESPUÉS:")
print(f"app_gateway_strategy: {fs.app_gateway_strategy}")
print(f"\n✓ Ahora el cliente puede elegir entre Stripe y Redsys")
