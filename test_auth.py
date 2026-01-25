#!/usr/bin/env python
"""Script para probar la autenticación directamente"""
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

from django.contrib.auth import authenticate, get_user_model
from accounts.models_memberships import GymMembership

User = get_user_model()

print("\n=== PRUEBA DE AUTENTICACIÓN ===\n")

# Credenciales a probar
test_emails = ['santiagoexplo@hotmail.com', 'admin@admin.com']
test_password = 'admin123'

for email in test_emails:
    print(f"\n--- Probando: {email} ---")
    
    # 1. Verificar que el usuario existe
    try:
        user = User.objects.get(email=email)
        print(f"✓ Usuario encontrado en DB")
        print(f"  - ID: {user.id}")
        print(f"  - Email: {user.email}")
        print(f"  - is_active: {user.is_active}")
        print(f"  - is_staff: {user.is_staff}")
        print(f"  - is_superuser: {user.is_superuser}")
        print(f"  - has_usable_password: {user.has_usable_password()}")
        
        # 2. Verificar membresías
        memberships = GymMembership.objects.filter(user=user)
        print(f"  - Membresías de gym: {memberships.count()}")
        for m in memberships:
            print(f"    • {m.gym.name} ({m.role})")
        
        # 3. Probar autenticación
        print(f"\n  Probando authenticate()...")
        auth_user = authenticate(username=email, password=test_password)
        
        if auth_user:
            print(f"  ✓ AUTENTICACIÓN EXITOSA")
            print(f"    Usuario autenticado: {auth_user.email}")
        else:
            print(f"  ✗ AUTENTICACIÓN FALLIDA")
            
            # Intentar verificar la contraseña manualmente
            print(f"\n  Verificando contraseña manualmente...")
            if user.check_password(test_password):
                print(f"  ✓ La contraseña ES CORRECTA (check_password)")
                print(f"  ⚠ Pero authenticate() falló - puede ser un problema con el backend")
            else:
                print(f"  ✗ La contraseña NO ES CORRECTA")
                # Intentar resetear
                print(f"\n  Reseteando contraseña...")
                user.set_password(test_password)
                user.save()
                print(f"  ✓ Contraseña reseteada")
                
                # Probar de nuevo
                auth_user = authenticate(username=email, password=test_password)
                if auth_user:
                    print(f"  ✓ AUTENTICACIÓN EXITOSA después de reseteo")
                else:
                    print(f"  ✗ AUTENTICACIÓN AÚN FALLA después de reseteo")
        
    except User.DoesNotExist:
        print(f"✗ Usuario NO encontrado en DB")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

# Verificar configuración de autenticación
print("\n\n=== CONFIGURACIÓN DE AUTENTICACIÓN ===")
from django.conf import settings

print(f"AUTH_USER_MODEL: {settings.AUTH_USER_MODEL}")
print(f"AUTHENTICATION_BACKENDS: {settings.AUTHENTICATION_BACKENDS}")

print("\n=== FIN DEL DIAGNÓSTICO ===\n")
