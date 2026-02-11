# ==============================================
# CONFIGURACIÓN PARA MODO BAJO RECURSOS
# ==============================================
# Añadir estas configuraciones a settings.py cuando
# el servidor tiene recursos muy limitados.
#
# Uso:
#   En settings.py, al final añadir:
#   from .settings_lightweight import *  # noqa

import os

# ==============================================
# DESACTIVAR FEATURES PESADOS
# ==============================================

# Desactivar logging extensivo de requests
LIGHTWEIGHT_MODE = True

# Desactivar auditoría automática de signals (ahorra CPU)
DISABLE_AUDIT_SIGNALS = True

# Desactivar middlewares no esenciales
MIDDLEWARE_LIGHTWEIGHT = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Mínimos requeridos
    "accounts.middleware.CurrentGymMiddleware",
]

# ==============================================
# OPTIMIZAR BASE DE DATOS
# ==============================================

# Menos conexiones persistentes
DATABASES['default']['CONN_MAX_AGE'] = 30
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 5,
}

# ==============================================
# OPTIMIZAR CACHE
# ==============================================

# Cache más agresivo para reducir queries
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'lightweight-cache',
        'TIMEOUT': 600,  # 10 minutos
        'OPTIONS': {
            'MAX_ENTRIES': 500  # Menos entradas = menos memoria
        }
    }
}

# ==============================================
# CELERY OPTIMIZACIONES
# ==============================================

# Tareas se ejecutan síncronamente si Celery no está disponible
CELERY_TASK_ALWAYS_EAGER = os.getenv('CELERY_EAGER', 'False') == 'True'

# Menos prefetch = menos memoria
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Reiniciar worker cada 50 tareas (previene memory leaks)
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50

# Deshabilitar eventos (ahorra CPU/memoria)
CELERY_WORKER_SEND_TASK_EVENTS = False
CELERY_TASK_SEND_SENT_EVENT = False

# ==============================================
# LOGGING MÍNIMO
# ==============================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,  # Desactiva loggers innecesarios
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',  # Solo warnings y errores
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# ==============================================
# TEMPLATES SIN DEBUG
# ==============================================

TEMPLATES[0]['OPTIONS']['debug'] = False

# ==============================================
# IMPORTS LAZY DE LIBRERÍAS PESADAS
# ==============================================

# Esto va en el código, pero como recordatorio:
# - NO importar pandas/matplotlib/weasyprint al inicio
# - Importar dentro de las funciones que los necesiten
# - Ejemplo:
#   def export_pdf(request):
#       from weasyprint import HTML  # Lazy import
#       ...

print("⚡ Modo Lightweight activado - Features reducidos para bajo consumo")
