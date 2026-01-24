"""Script para crear un cliente demo para la app móvil."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from clients.models import Client
from organizations.models import Gym

User = get_user_model()

# Buscar un gimnasio Qombo
gym = Gym.objects.filter(name__icontains='qombo').first()
if not gym:
    gym = Gym.objects.first()

print(f"Usando gimnasio: {gym.name} (ID: {gym.id})")

# Crear o actualizar usuario
email = 'demo@qombo.com'
password = 'demo123'

user, created = User.objects.get_or_create(
    email=email,
    defaults={
        'first_name': 'Demo',
        'last_name': 'Cliente'
    }
)
user.set_password(password)
user.save()
print(f"Usuario {'creado' if created else 'actualizado'}: {user.email}")

# Crear o actualizar cliente
client, cc = Client.objects.get_or_create(
    user=user,
    defaults={
        'gym': gym,
        'first_name': 'Demo',
        'last_name': 'Cliente',
        'email': email
    }
)

if not cc:
    client.gym = gym
    client.save()
    
print(f"Cliente {'creado' if cc else 'actualizado'}: {client.first_name} {client.last_name}")
print(f"\n✅ Credenciales de prueba:")
print(f"   Email: {email}")
print(f"   Password: {password}")
print(f"   Gimnasio: {gym.name}")
