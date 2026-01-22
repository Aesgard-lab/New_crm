#!/usr/bin/env python
"""
Script para agregar base_capacity=20 a Activity.objects.create()
"""

import re
from pathlib import Path

test_file = Path("activities/tests_reviews.py")

print("🔧 Leyendo archivo de tests...")
content = test_file.read_text(encoding='utf-8')

print("🔄 Agregando base_capacity a Activity.objects.create()...")

# Agregar base_capacity en Activity.objects.create()
# Buscar patrones como: gym=self.gym,\n        name="...",\n        duration=60
pattern = r'(Activity\.objects\.create\(\s*gym=self\.gym,\s*name="[^"]+",\s*duration=60)'
replacement = r'\1,\n            base_capacity=20'
content = re.sub(pattern, replacement, content)

print("💾 Guardando cambios...")
test_file.write_text(content, encoding='utf-8')

print("✅ Archivo corregido exitosamente!")
print("   - Agregado 'base_capacity=20' en Activity.objects.create()")
