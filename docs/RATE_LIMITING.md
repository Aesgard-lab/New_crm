# Rate Limiting

## Descripcion General

El sistema de rate limiting protege la aplicacion contra:
- Ataques de fuerza bruta
- Abuso de la API
- Ataques DDoS
- Scraping excesivo

Se implementa en dos niveles:
1. **Middleware global**: Limite general para todas las requests
2. **Decoradores/Throttles**: Limites especificos por endpoint

---

## Limites por Defecto

| Tipo | Limite | Descripcion |
|------|--------|-------------|
| API General | 100/min | Endpoints API normales |
| API Heavy | 20/min | Operaciones pesadas (exports) |
| Login | 5/min | Intentos de login |
| Register | 3/min | Registros de usuario |
| Password Reset | 3/hour | Solicitudes de reset |
| Upload | 10/min | Subida de archivos |
| Webhook | 1000/min | Webhooks externos |
| Public | 30/min | Endpoints publicos |
| Admin | 200/min | Panel de administracion |

---

## Uso en Vistas Django

### Decoradores Disponibles

```python
from core.ratelimit import (
    ratelimit_api,
    ratelimit_login,
    ratelimit_register,
    ratelimit_password_reset,
    ratelimit_upload,
    ratelimit_public,
)

# API general
@ratelimit_api
def my_api_view(request):
    return JsonResponse({'data': 'ok'})

# Con limite personalizado
@ratelimit_api(rate='50/m')
def custom_rate_view(request):
    return JsonResponse({'data': 'ok'})

# Login (muy restrictivo)
@ratelimit_login
def login_view(request):
    # Solo 5 intentos por minuto por IP
    ...

# Registro
@ratelimit_register
def register_view(request):
    # Solo 3 registros por minuto por IP
    ...

# Uploads
@ratelimit_upload
def upload_file(request):
    # 10 uploads por minuto por usuario
    ...

# Endpoints publicos
@ratelimit_public
def public_schedule(request):
    # 30 requests por minuto por IP
    ...
```

### Keys de Identificacion

```python
# Por IP (default para anonimos)
@ratelimit_api(key='ip')
def view(request): ...

# Por usuario autenticado
@ratelimit_api(key='user')
def view(request): ...

# Por gimnasio (multi-tenant)
@ratelimit_api(key='gym')
def view(request): ...
```

---

## Uso en Django REST Framework

### Throttle Classes

```python
from rest_framework.views import APIView
from core.throttling import (
    LoginThrottle,
    RegistrationThrottle,
    UploadThrottle,
    HeavyOperationThrottle,
)

class LoginAPIView(APIView):
    throttle_classes = [LoginThrottle]
    
    def post(self, request):
        ...

class ExportReportView(APIView):
    throttle_classes = [HeavyOperationThrottle]
    
    def get(self, request):
        # Solo 10 exports por minuto
        ...
```

### En ViewSets

```python
from rest_framework import viewsets
from core.throttling import APIUserThrottle, HeavyOperationThrottle

class ClientViewSet(viewsets.ModelViewSet):
    throttle_classes = [APIUserThrottle]
    
    # Override para accion especifica
    @action(detail=False, methods=['get'])
    def export(self, request):
        # Usar throttle mas restrictivo
        self.throttle_classes = [HeavyOperationThrottle]
        self.check_throttles(request)
        ...
```

---

## Configuracion

### Variables de Entorno

```env
# Limites personalizados
RATE_LIMIT_API=100/m
RATE_LIMIT_LOGIN=5/m
RATE_LIMIT_REGISTER=3/m
RATE_LIMIT_PASSWORD_RESET=3/h
RATE_LIMIT_UPLOAD=10/m
RATE_LIMIT_PUBLIC=30/m
```

### settings.py

