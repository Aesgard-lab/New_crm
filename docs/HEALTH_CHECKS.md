# Health Check Endpoints

## Descripcion General

El sistema proporciona endpoints de health check para monitoreo de la aplicacion,
compatibles con Docker, Kubernetes, load balancers y sistemas de monitoreo.

---

## Endpoints Disponibles

### GET /health/ping/
**Ping simple** - Respuesta minima para checks muy frecuentes.

```bash
curl http://localhost:8000/health/ping/
```

Respuesta:
```json
{"pong": true}
```

---

### GET /health/live/
**Liveness Probe** - Indica si la aplicacion esta corriendo.

Uso: Docker HEALTHCHECK, Kubernetes livenessProbe

```bash
curl http://localhost:8000/health/live/
```

Respuestas:
- `200 OK`: Aplicacion corriendo
- `503`: Aplicacion no responde

```json
{
  "status": "alive",
  "message": "Application is running"
}
```

---

### GET /health/ready/
**Readiness Probe** - Indica si la aplicacion puede recibir trafico.

Uso: Kubernetes readinessProbe, load balancer health checks

```bash
curl http://localhost:8000/health/ready/
```

Respuestas:
- `200 OK`: Lista para recibir trafico
- `503`: No lista (DB no disponible, etc.)

```json
{
  "status": "ready",
  "message": "Application is ready to receive traffic"
}
```

---

### GET /health/
**Estado Detallado** - Informacion completa de todos los componentes.

Uso: Dashboards de monitoreo, debugging

```bash
# Respuesta simplificada
curl http://localhost:8000/health/

# Respuesta detallada
curl "http://localhost:8000/health/?verbose=true"
```

Respuesta simplificada:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "components": {
    "database": "healthy",
    "cache": "healthy",
    "filesystem": "healthy",
    "celery": "healthy"
  }
}
```

Respuesta detallada (`?verbose=true`):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2024-01-15T12:30:00Z",
  "components": [
    {
      "name": "database",
      "status": "healthy",
      "latency_ms": 5.23,
      "details": {
        "engine": "django.db.backends.postgresql",
        "name": "crm_db"
      }
    },
    {
      "name": "cache",
      "status": "healthy",
      "latency_ms": 1.05,
      "details": {
        "backend": "django_redis.cache.RedisCache"
      }
    },
    {
      "name": "filesystem",
      "status": "healthy",
      "latency_ms": 0.52,
      "details": {
        "media_root": "/app/media",
        "static_root": "/app/staticfiles"
      }
    },
    {
      "name": "celery",
      "status": "healthy",
      "latency_ms": 12.34,
      "details": {
        "broker": "redis:6379/0"
      }
    }
  ]
}
```

---

## Estados de Salud

| Estado | Descripcion | HTTP Code |
|--------|-------------|-----------|
| `healthy` | Todos los componentes funcionando | 200 |
| `degraded` | Algunos componentes con problemas no criticos | 200 |
| `unhealthy` | Componente critico caido | 503 |

---

## Configuracion Docker

### Dockerfile
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live/ || exit 1
```

### Docker Compose
```yaml
services:
  web:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/ready/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
```

---

## Configuracion Kubernetes

### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-web
spec:
  template:
    spec:
      containers:
      - name: web
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/live/
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /health/live/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          failureThreshold: 30
```

---

## Configuracion Nginx

### upstream health check
```nginx
upstream django {
    server web:8000;
    
    # Health check (requiere nginx plus o modulo adicional)
    # health_check uri=/health/ready/ interval=10s;
}

location /health/ {
    proxy_pass http://django;
    proxy_set_header Host $host;
    
    # No cachear health checks
    add_header Cache-Control "no-store, no-cache";
    
    # Permitir acceso sin rate limiting
    limit_req off;
}
```

---

## Load Balancer (AWS ALB)

### Target Group Health Check
- **Protocol**: HTTP
- **Path**: `/health/ready/`
- **Port**: 8000
- **Healthy threshold**: 2
- **Unhealthy threshold**: 3
- **Timeout**: 5 seconds
- **Interval**: 30 seconds
- **Success codes**: 200

---

## Monitoreo con Prometheus

### Metrics Endpoint (opcional)
Si usas django-prometheus, puedes exponer metricas:

```python
# settings.py
INSTALLED_APPS += ['django_prometheus']

# urls.py
urlpatterns += [
    path('metrics/', include('django_prometheus.urls')),
]
```

### Prometheus scrape config
```yaml
scrape_configs:
  - job_name: 'crm-health'
    metrics_path: /health/
    static_configs:
      - targets: ['web:8000']
    scrape_interval: 30s
```

---

## Integracion con Alertas

### Ejemplo alertmanager
```yaml
groups:
- name: crm-alerts
  rules:
  - alert: CRMUnhealthy
    expr: probe_success{job="crm-health"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "CRM application is unhealthy"
      description: "Health check has been failing for more than 5 minutes"
```

---

## API Programatica

```python
from core.health import health_checker, HealthStatus

# Verificar si esta listo
if health_checker.is_ready():
    print("App lista para trafico")

# Obtener reporte completo
report = health_checker.get_health_report()
print(f"Estado: {report.status.value}")

for component in report.components:
    print(f"  {component.name}: {component.status.value}")
    if component.latency_ms:
        print(f"    Latencia: {component.latency_ms:.2f}ms")
```

---

## Agregar Checks Personalizados

```python
from core.health import HealthChecker, ComponentHealth, HealthStatus

class CustomHealthChecker(HealthChecker):
    def __init__(self):
        super().__init__()
        # Agregar check personalizado
        self.checks.append(("payment_gateway", self.check_payment_gateway))
    
    def check_payment_gateway(self) -> ComponentHealth:
        try:
            # Tu logica aqui
            response = requests.get("https://api.stripe.com/health", timeout=5)
            if response.status_code == 200:
                return ComponentHealth(
                    name="payment_gateway",
                    status=HealthStatus.HEALTHY,
                )
        except Exception as e:
            return ComponentHealth(
                name="payment_gateway",
                status=HealthStatus.DEGRADED,
                message=str(e),
            )
```

---

## Troubleshooting

### Health check falla constantemente
1. Verificar que la DB esta corriendo: `docker-compose ps db`
2. Verificar logs: `docker-compose logs web`
3. Probar endpoint manualmente: `curl -v http://localhost:8000/health/`

### Latencia alta en database
- Verificar conexiones: `SELECT count(*) FROM pg_stat_activity;`
- Optimizar queries lentos
- Aumentar pool de conexiones

### Cache marcado como degradado
- Verificar Redis: `redis-cli ping`
- Verificar configuracion CACHES en settings
- En desarrollo sin Redis, es normal que este degradado
