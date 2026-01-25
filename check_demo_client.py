#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from accounts.models import User
from django.contrib.auth import authenticate

email = "demo.cliente@mygym.com"
password = "demo123"

try:
    user = User.objects.get(email=email)
    print(f"✓ Usuario encontrado: {user.email}")
    print(f"  - ID: {user.id}")
    print(f"  - is_active: {user.is_active}")
    print(f"  - is_staff: {user.is_staff}")
    print(f"  - is_superuser: {user.is_superuser}")
    print(f"  - has_usable_password: {user.has_usable_password()}")
    
    # Intentar autenticar
    auth_user = authenticate(username=email, password=password)
    if auth_user:
        print(f"✓ AUTENTICACIÓN EXITOSA")
    else:
        print(f"✗ AUTENTICACIÓN FALLIDA")
        # Intentar resetear password
        user.set_password(password)
        user.save()
        print(f"✓ Password reseteado a: {password}")
        
        # Verificar de nuevo
        auth_user = authenticate(username=email, password=password)
        if auth_user:
            print(f"✓ AUTENTICACIÓN EXITOSA después de resetear")
        else:
            print(f"✗ AÚN FALLA después de resetear")
    
except User.DoesNotExist:
    print(f"✗ Usuario NO encontrado: {email}")
    print(f"Creando usuario demo...")
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name="Demo",
        last_name="Cliente",
        is_active=True,
        is_staff=False,
        is_superuser=False
    )
    print(f"✓ Usuario creado: {user.email}")
    
    # Verificar autenticación
    auth_user = authenticate(username=email, password=password)
    if auth_user:
        print(f"✓ AUTENTICACIÓN EXITOSA")
    else:
        print(f"✗ AUTENTICACIÓN FALLIDA")
