# ⚠️ ARCHIVO DE SEGURIDAD - NO EDITAR MANUALMENTE
# 
# Este archivo contiene configuraciones de seguridad específicas
# de este proyecto. Las variables aquí definidas sobrescriben
# las configuraciones por defecto para proteger el sistema.

# Tiempo de expiración de sesión en segundos
SESSION_COOKIE_AGE = 3600  # 1 hora

# Tiempo de expiración de tokens CSRF (30 días)
CSRF_COOKIE_AGE = 2592000

# Configuraciones de CORS (si se usa)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Límite de tamaño de uploads (10MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 * 1024 * 1024

# Límite de campos en POST
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Configuraciones de caché (Redis recomendado en producción)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Logging de seguridad
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'logs/security.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
