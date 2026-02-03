#!/usr/bin/env python
"""Script para verificar y corregir usuarios superadmin"""
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

from django.contrib.auth import get_user_model

User = get_user_model()

print("\n=== VERIFICANDO Y CORRIGIENDO USUARIOS ===\n")

# Corregir el usuario "verifier" que parece no tener email válido
try:
    verifier = User.objects.get(email="verifier")
    print(f"❌ Usuario encontrado con email inválido: {verifier.email}")
    print(f"   Este usuario tiene is_staff={verifier.is_staff} pero debería ser True para superuser")
    
    # Corregir
    verifier.is_staff = True
    verifier.save()
    print(f"✓ Usuario corregido: ahora is_staff=True")
except User.DoesNotExist:
    pass

# Resetear contraseña para santiagoexplo@hotmail.com
try:
    santiago = User.objects.get(email="santiagoexplo@hotmail.com")
    santiago.set_password("admin123")
    santiago.is_staff = True
    santiago.is_superuser = True
    santiago.is_active = True
    santiago.save()
    print(f"\n✓ Contraseña reseteada para: santiagoexplo@hotmail.com")
    print(f"  Nueva contraseña: admin123")
except User.DoesNotExist:
    pass

print("\n=== CREDENCIALES DISPONIBLES ===\n")
print("Opción 1:")
print("  Email: santiagoexplo@hotmail.com")
print("  Contraseña: admin123")
print()
print("Opción 2:")
print("  Email: admin@admin.com")
print("  Contraseña: admin123")
print()
print("URL de login: http://127.0.0.1:8000/login/")
print("===============================\n")
