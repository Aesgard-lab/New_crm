import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from clients.models import Client
from organizations.models import Gym

User = get_user_model()

# Datos del cliente demo
EMAIL = 'demo.cliente@mygym.com'
PASSWORD = 'Demo1234!'

try:
    # Obtener el primer gym
    gym = Gym.objects.first()
    print(f'Gym encontrado: {gym}')
    
    # Eliminar usuario existente si hay
    try:
        existing = User.objects.get(email=EMAIL)
        existing.delete()
        print('Usuario anterior eliminado')
    except User.DoesNotExist:
        pass
    
    # Crear usuario usando el manager que espera email
    user = User.objects.create_user(
        email=EMAIL,
        password=PASSWORD,
        first_name='Demo',
        last_name='Cliente'
    )
    print(f'Usuario creado: {user}')
    
    # Crear cliente
    client = Client.objects.create(
        gym=gym,
        user=user,
        first_name='Demo',
        last_name='Cliente',
        email=EMAIL,
        phone_number='+34 600 123 456',
        status='ACTIVE',
        access_code='1234'
    )
    print(f'Cliente creado: {client}')
    
    print('')
    print('='*50)
    print('CREDENCIALES PARA EL MEMBER PORTAL')
    print('='*50)
    print(f'URL:      http://localhost:8000/app/login/')
    print(f'Email:    {EMAIL}')
    print(f'Password: {PASSWORD}')
    print('='*50)
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
