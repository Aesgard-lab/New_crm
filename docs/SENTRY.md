# Sentry - Monitoreo de Errores y Rendimiento

## Descripcion

Sentry es una plataforma de monitoreo que captura errores y problemas de rendimiento en tiempo real. Esta configurado para:

- **Error Tracking**: Captura automatica de excepciones
- **Performance Monitoring**: Seguimiento de transacciones y latencia
- **Integracion con Celery**: Monitoreo de tareas en background
- **Contexto de Usuario**: Asocia errores con usuarios y gimnasios

## Configuracion

### 1. Crear cuenta en Sentry

1. Ve a [sentry.io](https://sentry.io) y crea una cuenta
2. Crea un nuevo proyecto de tipo **Django**
3. Copia el DSN que te proporciona

### 2. Variables de Entorno

```env
# Obligatorio
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# Opcionales
SENTRY_TRACES_SAMPLE_RATE=0.1    # 10% de transacciones
SENTRY_PROFILES_SAMPLE_RATE=0.1  # 10% de perfiles
RELEASE_VERSION=1.0.0            # Version del release
```

### 3. Sample Rates por Entorno

| Entorno | Traces | Profiles |
|---------|--------|----------|
| Production | 10% | 10% |
| Staging | 50% | 30% |
| Local | 100% | 0% |

## Uso

### Captura Automatica

Los errores se capturan automaticamente. No necesitas hacer nada especial.

### Captura Manual de Errores

```python
from core.sentry import capture_exception, capture_message

# Capturar una excepcion con contexto
try:
    proceso_peligroso()
except Exception as e:
    capture_exception(e, 
        gym_id=gym.id,
        action='proceso_peligroso'
    )

# Enviar un mensaje informativo
capture_message(
    "Usuario alcanzo limite de intentos",
    level='warning',
    user_id=user.id,
    attempts=5
)
```

### Establecer Contexto

```python
from core.sentry import set_user_context, set_gym_context

# Despues del login
set_user_context(request.user)

# Al cambiar de gimnasio
set_gym_context(gym)
```

### Transacciones Personalizadas

```python
import sentry_sdk

# Crear una transaccion para una operacion importante
with sentry_sdk.start_transaction(name="generar_informe", op="report"):
    # Span para la consulta
    with sentry_sdk.start_span(op="db", description="Consultar datos"):
        datos = obtener_datos()
    
    # Span para el procesamiento
    with sentry_sdk.start_span(op="process", description="Procesar datos"):
        resultado = procesar(datos)
    
    # Span para el guardado
    with sentry_sdk.start_span(op="save", description="Guardar resultado"):
        guardar(resultado)
```

### En Tareas Celery

```python
from celery import shared_task
import sentry_sdk

@shared_task
def tarea_importante(gym_id):
    # El contexto se establece automaticamente
    # pero puedes anadir mas
    sentry_sdk.set_tag('gym_id', gym_id)
    
    try:
        hacer_algo()
    except Exception as e:
        # La excepcion se captura automaticamente
        # pero puedes anadir contexto
        sentry_sdk.set_context('task_data', {
            'gym_id': gym_id,
            'intentos': 3,
        })
        raise
```

## Filtrado de Errores

Por defecto, NO se reportan:

- Errores 404 (Http404)
- Errores de permisos (PermissionDenied)
- Operaciones sospechosas (SuspiciousOperation)
- Health checks (/health/)
- Archivos estaticos (/static/, /media/)

Para modificar el filtrado, edita `core/sentry.py`:

```python
def _before_send(event, hint):
    # Anadir tu logica de filtrado aqui
    pass
```

## Datos Sensibles

Por privacidad (GDPR), NO se envian:

- Cookies
- Passwords
- Tokens de autenticacion
- Numeros de tarjeta
- Nombres completos de usuarios

El email y ID de usuario SI se envian para identificar problemas.

## Dashboard de Sentry

### Issues (Errores)

- Ve a **Issues** para ver todos los errores
- Agrupa por gimnasio con el tag `gym_id`
- Filtra por entorno con `environment:production`

### Performance

- Ve a **Performance** para ver latencia
- Identifica endpoints lentos
- Analiza transacciones de Celery

### Alertas

Configura alertas en **Alerts**:

```
# Alerta de tasa de errores
IF error_rate > 1% for 5 minutes
THEN notify Slack
```

## Releases

Para trackear deploys, configura la variable `RELEASE_VERSION`:

```bash
# En el deploy
export RELEASE_VERSION=$(git describe --tags)
```

O en CI/CD:

```yaml
env:
  RELEASE_VERSION: ${{ github.sha }}
```

## Troubleshooting

### Los errores no aparecen

1. Verifica que `SENTRY_DSN` esta configurado
2. Verifica que no estas en `DEBUG=True`
3. Revisa los logs: `Sentry inicializado - Entorno: ...`

### Demasiados errores

1. Revisa los filtros en `_before_send`
2. Ajusta `sample_rate` para reducir volumen
3. Agrupa errores similares en Sentry

### Performance muy lento

1. Reduce `traces_sample_rate`
2. Deshabilita `profiles_sample_rate`
3. Filtra transacciones innecesarias

## Recursos

- [Documentacion de Sentry](https://docs.sentry.io/)
- [Integracion Django](https://docs.sentry.io/platforms/python/integrations/django/)
- [Integracion Celery](https://docs.sentry.io/platforms/python/integrations/celery/)