```python
# Habilitar/deshabilitar
RATELIMIT_ENABLE = True

# Backend de cache (usar Redis en produccion)
RATELIMIT_USE_CACHE = 'default'

# Limites personalizados
RATE_LIMITS = {
    'api': '100/m',
    'login': '5/m',
    # ...
}

# DRF Throttling
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'core.throttling.APIAnonThrottle',
        'core.throttling.APIUserThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/min',
        'user': '100/min',
        # ...
    },
}
```

---

## Headers de Respuesta

Las respuestas incluyen headers informativos:

```
X-RateLimit-Limit: 100       # Limite total
X-RateLimit-Remaining: 95    # Requests restantes
X-RateLimit-Window: 60       # Ventana en segundos
```

---

## Respuesta de Rate Limited

Cuando se excede el limite:

```json
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
    "error": "rate_limited",
    "message": "Too many requests. Please slow down.",
    "retry_after": 60
}
```

---

## Verificacion Manual

```python
from core.ratelimit import check_rate_limit, reset_rate_limit, get_rate_limit_status

# Verificar limite
allowed, remaining = check_rate_limit('custom_key', limit=10, window=60)
if not allowed:
    return JsonResponse({'error': 'rate_limited'}, status=429)

# Resetear limite (ej: despues de verificacion exitosa)
reset_rate_limit('custom_key')

# Obtener estado actual
status = get_rate_limit_status(request)
# {'ip': '192.168.1.1', 'current_requests': 5, 'limit': 1000, 'remaining': 995}
```

---

## Nginx Rate Limiting (Adicional)

Para proteccion adicional a nivel de proxy:

```nginx
# En nginx.conf
http {
    # Zonas de rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;
    
    # Conexiones simultaneas
    limit_conn_zone $binary_remote_addr zone=conn:10m;
}

# En server block
server {
    # API general
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        limit_conn conn 10;
        proxy_pass http://django;
    }
    
    # Login mas restrictivo
    location /api/auth/login/ {
        limit_req zone=login burst=5;
        proxy_pass http://django;
    }
}
```

---

## Excluir Paths

El middleware excluye automaticamente:
- `/health/` - Health checks
- `/static/` - Archivos estaticos
- `/media/` - Archivos media
- `/favicon.ico`

Para agregar mas:

```python
# En core/ratelimit.py
class RateLimitMiddleware:
    EXCLUDED_PATHS = [
        '/health/',
        '/static/',
        '/media/',
        '/favicon.ico',
        '/mi-path-excluido/',  # Agregar aqui
    ]
```

---

## Monitoreo

### Logs

Los rate limits se loguean automaticamente:

```
WARNING Rate limit exceeded for IP 192.168.1.1 on /api/clients/
```

### Metricas

Si usas Prometheus:

```python
# Contador de rate limits
rate_limit_exceeded = Counter(
    'rate_limit_exceeded_total',
    'Total rate limit exceeded',
    ['endpoint', 'ip']
)
```

### Alertas

Configurar alertas si hay muchos 429:

```yaml
# alertmanager
- alert: HighRateLimitRate
  expr: rate(http_responses_total{status="429"}[5m]) > 10
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High rate limit rate detected"
```

---

## Troubleshooting

### Rate limit no funciona

1. Verificar que `RATELIMIT_ENABLE = True`
2. Verificar que el cache esta funcionando
3. Verificar que el middleware esta en MIDDLEWARE

### Rate limit muy agresivo

1. Aumentar limites en `.env`
2. Excluir paths especificos
3. Usar `key='user'` en lugar de `key='ip'` para autenticados

### Redis no disponible

El sistema funciona con cache local, pero es menos preciso en multiples instancias.

```python
# Fallback a memoria local
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
```

---

## Buenas Practicas

1. **Usar Redis en produccion** para rate limiting preciso
2. **Rate limit en Nginx tambien** para proteccion a nivel de proxy
3. **Monitorear 429s** para ajustar limites
4. **Diferentes limites** para anonimos vs autenticados
5. **Limites mas bajos** para operaciones sensibles (login, reset)
6. **Documentar limites** en la API para clientes
