import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from marketing.models import Popup

popups = Popup.objects.all()
print(f"Total popups: {popups.count()}\n")

for p in popups:
    print(f"ID: {p.id}")
    print(f"Título: {p.title}")
    print(f"Contenido: {repr(p.content)}")
    
    # Si contiene el texto problemático, actualizar
    if "POPUP.GET_TARGET_GROUP_DISPLAY" in p.content:
        print("⚠️  CONTIENE TEXTO PROBLEMÁTICO - ELIMINANDO")
        p.delete()
    
    print("-" * 60)
    print()

print("\n✅ Limpieza completada")
