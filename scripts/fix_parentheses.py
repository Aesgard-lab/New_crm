#!/usr/bin/env python
"""
Script para eliminar paréntesis extra después de timedelta(hours=1))
"""

from pathlib import Path

test_file = Path("activities/tests_reviews.py")

print("🔧 Leyendo archivo de tests...")
content = test_file.read_text(encoding='utf-8')

print("🔄 Eliminando paréntesis extra...")
content = content.replace('timedelta(hours=1)),', 'timedelta(hours=1),')

print("💾 Guardando cambios...")
test_file.write_text(content, encoding='utf-8')

print("✅ Archivo corregido exitosamente!")
