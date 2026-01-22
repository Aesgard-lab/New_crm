#!/usr/bin/env python
"""
Script para corregir los tests:
1. Eliminar username de User.objects.create_user()
2. Cambiar enabled=False por enabled=True en ReviewSettings
"""

import re
from pathlib import Path

test_file = Path("activities/tests_reviews.py")

print("🔧 Leyendo archivo de tests...")
content = test_file.read_text(encoding='utf-8')

print("🔄 Paso 1: Eliminando username de User.objects.create_user()...")

# Pattern 1: username con email y password en líneas separadas
pattern1 = r'User\.objects\.create_user\(\s*username="[^"]+",\s*email="([^"]+)",\s*password="([^"]+)"'
replacement1 = r'User.objects.create_user(\n            email="\1",\n            password="\2"'
content = re.sub(pattern1, replacement1, content)

# Pattern 2: username con email, password e is_staff en líneas separadas  
pattern2 = r'User\.objects\.create_user\(\s*username="[^"]+",\s*email="([^"]+)",\s*password="([^"]+)",\s*is_staff=([TrueFalse]+)'
replacement2 = r'User.objects.create_user(\n            email="\1",\n            password="\2",\n            is_staff=\3'
content = re.sub(pattern2, replacement2, content)

print("🔄 Paso 2: Cambiando enabled=False por enabled=True en ReviewSettings...")
# Cambiar el default de enabled a True en los tests
content = content.replace(
    'settings = ReviewSettings.objects.create(gym=self.gym)',
    'settings = ReviewSettings.objects.create(gym=self.gym, enabled=True)'
)

print("💾 Guardando cambios...")
test_file.write_text(content, encoding='utf-8')

print("✅ Archivo corregido exitosamente!")
print("   - Eliminado parámetro 'username' de User.objects.create_user()")
print("   - Cambiado enabled=False a enabled=True en ReviewSettings")
