#!/usr/bin/env python
"""
Script para corregir timezone.now( mal formateado
"""

import re
from pathlib import Path

test_file = Path("activities/tests_reviews.py")

print("🔧 Leyendo archivo de tests...")
content = test_file.read_text(encoding='utf-8')

print("🔄 Corrigiendo timezone.now( mal formateado...")

# Corregir timezone.now( sin cerrar
content = content.replace('start_datetime=timezone.now(,', 'start_datetime=timezone.now(),')
content = content.replace('end_datetime=timezone.now( + timedelta(hours=1)', 'end_datetime=timezone.now() + timedelta(hours=1)')

print("💾 Guardando cambios...")
test_file.write_text(content, encoding='utf-8')

print("✅ Archivo corregido exitosamente!")
