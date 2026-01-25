"""
Configuración de Django - Selector automático de entorno.

El entorno se determina por la variable DJANGO_SETTINGS_MODULE:
    - config.settings.local      -> Desarrollo
    - config.settings.staging    -> Pre-producción  
    - config.settings.production -> Producción

Si no se especifica, se usa 'local' por defecto para seguridad
(mejor fallar en desarrollo que exponer datos en producción).
"""

import os

# Por defecto usar local para seguridad
environment = os.getenv('DJANGO_ENV', 'local')

if environment == 'production':
    from .production import *
elif environment == 'staging':
    from .staging import *
else:
    from .local import *
