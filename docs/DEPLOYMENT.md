# Guia de Despliegue a Produccion

## Resumen de Configuracion

Este documento resume todos los pasos implementados para el despliegue a produccion.

---

## 1. Estructura de Settings

```
config/settings/
├── __init__.py      # Selector automatico de entorno
├── base.py          # Configuracion comun
├── local.py         # Desarrollo local
├── staging.py       # Pre-produccion
└── production.py    # Produccion
```

**Selector de entorno** via `DJANGO_ENV`:
```bash
export DJANGO_ENV=production  # production | staging | local
```

---

## 2. Docker

### Archivos
- `Dockerfile` - Multi-stage build optimizado
- `docker-compose.yml` - Desarrollo
- `docker-compose.prod.yml` - Produccion con Nginx

### Comandos
```bash
# Desarrollo
docker-compose up -d

# Produccion
docker-compose -f docker-compose.prod.yml up -d

# Ver logs
docker-compose logs -f web
```

---

## 3. CI/CD (GitHub Actions)

### Workflows
- `.github/workflows/ci.yml` - Tests y linting en PRs
- `.github/workflows/cd.yml` - Deploy automatico en merge a main
- `.github/workflows/security.yml` - Escaneo de seguridad semanal
- `.github/workflows/docker.yml` - Build de imagenes Docker

### Configurar Secrets
```
DJANGO_SECRET_KEY
POSTGRES_PASSWORD
REDIS_PASSWORD
SENTRY_DSN
SSH_PRIVATE_KEY (para deploy)
```

---

## 4. Monitoreo (Sentry)

### Configuracion
```env
SENTRY_DSN=https://xxx@sentry.io/123
SENTRY_ENVIRONMENT=production
```

### Funcionalidades
- Error tracking automatico
- Performance monitoring
- Release tracking
- User context

---

## 5. Backups Automaticos

### Comandos
```bash
# Backup manual
python manage.py backup --database
python manage.py backup --full --upload-s3

# Restaurar
python manage.py restore --latest

# Listar
python manage.py backup --list
```

### Programacion (Celery Beat)
- DB diario: 3:00 AM
- Media semanal: Domingos 4:00 AM
- Limpieza: Lunes 5:00 AM

---

## 6. Health Checks

### Endpoints
```
GET /health/ping/    → Simple ping
GET /health/live/    → Liveness probe
GET /health/ready/   → Readiness probe
GET /health/         → Estado detallado
```

### Docker
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/ready/"]
  interval: 30s
```

---

## 7. Rate Limiting

### Limites
| Tipo | Limite |
|------|--------|
| API | 100/min |
| Login | 5/min |
| Upload | 10/min |

### Uso
```python
from core.ratelimit import ratelimit_api

@ratelimit_api
def my_view(request): ...
```

---

## 8. Cache (Redis)

### Configuracion
```env
REDIS_URL=redis://localhost:6379/1
```

### Uso
```python
from core.cache import cache_response, cache_queryset

@cache_response(timeout=300)
def my_view(request): ...

data = cache_queryset('key', MyModel.objects.all())
```

---

## 9. Logging Estructurado

### Formato JSON (produccion)
```json
{
  "timestamp": "2024-01-15T12:00:00Z",
  "level": "INFO",
  "message": "Request completed",
  "request_id": "abc123",
  "user_id": 1,
  "duration_ms": 45.2
}
```

### Archivos
- `logs/app.log` - Logs generales
- `logs/error.log` - Solo errores

---

## 10. Documentacion API

### URLs
```
GET /api/docs/    → Swagger UI
GET /api/redoc/   → ReDoc
GET /api/schema/  → OpenAPI JSON
```

---

## Variables de Entorno (Produccion)

```env
# Django
DJANGO_ENV=production
DJANGO_SECRET_KEY=<clave-secreta-50-chars>
DJANGO_ALLOWED_HOSTS=tudominio.com,www.tudominio.com
CSRF_TRUSTED_ORIGINS=https://tudominio.com

# Database
POSTGRES_DB=crm_prod
POSTGRES_USER=crm_user
POSTGRES_PASSWORD=<password-seguro>
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://:password@redis:6379/1
CELERY_BROKER_URL=redis://:password@redis:6379/0

# Email
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<sendgrid-api-key>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@tudominio.com

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/123

# Payments
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Backups (opcional S3)
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_S3_BUCKET_NAME=backups-bucket
```

---

## Checklist Pre-Deploy

- [ ] Variables de entorno configuradas
- [ ] Base de datos migrada
- [ ] Static files collectados
- [ ] SSL/HTTPS configurado
- [ ] Backups programados
- [ ] Monitoring activo (Sentry)
- [ ] Health checks funcionando
- [ ] Rate limiting activo
- [ ] Logs configurados

---

## Comandos de Deploy

```bash
# 1. Pull changes
git pull origin main

# 2. Build
docker-compose -f docker-compose.prod.yml build

# 3. Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# 4. Collect static
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# 5. Restart
docker-compose -f docker-compose.prod.yml up -d

# 6. Verify
curl https://tudominio.com/health/ready/
```

---

## Documentacion Adicional

- [docs/BACKUPS.md](docs/BACKUPS.md) - Sistema de backups
- [docs/HEALTH_CHECKS.md](docs/HEALTH_CHECKS.md) - Health checks
- [docs/RATE_LIMITING.md](docs/RATE_LIMITING.md) - Rate limiting
- [docs/SENTRY.md](docs/SENTRY.md) - Monitoreo con Sentry
