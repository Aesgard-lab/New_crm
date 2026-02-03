#!/usr/bin/env python
"""Script para verificar y configurar completamente los usuarios superadmin"""
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
from organizations.models import Gym
from accounts.models_memberships import GymMembership

User = get_user_model()

print("\n=== DIAGNÓSTICO Y REPARACIÓN DE USUARIOS ===\n")

# Listar gimnasios disponibles
gyms = Gym.objects.all()
print(f"Gimnasios en el sistema: {gyms.count()}")
for gym in gyms:
    print(f"  - {gym.name} (ID: {gym.id})")
print()

# Verificar usuarios superadmin
superusers = User.objects.filter(is_superuser=True)
print(f"Superusuarios encontrados: {superusers.count()}\n")

for user in superusers:
    print(f"Usuario: {user.email}")
    print(f"  - is_active: {user.is_active}")
    print(f"  - is_staff: {user.is_staff}")
    print(f"  - is_superuser: {user.is_superuser}")
    
    # Verificar si tiene perfil de cliente
    has_client_profile = hasattr(user, 'client_profile')
    print(f"  - tiene client_profile: {has_client_profile}")
    
    # Verificar membresías de gimnasio
    gym_memberships = GymMembership.objects.filter(user=user)
    print(f"  - membresías de gym: {gym_memberships.count()}")
    
    for membership in gym_memberships:
        print(f"    • {membership.gym.name} - Rol: {membership.role}")
    
    # Si no tiene membresías y hay gimnasios, asignar al primero
    if gym_memberships.count() == 0 and gyms.exists():
        first_gym = gyms.first()
        GymMembership.objects.create(
            user=user,
            gym=first_gym,
            role='admin'
        )
        print(f"  ✓ Asignado al gimnasio: {first_gym.name} como admin")
    
    # Asegurar que el usuario esté correctamente configurado
    if not user.is_active:
        user.is_active = True
        user.save()
        print(f"  ✓ Activado")
    
    if not user.is_staff:
        user.is_staff = True
        user.save()
        print(f"  ✓ is_staff activado")
    
    print()

print("\n=== RESUMEN DE CREDENCIALES ===\n")

# Resetear contraseñas para asegurar que funcionen
for email in ['santiagoexplo@hotmail.com', 'admin@admin.com']:
    try:
        user = User.objects.get(email=email)
        user.set_password('admin123')
        user.save()
        print(f"✓ {email}")
        print(f"  Contraseña: admin123")
    except User.DoesNotExist:
        print(f"✗ {email} - No encontrado")

print(f"\nURL de login: http://127.0.0.1:8000/login/")
print("================================\n")
