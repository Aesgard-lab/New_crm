import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from django.urls import get_resolver
from config.urls import urlpatterns

print("="*60)
print("PATRONES EN config.urls.urlpatterns:")
print("="*60)
for i, pattern in enumerate(urlpatterns):
    print(f"{i:2d}: {pattern.pattern}")

print("\n" + "="*60)
print("PATRONES EN EL RESOLVER:")
print("="*60)
resolver = get_resolver()
for i, pattern in enumerate(resolver.url_patterns):
    print(f"{i:2d}: {pattern.pattern}")

print("\n" + "="*60)
print(f"Total en urlpatterns: {len(urlpatterns)}")
print(f"Total en resolver: {len(resolver.url_patterns)}")
print("="*60)

# Verificar módulos de public_portal
print("\n" + "="*60)
print("VERIFICANDO MÓDULOS:")
print("="*60)
try:
    import public_portal.urls
    print(f"✓ public_portal.urls - {len(public_portal.urls.urlpatterns)} patrones")
except Exception as e:
    print(f"✗ public_portal.urls - ERROR: {e}")

try:
    import public_portal.embed_urls
    print(f"✓ public_portal.embed_urls - {len(public_portal.embed_urls.urlpatterns)} patrones")
except Exception as e:
    print(f"✗ public_portal.embed_urls - ERROR: {e}")
