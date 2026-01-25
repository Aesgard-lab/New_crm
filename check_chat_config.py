import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from organizations.models import Gym

# Verificar el gimnasio
gym = Gym.objects.get(slug='qombo-arganzuela')
print(f"Gimnasio: {gym.name}")
print(f"\n=== Configuración de Chat ===")

# Verificar si existe módulo de chat
from django.conf import settings
installed_apps = settings.INSTALLED_APPS
print(f"Chat instalado: {'chat' in [app.split('.')[-1] for app in installed_apps]}")

# Verificar URLs de chat en public_portal
try:
    from django.urls import reverse
    # Intentar buscar URL de chat
    try:
        chat_url = reverse('public_chat', kwargs={'slug': gym.slug})
        print(f"URL de chat encontrada: {chat_url}")
    except:
        print("❌ No existe URL 'public_chat' en el portal público")
        
    # Listar todas las URLs públicas disponibles
    from django.urls import get_resolver
    resolver = get_resolver()
    public_patterns = [p.name for p in resolver.url_patterns if p.name and p.name.startswith('public_')]
    print(f"\n=== URLs públicas disponibles ===")
    for pattern in sorted(public_patterns):
        print(f"  - {pattern}")
except Exception as e:
    print(f"Error al verificar URLs: {e}")
