"""
Configuración de producción.

⚠️ IMPORTANTE: Este archivo contiene configuraciones de seguridad críticas.
Asegúrate de que todas las variables de entorno estén configuradas correctamente.

Variables de entorno REQUERIDAS:
    - DJANGO_SECRET_KEY: Clave secreta única (mínimo 50 caracteres)
    - DJANGO_ALLOWED_HOSTS: Lista de dominios permitidos
    - POSTGRES_*: Credenciales de base de datos
    - REDIS_URL: URL de Redis para caché y Celery
    - EMAIL_*: Configuración SMTP

Para usar este archivo:
    export DJANGO_SETTINGS_MODULE=config.settings.production
"""

from .base import *

# --------------------------------------------------
# DEBUG MODE (NUNCA True en produccion)
# --------------------------------------------------
DEBUG = False

# --------------------------------------------------
# SECURITY KEY VALIDATION
# --------------------------------------------------
if SECRET_KEY == "dev-secret-key-CHANGE-IN-PRODUCTION":
    raise ValueError(
        "❌ SECURITY ERROR: Debes configurar DJANGO_SECRET_KEY en producción. "
        "Genera una clave con: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
    )

# --------------------------------------------------
# ALLOWED HOSTS (OBLIGATORIO en producción)
# --------------------------------------------------
_allowed_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "")
if not _allowed_hosts:
    raise ValueError(
        "❌ SECURITY ERROR: Debes configurar DJANGO_ALLOWED_HOSTS en producción. "
        "Ejemplo: DJANGO_ALLOWED_HOSTS=tudominio.com,www.tudominio.com"
    )
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(",") if h.strip()]

# --------------------------------------------------
# CSRF TRUSTED ORIGINS (Django 4.0+)
# --------------------------------------------------
_csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]
else:
    # Derivar de ALLOWED_HOSTS
    CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]

# --------------------------------------------------
# DATABASE (Producción - PostgreSQL con optimizaciones)
# --------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        # Optimizaciones de conexión
        "CONN_MAX_AGE": 600,  # 10 minutos
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000",  # 30s timeout para queries
        },
    }
}

# Validar configuración de base de datos
for key in ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST"]:
    if not os.getenv(key):
        raise ValueError(f"❌ DATABASE ERROR: Variable de entorno {key} no configurada")

# --------------------------------------------------
# CACHING (Redis OBLIGATORIO en producción)
# --------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError(
        "❌ CACHE ERROR: Debes configurar REDIS_URL en producción. "
        "Ejemplo: REDIS_URL=redis://localhost:6379/1"
    )

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'TIMEOUT': 300,
        'KEY_PREFIX': 'crm_prod',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        }
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL.replace('/1', '/2') if '/1' in REDIS_URL else f"{REDIS_URL}/2",
        'TIMEOUT': 86400,  # 1 dia
        'KEY_PREFIX': 'crm_session',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    },
}

# Sesiones en Redis para mejor rendimiento
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'

# --------------------------------------------------
# SECURITY SETTINGS (CRÍTICO)
# --------------------------------------------------
# HTTPS
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies seguras
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 3600  # 1 hora

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Protección XSS y Content-Type
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# --------------------------------------------------
# CORS (Restrictivo en producción)
# --------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
_cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in _cors_origins.split(',')
    if origin.strip()
] if _cors_origins else [f"https://{host}" for host in ALLOWED_HOSTS]

# --------------------------------------------------
# STATIC FILES (WhiteNoise optimizado)
# --------------------------------------------------
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# O usar S3 si está configurado
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
if AWS_ACCESS_KEY_ID:
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'eu-west-1')
    AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN')
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    # Usar S3 para estáticos y media
    # STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# --------------------------------------------------
# EMAIL (SMTP en producción)
# --------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

if not EMAIL_HOST_USER:
    import warnings
    warnings.warn("⚠️ EMAIL_HOST_USER no configurado. Los emails no se enviarán.")

# --------------------------------------------------
# TEMPLATES (con caché para rendimiento)
# --------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.gym_permissions",
                "saas_billing.context_processors.subscription_warnings",
                "saas_billing.context_processors.system_branding",
                "core.context_processors.translations",
            ],
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                    ],
                ),
            ],
        },
    },
]

# --------------------------------------------------
# SENTRY (Error Tracking y Performance Monitoring)
# --------------------------------------------------
# Usar nuestro modulo de configuracion avanzada
from core.sentry import init_sentry
init_sentry()

# --------------------------------------------------
# LOGGING (Produccion - JSON estructurado)
# --------------------------------------------------
from core.logging import get_logging_config
LOGGING = get_logging_config(environment='production', log_level='INFO')

# --------------------------------------------------
# REQUEST LOGGING MIDDLEWARE
# --------------------------------------------------
# Agregar middleware de logging al final
MIDDLEWARE = MIDDLEWARE + ['core.logging.RequestLoggingMiddleware']

# --------------------------------------------------
# CELERY (Producción)
# --------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL.replace('/1', '/0'))
CELERY_RESULT_BACKEND = "django-db"

# Configuraciones de producción
CELERY_TASK_ACKS_LATE = True  # Confirmar tareas después de ejecutar
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Una tarea a la vez
CELERY_TASK_TIME_LIMIT = 300  # 5 minutos máximo por tarea
CELERY_TASK_SOFT_TIME_LIMIT = 240  # Warning a los 4 minutos

# --------------------------------------------------
# ADMINS (para notificaciones de errores)
# --------------------------------------------------
_admins = os.getenv('DJANGO_ADMINS', '')
if _admins:
    ADMINS = [
        tuple(admin.split(':')) for admin in _admins.split(',')
        if ':' in admin
    ]
    MANAGERS = ADMINS

print("[PROD] Usando configuracion de PRODUCCION (production.py)")
