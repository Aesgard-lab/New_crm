#!/usr/bin/env python
"""Script para crear o resetear el superusuario"""
import os
import sys
import django

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f'Error al inicializar Django: {e}')
    sys.exit(1)

from django.contrib.auth import get_user_model

User = get_user_model()

# Credenciales del superusuario
email = 'admin@admin.com'
password = 'admin123'
first_name = 'Admin'
last_name = 'User'

try:
    # Verificar si el usuario ya existe
    if User.objects.filter(email=email).exists():
        user = User.objects.get(email=email)
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        print(f'✓ Contraseña reseteada para el superusuario: {email}')
    else:
        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        print(f'✓ Superusuario creado: {email}')

    print(f'\n=== Credenciales ===')
    print(f'Email: {email}')
    print(f'Contraseña: {password}')
    print(f'====================\n')
    print('Puedes acceder en: http://127.0.0.1:8000/accounts/login/')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
