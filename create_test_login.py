"""
Create a test user for easy login
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from clients.models import Client
from organizations.models import Gym

User = get_user_model()

# Get first gym
gym = Gym.objects.first()

if not gym:
    print("❌ No hay gimnasios en la base de datos")
    exit(1)

# Check if demo user exists
email = "demo@test.com"
password = "demo1234"

try:
    user = User.objects.get(email=email)
    print(f"✅ Usuario ya existe: {email}")
    # Reset password
    user.set_password(password)
    user.save()
    print(f"✅ Contraseña reseteada")
except User.DoesNotExist:
    # Create user
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name="Demo",
        last_name="User"
    )
    print(f"✅ Usuario creado: {email}")

# Check if client profile exists
try:
    client = Client.objects.get(user=user)
    print(f"✅ Perfil de cliente ya existe")
except Client.DoesNotExist:
    # Create client profile
    client = Client.objects.create(
        user=user,
        gym=gym,
        first_name="Demo",
        last_name="User",
        email=email,
        phone_number="123456789",
        access_code=f"DEMO{user.id:04d}"
    )
    print(f"✅ Perfil de cliente creado")

print("\n" + "="*50)
print("CREDENCIALES PARA LOGIN:")
print("="*50)
print(f"Email:    {email}")
print(f"Password: {password}")
print(f"Gimnasio: {gym.name}")
print("="*50)
