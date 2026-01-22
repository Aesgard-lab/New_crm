import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from marketing.models import Popup

# Buscar popups con el texto problemático
problematic = Popup.objects.filter(content__icontains='POPUP.GET_TARGET_GROUP_DISPLAY')

print(f"Popups encontrados con texto problemático: {problematic.count()}\n")

for popup in problematic:
    print(f"ID: {popup.id}")
    print(f"Título: {popup.title}")
    print(f"Contenido:\n{popup.content}\n")
    print("-" * 50)

if problematic.count() > 0:
    confirm = input("\n¿Eliminar estos popups? (s/n): ")
    if confirm.lower() == 's':
        count = problematic.count()
        problematic.delete()
        print(f"\n✅ Eliminados {count} popups")
    else:
        print("\n❌ Cancelado")
else:
    print("No se encontraron popups con ese contenido")
