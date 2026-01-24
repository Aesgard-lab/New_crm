"""
Script para configurar acceso al portal del cliente
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from clients.models import Client

User = get_user_model()

print("=" * 60)
print("🔐 CONFIGURANDO ACCESO AL PORTAL DEL CLIENTE")
print("=" * 60)

# Buscar cliente existente
client = Client.objects.filter(user__isnull=False).first()

if client:
    user = client.user
    print(f"\n✅ Cliente encontrado: {client.first_name} {client.last_name}")
    print(f"   Email: {client.email}")
    print(f"   Gym: {client.gym.name}")
    
    # Resetear contraseña a algo simple para pruebas
    nueva_password = "demo123"
    user.set_password(nueva_password)
    user.save()
    
    print(f"\n🔑 Contraseña actualizada a: {nueva_password}")
    print("\n" + "=" * 60)
    print("🌐 CREDENCIALES DE ACCESO AL PORTAL")
    print("=" * 60)
    print(f"\n   URL: http://127.0.0.1:8000/portal/login/")
    print(f"   Email: {client.email}")
    print(f"   Contraseña: {nueva_password}")
    print("\n" + "=" * 60)
    print("✅ ¡Ya puedes acceder al portal del cliente!")
    print("=" * 60)
else:
    print("\n❌ No se encontró ningún cliente con usuario")
    print("   Creando uno nuevo...")
    
    from organizations.models import Gym
    
    gym = Gym.objects.first()
    if not gym:
        print("❌ No hay gimnasios en la base de datos")
        exit()
    
    # Crear usuario
    user = User.objects.create_user(
        email='cliente@demo.com',
        password='demo123',
        first_name='Cliente',
        last_name='Demo'
    )
    
    # Crear cliente
    client = Client.objects.create(
        gym=gym,
        user=user,
        first_name='Cliente',
        last_name='Demo',
        email='cliente@demo.com',
        phone='600000000',
        status='active'
    )
    
    print(f"\n✅ Cliente creado: {client.first_name} {client.last_name}")
    print("\n" + "=" * 60)
    print("🌐 CREDENCIALES DE ACCESO AL PORTAL")
    print("=" * 60)
    print(f"\n   URL: http://127.0.0.1:8000/portal/login/")
    print(f"   Email: cliente@demo.com")
    print(f"   Contraseña: demo123")
    print("\n" + "=" * 60)
    print("✅ ¡Ya puedes acceder al portal del cliente!")
    print("=" * 60)
