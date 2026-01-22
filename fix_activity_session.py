#!/usr/bin/env python
"""
Script para corregir ActivitySession.objects.create():
- Cambiar 'instructor' por 'staff'
- Cambiar 'start_time' por 'start_datetime'
- Agregar 'end_datetime'
"""

import re
from pathlib import Path
from datetime import timedelta

test_file = Path("activities/tests_reviews.py")

print("🔧 Leyendo archivo de tests...")
content = test_file.read_text(encoding='utf-8')

print("🔄 Paso 1: Cambiando 'instructor=' por 'staff='...")
content = content.replace('instructor=self.instructor', 'staff=self.instructor')

print("🔄 Paso 2: Cambiando 'start_time=' por 'start_datetime=' y agregando end_datetime...")

# Patrón para ActivitySession.objects.create con start_time
pattern = r'ActivitySession\.objects\.create\(\s*gym=self\.gym,\s*activity=self\.activity,\s*staff=([^,]+),\s*start_time=([^,\)]+)'
replacement = r'ActivitySession.objects.create(\n            gym=self.gym,\n            activity=self.activity,\n            staff=\1,\n            start_datetime=\2,\n            end_datetime=\2 + timedelta(hours=1)'

content = re.sub(pattern, replacement, content)

# Agregar import de timedelta si no está
if 'from datetime import' not in content:
    # Agregar después de la línea de unittest.mock import
    content = content.replace(
        'from unittest.mock import patch',
        'from unittest.mock import patch\nfrom datetime import timedelta'
    )

print("💾 Guardando cambios...")
test_file.write_text(content, encoding='utf-8')

print("✅ Archivo corregido exitosamente!")
print("   - Cambiado 'instructor' por 'staff'")
print("   - Cambiado 'start_time' por 'start_datetime'")
print("   - Agregado 'end_datetime'")
print("   - Agregado import de timedelta")
