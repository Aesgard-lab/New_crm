# Estructura de Configuración por Entornos

## Descripción

El proyecto utiliza una estructura de configuración modular que permite mantener configuraciones específicas para cada entorno (desarrollo, staging, producción) mientras comparte configuraciones comunes.

## Estructura de Archivos

```
config/
├── settings/
│   ├── __init__.py      # Selector automático de entorno
│   ├── base.py          # Configuraciones comunes
│   ├── local.py         # Desarrollo local
│   ├── staging.py       # Pre-producción
│   └── production.py    # Producción
├── urls.py
├── wsgi.py
├── asgi.py
└── celery.py
```

## Cómo Funciona

### Selección Automática de Entorno

El entorno se selecciona mediante la variable de entorno `DJANGO_ENV`:

| Valor | Entorno | Archivo |
|-------|---------|---------|
| `local` (default) | Desarrollo | `local.py` |
| `staging` | Pre-producción | `staging.py` |
| `production` | Producción | `production.py` |

### Uso

#### Desarrollo (por defecto)
```bash
# Sin configurar nada, usa local.py
python manage.py runserver

# O explícitamente
DJANGO_ENV=local python manage.py runserver
```

#### Staging
```bash
DJANGO_ENV=staging python manage.py runserver
```

#### Producción
```bash
DJANGO_ENV=production python manage.py check --deploy
DJANGO_ENV=production gunicorn config.wsgi:application
```

## Jerarquía de Configuración

```
base.py (configuraciones comunes)
    ↓
local.py / staging.py / production.py (sobrescribe según entorno)
```

### base.py
Contiene todas las configuraciones que son iguales en todos los entornos:
- Apps instaladas
- Middleware
- Configuración de templates
- Validadores de contraseña
- Internacionalización
- Configuración base de logging

### local.py (Desarrollo)
- `DEBUG = True`
- Hosts permitidos locales
- Email a consola
- Cache en memoria local
- Cookies no seguras
- CORS permisivo
- Logging verboso

### staging.py (Pre-producción)
- Similar a producción pero más permisivo
- Permite DEBUG condicional
- HSTS más corto
- Logging más verboso
- Permite datos de prueba

### production.py (Producción)
- `DEBUG = False` (siempre)
- Validación estricta de SECRET_KEY
- HTTPS obligatorio
- HSTS configurado
- Cookies seguras
- Redis obligatorio
- Sentry integrado
- Logging a archivos
- Templates cacheados

## Variables de Entorno Requeridas

### Desarrollo (local.py)
```env
DJANGO_ENV=local
DJANGO_SECRET_KEY=cualquier-valor-para-desarrollo
POSTGRES_DB=new_gym
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_password
```

### Staging (staging.py)
```env
DJANGO_ENV=staging
DJANGO_SECRET_KEY=clave-segura
DJANGO_ALLOWED_HOSTS=staging.tudominio.com
POSTGRES_DB=crm_staging
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password_seguro
```

### Producción (production.py)
```env
DJANGO_ENV=production
DJANGO_SECRET_KEY=clave-muy-segura-minimo-50-caracteres
DJANGO_ALLOWED_HOSTS=tudominio.com,www.tudominio.com
POSTGRES_DB=crm_production
POSTGRES_USER=crm_user
POSTGRES_PASSWORD=password_muy_seguro
POSTGRES_HOST=db.tudominio.com
REDIS_URL=redis://localhost:6379/1
EMAIL_HOST=smtp.proveedor.com
EMAIL_HOST_USER=tu_email
EMAIL_HOST_PASSWORD=password_email
SENTRY_DSN=https://xxx@sentry.io/xxx
```

## Generar SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Verificar Configuración de Producción

```bash
DJANGO_ENV=production python manage.py check --deploy
```

## Migraciones por Entorno

```bash
# Desarrollo
python manage.py migrate

# Producción
DJANGO_ENV=production python manage.py migrate
```

## Recolectar Estáticos

```bash
# Producción
DJANGO_ENV=production python manage.py collectstatic --noinput
```

## Notas de Seguridad

1. **NUNCA** subas el archivo `.env` a git
2. **NUNCA** uses `DEBUG=True` en producción
3. **SIEMPRE** genera un SECRET_KEY único para producción
4. **SIEMPRE** usa HTTPS en producción
5. **SIEMPRE** configura ALLOWED_HOSTS en producción

## Troubleshooting

### "SECRET_KEY debe configurarse en producción"
```bash
# Genera una clave y añádela al .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### "REDIS_URL no configurada"
Redis es obligatorio en producción para cache y sesiones. Instala Redis y configura la URL.

### "DJANGO_ALLOWED_HOSTS no configurada"
Añade los dominios permitidos:
```env
DJANGO_ALLOWED_HOSTS=tudominio.com,www.tudominio.com
```
