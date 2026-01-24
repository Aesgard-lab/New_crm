import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from finance.models import PaymentMethod
from organizations.models import Gym

# Get first gym (or create one if dev env is empty, but likely exists)
gym = Gym.objects.first()
if gym:
    if not PaymentMethod.objects.filter(gym=gym).exists():
        PaymentMethod.objects.create(gym=gym, name='Efectivo', is_cash=True)
        PaymentMethod.objects.create(gym=gym, name='Tarjeta', is_cash=False)
        print("Created default Payment Methods: Efectivo, Tarjeta")
    else:
        print("Payment Methods already exist.")
else:
    print("No Gym found.")
