from pathlib import Path
import os
from dotenv import load_dotenv

# --------------------------------------------------
# BASE
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------
# SECURITY
# --------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")

DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"

_allowed_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(",") if h.strip()]

# --------------------------------------------------
# APPLICATIONS
# --------------------------------------------------
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Third-party
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
    "rest_framework",
    "rest_framework.authtoken",
    
    # Project apps
    "accounts.apps.AccountsConfig",
    "organizations",
    "backoffice",
    "clients",
    "staff",
    "activities",
    "services",
    "products",
    "providers",
    "memberships",
    "discounts",
    "finance",
    "sales",
    "reporting",
    "marketing",
    "routines",
    "gamification",  # Sistema de gamificación
    "public_portal",  # Portal público y widgets
    "saas_billing",  # SaaS billing and subscriptions
    "superadmin",  # Superadmin panel
    "api",
    "access_control",  # Control de acceso con tornos/puertas
    "lockers",  # Gestión de taquillas
    # "facial_checkin.apps.FacialCheckinConfig",  # Reconocimiento facial para check-in - DESACTIVADO por consumo de recursos
]

# --------------------------------------------------
# REST FRAMEWORK
# --------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'core.exception_handler.custom_exception_handler',
}

# --------------------------------------------------
# MIDDLEWARE
# --------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.SecurityHeadersMiddleware",  # SECURITY: CSP y headers adicionales
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Sirve estáticos eficientemente
    "django.middleware.gzip.GZipMiddleware",  # Compresión de respuestas
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # Internacionalización
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "saas_billing.middleware.SubscriptionMiddleware",
    # Custom
    "accounts.middleware.CurrentGymMiddleware",
]

# --------------------------------------------------
# URLS / WSGI
# --------------------------------------------------
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# --------------------------------------------------
# TEMPLATES
# --------------------------------------------------
# En producción usamos el loader cacheado para mejor rendimiento
if DEBUG:
    TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [BASE_DIR / "templates"],
            "APP_DIRS": True,
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
                    "public_portal.context_processors.portal_advertisements",
                ],
            },
        },
    ]
else:
    # Producción: Template caching para mejor rendimiento
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
                    "public_portal.context_processors.portal_advertisements",
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
# DATABASE (PostgreSQL)
# --------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "new_gym"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "123"),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        # Optimizaciones de conexión
        "CONN_MAX_AGE": 60,  # Mantener conexiones abiertas 60 segundos
        "CONN_HEALTH_CHECKS": True,  # Verificar salud de conexiones
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# --------------------------------------------------
# AUTH
# --------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# --------------------------------------------------
# INTERNATIONALIZATION
# --------------------------------------------------
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "es-es")
TIME_ZONE = os.getenv("TIME_ZONE", "Europe/Madrid")

USE_I18N = True
USE_TZ = True

# Idiomas soportados
from django.utils.translation import gettext_lazy as _
LANGUAGES = [
    ('es', _('Español')),
    ('en', _('English')),
]

# Rutas de archivos de traducción
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# --------------------------------------------------
# STATIC FILES
# --------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise - Compresión y caché de estáticos
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --------------------------------------------------
# MEDIA FILES
# --------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --------------------------------------------------
# DEFAULTS
# --------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------
# CACHING (Optimización de rendimiento)
# --------------------------------------------------
# En producción, usa Redis para mejor rendimiento
if os.getenv("REDIS_URL"):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv("REDIS_URL", "redis://localhost:6379/1"),
            'TIMEOUT': 300,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'crm',
        }
    }
    # Sesiones en Redis (más rápido)
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
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
# CELERY CONFIGURATION
# --------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "default"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# --------------------------------------------------
# SECURITY SETTINGS
# --------------------------------------------------

# Security headers aplicables en todos los entornos
X_FRAME_OPTIONS = 'SAMEORIGIN'  # Permite iframes solo del mismo origen
SECURE_CONTENT_TYPE_NOSNIFF = True  # Previene MIME sniffing
SECURE_BROWSER_XSS_FILTER = True  # Activa filtro XSS del navegador

if not DEBUG:
    # HTTPS Settings (solo producción)
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Cookie Security (estricta en producción)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_AGE = 3600  # 1 hora
    
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = 'Lax'
    
    # Más restrictivo en producción
    X_FRAME_OPTIONS = 'DENY'
    
    # Validate SECRET_KEY
    if SECRET_KEY == "dev-secret-key":
        raise ValueError("❌ SECURITY ERROR: SECRET_KEY debe configurarse en producción")
else:
    # Development: Cookies más permisivas pero con httponly
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True  # Siempre httponly
    CSRF_COOKIE_SECURE = False
    CSRF_COOKIE_HTTPONLY = True  # Siempre httponly
    SESSION_COOKIE_AGE = 86400  # 24 horas

# Rate Limiting (Desarrollo y Producción)
RATELIMIT_ENABLE = True
RATELIMIT_VIEW_DEFAULT = '100/h'  # 100 requests por hora por defecto

# CORS - SECURITY: Restrict origins in production
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in 
        os.getenv('CORS_ALLOWED_ORIGINS', 'https://localhost').split(',')
        if origin.strip()
    ]

# --------------------------------------------------
# EMAIL CONFIGURATION
# --------------------------------------------------
if DEBUG:
    # En desarrollo: Muestra los emails en la consola
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # En producción: Configuración SMTP real
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    
# Configuración común
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@tucrm.com')
SERVER_EMAIL = DEFAULT_FROM_EMAIL


