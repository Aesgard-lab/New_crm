import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from organizations.models import Gym
from clients.models import Client

# Buscar el gimnasio y cliente
gym = Gym.objects.get(slug='qombo-arganzuela')
client = Client.objects.filter(gym=gym).first()

print(f"Gimnasio: {gym.name}")
print(f"Cliente: {client.first_name if client else 'No encontrado'}")

# Verificar FinanceSettings
finance_settings = getattr(gym, 'finance_settings', None)
if finance_settings:
    print(f"\n=== FinanceSettings ===")
    print(f"has_stripe: {finance_settings.has_stripe}")
    print(f"stripe_public_key: {finance_settings.stripe_public_key[:20]}..." if finance_settings.stripe_public_key else "None")
    print(f"stripe_secret_key: {'✓ Configurada' if finance_settings.stripe_secret_key else '✗ No configurada'}")
    print(f"app_gateway_strategy: {finance_settings.app_gateway_strategy}")
    
    # Intentar crear SetupIntent
    if client and finance_settings.has_stripe:
        try:
            from finance.stripe_utils import create_setup_intent
            client_secret = create_setup_intent(client)
            print(f"\n✓ SetupIntent creado correctamente")
            print(f"client_secret: {client_secret[:30]}...")
        except Exception as e:
            print(f"\n✗ Error creando SetupIntent: {e}")
else:
    print("✗ No hay FinanceSettings configurado")
