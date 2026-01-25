#!/usr/bin/env python
"""Script para limpiar el rate limit y preparar para login"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f'Error al inicializar Django: {e}')
    sys.exit(1)

from django.core.cache import cache
from django.contrib.auth import get_user_model
from accounts.models_memberships import GymMembership
from organizations.models import Gym

User = get_user_model()

print("\n=== LIMPIEZA Y PREPARACIÓN PARA LOGIN ===\n")

# 1. Limpiar cache de rate limit
print("1. Limpiando rate limits...")
try:
    cache.clear()
    print("   ✓ Cache limpiado (rate limits reseteados)")
except Exception as e:
    print(f"   ⚠ Error al limpiar cache: {e}")

# 2. Verificar y configurar usuarios
print("\n2. Verificando configuración de usuarios...")

for email in ['santiagoexplo@hotmail.com', 'admin@admin.com']:
    try:
        user = User.objects.get(email=email)
        
        # Asegurar que todo está correcto
        changed = False
        if not user.is_active:
            user.is_active = True
            changed = True
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True
        
        # Resetear contraseña
        user.set_password('admin123')
        changed = True
        
        if changed:
            user.save()
        
        # Verificar membresías
        memberships = GymMembership.objects.filter(user=user)
        if memberships.count() == 0:
            gym = Gym.objects.first()
            if gym:
                GymMembership.objects.create(
                    user=user,
                    gym=gym,
                    role='admin'
                )
                print(f"   ✓ {email} - Membresía asignada a {gym.name}")
        else:
            print(f"   ✓ {email} - Todo configurado correctamente")
            
    except User.DoesNotExist:
        print(f"   ✗ {email} - Usuario no encontrado")

# 3. Información de configuración
print("\n3. Configuración del servidor:")
from django.conf import settings
print(f"   - DEBUG: {settings.DEBUG}")
print(f"   - ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")

# 4. Verificar que el servidor esté corriendo
print("\n4. Estado del servidor:")
print("   - Si el servidor NO está corriendo, ejecuta:")
print("     python manage.py runserver")

print("\n=== LISTO PARA LOGIN ===\n")
print("Credenciales válidas:\n")
print("Opción 1:")
print("  Email: santiagoexplo@hotmail.com")
print("  Contraseña: admin123\n")
print("Opción 2:")
print("  Email: admin@admin.com")
print("  Contraseña: admin123\n")
print("URL: http://127.0.0.1:8000/login/")
print("\nNOTA: Si sigue sin funcionar, por favor indica:")
print("  - ¿Qué mensaje de error ves en la pantalla?")
print("  - ¿Te redirige a algún lugar?")
print("  - ¿Aparece 'Credenciales incorrectas'?")
print("  - ¿O simplemente recarga la página de login?")
print("==================================\n")
