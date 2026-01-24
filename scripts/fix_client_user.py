"""
Script para asegurar que el cliente demo NO sea staff
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from clients.models import Client

User = get_user_model()

print("=" * 60)
print("🔧 CORRIGIENDO USUARIO DEL CLIENTE")
print("=" * 60)

try:
    client = Client.objects.get(email='demo.cliente@mygym.com')
    user = client.user
    
    print(f"\n📊 Estado actual:")
    print(f"   Email: {user.email}")
    print(f"   is_staff: {user.is_staff}")
    print(f"   is_superuser: {user.is_superuser}")
    
    # Quitar privilegios de staff
    user.is_staff = False
    user.is_superuser = False
    user.set_password('demo123')
    user.save()
    
    print(f"\n✅ Usuario corregido:")
    print(f"   is_staff: {user.is_staff}")
    print(f"   is_superuser: {user.is_superuser}")
    print(f"   Contraseña: demo123")
    
    print("\n" + "=" * 60)
    print("🌐 ACCESO AL PORTAL DEL CLIENTE")
    print("=" * 60)
    print(f"\n   1. Haz logout del backoffice en: http://127.0.0.1:8000/logout/")
    print(f"   2. Ve a: http://127.0.0.1:8000/portal/login/")
    print(f"   3. Login con:")
    print(f"      Email: demo.cliente@mygym.com")
    print(f"      Contraseña: demo123")
    print("\n" + "=" * 60)
    
except Client.DoesNotExist:
    print("❌ Cliente no encontrado")
