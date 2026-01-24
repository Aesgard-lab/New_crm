#!/usr/bin/env python
"""
Script final para corregir todos los tests:
1. Agregar gym=self.gym a ClassReview.objects.create()
2. Agregar gym=self.gym a ReviewRequest.objects.create()
3. Corregir ClientVisit.objects.create() para usar campos correctos
"""

import re
from pathlib import Path

test_file = Path("activities/tests_reviews.py")

print("🔧 Leyendo archivo de tests...")
content = test_file.read_text(encoding='utf-8')

print("🔄 Paso 1: Agregando gym=self.gym a ClassReview.objects.create()...")
# Buscar ClassReview.objects.create( sin gym y agregar gym
pattern1 = r'ClassReview\.objects\.create\(\s*session=self\.session,'
replacement1 = r'ClassReview.objects.create(\n            gym=self.gym,\n            session=self.session,'
content = re.sub(pattern1, replacement1, content)

print("🔄 Paso 2: Agregando gym=self.gym a ReviewRequest.objects.create()...")
# Buscar ReviewRequest.objects.create( sin gym y agregar gym
pattern2 = r'ReviewRequest\.objects\.create\(\s*session=self\.session,'
replacement2 = r'ReviewRequest.objects.create(\n            gym=self.gym,\n            session=self.session,'
content = re.sub(pattern2, replacement2, content)

print("🔄 Paso 3: Corrigiendo ClientVisit.objects.create()...")
# ClientVisit no tiene 'session', necesita: client, date, staff, concept
# Reemplazar:
# ClientVisit.objects.create(
#     session=self.session,
#     client=self.client_model,
#     status='BOOKED'
# )
# Por:
# ClientVisit.objects.create(
#     client=self.client_model,
#     staff=self.instructor,
#     date=timezone.now().date(),
#     concept=self.activity.name,
#     status='ATTENDED'
# )

pattern3 = r'ClientVisit\.objects\.create\(\s*session=self\.session,\s*client=self\.client_model,\s*status=[\'"]BOOKED[\'"]\s*\)'
replacement3 = '''ClientVisit.objects.create(
            client=self.client_model,
            staff=self.instructor,
            date=timezone.now().date(),
            concept=self.activity.name,
            status='ATTENDED'
        )'''
content = re.sub(pattern3, replacement3, content, flags=re.DOTALL)

# También cambiar status='BOOKED' por status='ATTENDED' donde esté solo
content = content.replace("status='BOOKED'", "status='ATTENDED'")

print("💾 Guardando cambios...")
test_file.write_text(content, encoding='utf-8')

print("✅ Archivo corregido exitosamente!")
print("   - Agregado gym=self.gym a ClassReview.objects.create()")
print("   - Agregado gym=self.gym a ReviewRequest.objects.create()")
print("   - Corregido ClientVisit.objects.create() con campos correctos")
