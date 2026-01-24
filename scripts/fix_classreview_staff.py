#!/usr/bin/env python
"""
Script para agregar staff=self.instructor a ClassReview.objects.create()
"""

import re
from pathlib import Path

test_file = Path("activities/tests_reviews.py")

print("🔧 Leyendo archivo de tests...")
content = test_file.read_text(encoding='utf-8')

print("🔄 Agregando staff a ClassReview.objects.create()...")

# Patrón: ClassReview.objects.create( con gym y session pero sin staff
pattern = r'ClassReview\.objects\.create\(\s*gym=self\.gym,\s*session=self\.session,\s*client='
replacement = r'ClassReview.objects.create(\n            gym=self.gym,\n            session=self.session,\n            staff=self.instructor,\n            client='

content = re.sub(pattern, replacement, content)

print("💾 Guardando cambios...")
test_file.write_text(content, encoding='utf-8')

print("✅ Corregido staff en ClassReview!")
