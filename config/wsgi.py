"""
WSGI config for CRM project.

Expone el callable WSGI como variable 'application'.

El entorno se selecciona según DJANGO_ENV:
    - local: Desarrollo
    - staging: Pre-producción
    - production: Producción

Para producción con Gunicorn:
    gunicorn config.wsgi:application

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
