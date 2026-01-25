"""
ASGI config for CRM project.

Expone el callable ASGI como variable 'application'.

El entorno se selecciona según DJANGO_ENV:
    - local: Desarrollo
    - staging: Pre-producción
    - production: Producción

Para producción con uvicorn:
    uvicorn config.asgi:application

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
