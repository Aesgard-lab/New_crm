import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from marketing.models import Popup

# Buscar popups con contenido que contiene variables template mal formateadas
popups = Popup.objects.all()

print(f"Total popups: {popups.count()}\n")

for popup in popups:
    print(f"ID: {popup.id}")
    print(f"Título: {popup.title}")
    print(f"Audiencia: {popup.get_audience_type_display()}")
    print(f"Contenido actual:\n{popup.content}")
    
    # Si el contenido tiene texto estático, actualizarlo a dinámico
    if "Hola Juan" in popup.content:
        popup.content = '<p>Hola {{ client.first_name }}, gracias por unirte a {{ gym.name }}. ¡Disfruta de tus entrenamientos!</p>'
        popup.save()
        print("✓ ACTUALIZADO con variables dinámicas")
    
    print("-" * 50)
    print()

print("\n✅ Proceso completado")
