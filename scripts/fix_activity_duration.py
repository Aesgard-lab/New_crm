#!/usr/bin/env python
"""
Script para corregir duration_minutes a duration en Activity.objects.create()
"""

import re
from pathlib import Path

test_file = Path("activities/tests_reviews.py")

print("🔧 Leyendo archivo de tests...")
content = test_file.read_text(encoding='utf-8')

print("🔄 Cambiando duration_minutes por duration...")
content = content.replace('duration_minutes=', 'duration=')

print("💾 Guardando cambios...")
test_file.write_text(content, encoding='utf-8')

print("✅ Archivo corregido exitosamente!")
print("   - Cambiado 'duration_minutes' por 'duration' en Activity.objects.create()")
