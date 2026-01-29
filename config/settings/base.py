"""
Configuración base de Django.
Contiene todas las configuraciones comunes entre entornos.

Uso:
- local.py hereda de base.py para desarrollo
- production.py hereda de base.py para producción
- staging.py hereda de base.py para entorno de pruebas
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# --------------------------------------------------
# BASE PATHS
# --------------------------------------------------
# El directorio base es el padre del directorio config/settings
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------
# SECURITY (valores por defecto, sobrescribir en producción)
# --------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-CHANGE-IN-PRODUCTION")

# DEBUG se define en cada entorno específico
DEBUG = False  # Por defecto seguro

# --------------------------------------------------
# HOSTS (sobrescribir en cada entorno)
# --------------------------------------------------
ALLOWED_HOSTS = []

# --------------------------------------------------
# APPLICATIONS
# --------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
]

LOCAL_APPS = [
    "core",  # Core utilities, commands, middleware
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
    "gamification",
    "public_portal",
    "saas_billing",
    "superadmin",
    "api",
    "access_control",
    "lockers",
    "facial_checkin.apps.FacialCheckinConfig",  # Reconocimiento facial para check-in
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

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
    'DEFAULT_THROTTLE_CLASSES': [
        'core.throttling.APIAnonThrottle',
        'core.throttling.APIUserThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/min',
        'user': '100/min',
        'burst': '10/sec',
        'login': '5/min',
        'registration': '3/min',
        'password_reset': '3/hour',
        'upload': '10/min',
        'webhook': '1000/min',
        'heavy': '10/min',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# --------------------------------------------------
# API DOCUMENTATION (OpenAPI / Swagger)
# --------------------------------------------------
SPECTACULAR_SETTINGS = {
    'TITLE': 'CRM Gym API',
    'DESCRIPTION': '''
## API del Sistema de Gestion para Gimnasios

Esta API proporciona acceso programatico a todas las funcionalidades del CRM:

### Modulos Principales
- **Clientes**: Gestion completa de clientes y membresias
- **Actividades**: Clases, sesiones y reservas
- **Staff**: Gestion de empleados y horarios
- **Finanzas**: Pagos, facturas y reportes
- **Marketing**: Campanas, leads y comunicaciones

### Autenticacion
La API usa autenticacion por Token. Incluye el header:
```
Authorization: Token <tu-token>
```

### Rate Limiting
- Usuarios anonimos: 30 requests/minuto
- Usuarios autenticados: 100 requests/minuto

### Soporte
Para soporte tecnico, contacta a soporte@tudominio.com
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/',
    'TAGS': [
        {'name': 'Auth', 'description': 'Autenticacion y tokens'},
        {'name': 'Clients', 'description': 'Gestion de clientes'},
        {'name': 'Activities', 'description': 'Clases y sesiones'},
        {'name': 'Staff', 'description': 'Empleados y horarios'},
        {'name': 'Finance', 'description': 'Pagos y facturacion'},
        {'name': 'Marketing', 'description': 'Campanas y leads'},
        {'name': 'Health', 'description': 'Estado del sistema'},
    ],
    'CONTACT': {
        'name': 'Soporte API',
        'email': 'api@tudominio.com',
    },
    'LICENSE': {
        'name': 'Proprietary',
    },
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
    },
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
    },
}

# --------------------------------------------------
# MIDDLEWARE
# --------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "core.ratelimit.RateLimitMiddleware",  # Rate limiting global
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "saas_billing.middleware.SubscriptionMiddleware",
    "accounts.middleware.CurrentGymMiddleware",
    "core.middleware.SentryContextMiddleware",  # Contexto para Sentry
]

# --------------------------------------------------
# URLS / WSGI / ASGI
# --------------------------------------------------
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --------------------------------------------------
# TEMPLATES (configuración base)
# --------------------------------------------------
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

# --------------------------------------------------
# DATABASE (PostgreSQL)
# --------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "new_gym"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
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

from django.utils.translation import gettext_lazy as _
LANGUAGES = [
    ('es', _('Español')),
    ('en', _('English')),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# --------------------------------------------------
# STATIC FILES
# --------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# --------------------------------------------------
# MEDIA FILES
# --------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --------------------------------------------------
# CACHE (configuracion base - override en produccion)
# --------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Cache settings
CACHE_PREFIX = 'crm'
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = CACHE_PREFIX
# --------------------------------------------------
# DEFAULTS
# --------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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

# Celery Beat Schedule (tareas programadas)
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    # Backup diario de DB a las 3:00 AM
    'backup-database-daily': {
        'task': 'core.tasks.backup_database_task',
        'schedule': crontab(hour=3, minute=0),
    },
    # Backup semanal de media los domingos a las 4:00 AM
    'backup-media-weekly': {
        'task': 'core.tasks.backup_media_task',
        'schedule': crontab(hour=4, minute=0, day_of_week='sunday'),
    },
    # Limpieza de backups antiguos los lunes a las 5:00 AM
    'cleanup-backups-weekly': {
        'task': 'core.tasks.cleanup_old_backups_task',
        'schedule': crontab(hour=5, minute=0, day_of_week='monday'),
    },
}

# --------------------------------------------------
# BACKUP CONFIGURATION
# --------------------------------------------------
BACKUP_DIR = os.getenv('BACKUP_DIR', str(BASE_DIR / 'backups'))
BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))

# --------------------------------------------------
# EMAIL (configuración base)
# --------------------------------------------------
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@tucrm.com')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --------------------------------------------------
# RATE LIMITING
# --------------------------------------------------
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'  # Usar cache de Redis en produccion

# Limites personalizados (override de defaults en core/ratelimit.py)
RATE_LIMITS = {
    'api': os.getenv('RATE_LIMIT_API', '100/m'),
    'api_heavy': os.getenv('RATE_LIMIT_API_HEAVY', '20/m'),
    'login': os.getenv('RATE_LIMIT_LOGIN', '5/m'),
    'register': os.getenv('RATE_LIMIT_REGISTER', '3/m'),
    'password_reset': os.getenv('RATE_LIMIT_PASSWORD_RESET', '3/h'),
    'upload': os.getenv('RATE_LIMIT_UPLOAD', '10/m'),
    'webhook': os.getenv('RATE_LIMIT_WEBHOOK', '1000/m'),
    'public': os.getenv('RATE_LIMIT_PUBLIC', '30/m'),
    'admin': os.getenv('RATE_LIMIT_ADMIN', '200/m'),
}

# --------------------------------------------------
# UPLOAD LIMITS
# --------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# --------------------------------------------------
# LOGGING (configuración base)
# --------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['mail_admins', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
