"""
Configuración de desarrollo local.

Para usar este archivo:
    export DJANGO_SETTINGS_MODULE=config.settings.local
    
O en manage.py:
    python manage.py runserver --settings=config.settings.local
"""

from .base import *

# --------------------------------------------------
# DEBUG MODE
# --------------------------------------------------
DEBUG = True

# --------------------------------------------------
# ALLOWED HOSTS (desarrollo)
# --------------------------------------------------
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
    ".localhost",
]

# --------------------------------------------------
# INSTALLED APPS (extras de desarrollo)
# --------------------------------------------------
INSTALLED_APPS += [
    # Herramientas de debug (opcional)
    # "debug_toolbar",
    # "django_extensions",
]

# --------------------------------------------------
# MIDDLEWARE (extras de desarrollo)
# --------------------------------------------------
# Descomentar si usas Django Debug Toolbar
# MIDDLEWARE += [
#     "debug_toolbar.middleware.DebugToolbarMiddleware",
# ]

# IPs internas para Debug Toolbar
INTERNAL_IPS = [
    "127.0.0.1",
]

# --------------------------------------------------
# DATABASE (desarrollo - puede usar SQLite o PostgreSQL)
# --------------------------------------------------
# Usa PostgreSQL local por defecto, pero permite SQLite para desarrollo rápido
if os.getenv("USE_SQLITE", "False") == "True":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    # Usar la configuración de PostgreSQL de base.py
    DATABASES["default"]["PASSWORD"] = os.getenv("POSTGRES_PASSWORD", "123")

# --------------------------------------------------
# CACHING (desarrollo - memoria local)
# --------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

# --------------------------------------------------
# EMAIL (desarrollo - consola)
# --------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# --------------------------------------------------
# STATIC FILES (desarrollo)
# --------------------------------------------------
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# --------------------------------------------------
# SECURITY (relajada para desarrollo)
# --------------------------------------------------
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_AGE = 86400  # 24 horas en desarrollo

# --------------------------------------------------
# CORS (permisivo en desarrollo)
# --------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# --------------------------------------------------
# TEMPLATES (sin caché en desarrollo)
# --------------------------------------------------
# Ya configurado en base.py con APP_DIRS = True

# --------------------------------------------------
# LOGGING (reducido para desarrollo)
# --------------------------------------------------
LOGGING['handlers']['console']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'INFO'
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'WARNING',  # Cambiar a DEBUG para ver queries SQL
    'propagate': False,
}

# Logger para las apps del proyecto
for app in LOCAL_APPS:
    app_name = app.split('.')[0]  # Obtener el nombre base de la app
    LOGGING['loggers'][app_name] = {
        'handlers': ['console'],
        'level': 'INFO',
        'propagate': False,
    }

# --------------------------------------------------
# CELERY (desarrollo)
# --------------------------------------------------
# Ejecutar tareas de forma síncrona en desarrollo (más fácil de debuggear)
# Descomentar la siguiente línea si quieres tareas síncronas:
# CELERY_TASK_ALWAYS_EAGER = True
# CELERY_TASK_EAGER_PROPAGATES = True

print("[DEV] Usando configuracion de DESARROLLO (local.py)")
