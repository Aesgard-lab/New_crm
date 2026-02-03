#!/usr/bin/env python
"""Script para listar todos los usuarios superadmin"""
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

print("\n=== USUARIOS EN EL SISTEMA ===\n")

# Listar todos los superusuarios
superusers = User.objects.filter(is_superuser=True)
if superusers.exists():
    print("Superusuarios:")
    for user in superusers:
        print(f"  - Email: {user.email}")
        print(f"    Nombre: {user.get_full_name()}")
        print(f"    Activo: {user.is_active}")
        print(f"    Staff: {user.is_staff}")
        print(f"    Creado: {user.created_at}")
        print()
else:
    print("No hay superusuarios en el sistema.")

# Listar todos los usuarios staff
print("\nUsuarios Staff:")
staff_users = User.objects.filter(is_staff=True, is_superuser=False)
if staff_users.exists():
    for user in staff_users:
        print(f"  - Email: {user.email}")
        print(f"    Nombre: {user.get_full_name()}")
        print()
else:
    print("No hay usuarios staff (no superadmin).")

# Total de usuarios
total_users = User.objects.count()
print(f"\nTotal de usuarios en el sistema: {total_users}")
print("\nURL de login: http://127.0.0.1:8000/login/")
print("==============================\n")
