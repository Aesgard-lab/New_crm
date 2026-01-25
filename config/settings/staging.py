"""
Configuración de Staging/Pre-producción.

Similar a producción pero con algunas relajaciones para testing.

Para usar este archivo:
    export DJANGO_SETTINGS_MODULE=config.settings.staging
"""

from .base import *

# --------------------------------------------------
# DEBUG MODE
# --------------------------------------------------
DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"

# --------------------------------------------------
# ALLOWED HOSTS (Staging)
# --------------------------------------------------
_allowed_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "staging.tudominio.com")
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(",") if h.strip()]

# --------------------------------------------------
# CSRF TRUSTED ORIGINS
# --------------------------------------------------
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]

# --------------------------------------------------
# DATABASE (PostgreSQL)
# --------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "crm_staging"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

# --------------------------------------------------
# CACHING (Redis o memoria local)
# --------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'TIMEOUT': 300,
            'KEY_PREFIX': 'crm_staging',
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'staging-cache',
        }
    }

# --------------------------------------------------
# SECURITY (Similar a producción)
# --------------------------------------------------
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True") == "True"
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 7200  # 2 horas (más permisivo para testing)

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# HSTS más corto para staging
SECURE_HSTS_SECONDS = 3600  # 1 hora
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'  # Permite iframes del mismo origen (útil para testing)

# --------------------------------------------------
# CORS (Más permisivo para testing)
# --------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
_cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in _cors_origins.split(',')
    if origin.strip()
] if _cors_origins else [f"https://{host}" for host in ALLOWED_HOSTS]

# --------------------------------------------------
# STATIC FILES
# --------------------------------------------------
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --------------------------------------------------
# EMAIL (Staging - usar servicio de testing)
# --------------------------------------------------
# Puedes usar servicios como Mailtrap para staging
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND', 
    'django.core.mail.backends.console.EmailBackend'
)
if os.getenv('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# --------------------------------------------------
# SENTRY (Staging)
# --------------------------------------------------
SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.5,  # Más sampling en staging para testing
        profiles_sample_rate=0.5,
        environment="staging",
        release=os.getenv('RELEASE_VERSION', 'unknown'),
        send_default_pii=True,  # Permitido en staging para debug
    )

# --------------------------------------------------
# LOGGING (Staging - más verboso que producción)
# --------------------------------------------------
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
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# --------------------------------------------------
# TEST DATA FLAGS
# --------------------------------------------------
# Permitir reseteo de datos en staging (util para testing)
ALLOW_DATA_RESET = os.getenv("ALLOW_DATA_RESET", "False") == "True"

print("[STAGING] Usando configuracion de STAGING (staging.py)")
