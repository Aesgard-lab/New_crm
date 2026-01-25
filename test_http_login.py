#!/usr/bin/env python
"""Script para hacer un login de prueba y ver qué está pasando"""
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

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n=== SIMULANDO LOGIN HTTP ===\n")

# Usar el cliente de prueba de Django
client = Client()

# Intentar login
email = 'santiagoexplo@hotmail.com'
password = 'admin123'

print(f"1. Intentando login con:")
print(f"   Email: {email}")
print(f"   Contraseña: {password}\n")

# Hacer POST a /login/
response = client.post('/login/', {
    'email': email,
    'password': password
})

print(f"2. Respuesta del servidor:")
print(f"   Status Code: {response.status_code}")
print(f"   Redirect: {response.status_code in [301, 302, 303, 307, 308]}")

if response.status_code in [301, 302, 303, 307, 308]:
    print(f"   Redirect URL: {response.url}")
    print("\n✓ LOGIN EXITOSO - Redirigió correctamente")
else:
    print(f"   Content-Type: {response.get('Content-Type', 'N/A')}")
    print("\n✗ LOGIN FALLÓ - Devolvió la página de login")
    
    # Intentar extraer el mensaje de error del HTML
    content = response.content.decode('utf-8')
    if 'error' in content.lower():
        # Buscar el mensaje de error
        import re
        error_pattern = r'<div[^>]*bg-red[^>]*>(.*?)</div>'
        matches = re.findall(error_pattern, content, re.DOTALL)
        if matches:
            for match in matches:
                # Limpiar HTML tags
                clean_error = re.sub(r'<[^>]+>', '', match).strip()
                print(f"\n   Mensaje de error en HTML: {clean_error}")

# Verificar si el usuario existe y puede autenticarse
print("\n3. Verificación directa:")
from django.contrib.auth import authenticate

user = authenticate(username=email, password=password)
if user:
    print(f"   ✓ authenticate() funciona - Usuario: {user.email}")
else:
    print(f"   ✗ authenticate() falló")
    
    # Verificar el usuario manualmente
    try:
        user_obj = User.objects.get(email=email)
        print(f"\n   Usuario existe en DB:")
        print(f"   - is_active: {user_obj.is_active}")
        print(f"   - is_staff: {user_obj.is_staff}")
        print(f"   - check_password(): {user_obj.check_password(password)}")
    except User.DoesNotExist:
        print(f"\n   ✗ Usuario NO existe en DB")

# Probar con el otro usuario también
print("\n" + "="*50)
email2 = 'admin@admin.com'
print(f"\n4. Probando con: {email2}")

response2 = client.post('/login/', {
    'email': email2,
    'password': password
})

print(f"   Status Code: {response2.status_code}")
if response2.status_code in [301, 302, 303, 307, 308]:
    print(f"   ✓ LOGIN EXITOSO")
else:
    print(f"   ✗ LOGIN FALLÓ")

print("\n" + "="*50 + "\n")
