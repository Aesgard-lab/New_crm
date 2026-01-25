"""
Configuracion de Sentry para monitoreo de errores y rendimiento.

Este modulo configura Sentry con:
- Captura automatica de errores
- Monitoreo de rendimiento (transacciones)
- Integracion con Django y Celery
- Filtros de datos sensibles
- Contexto de usuario y gimnasio
"""

import os
import logging

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger(__name__)


def init_sentry():
    """
    Inicializa Sentry si SENTRY_DSN esta configurado.
    Llamar desde settings de produccion/staging.
    """
    sentry_dsn = os.getenv('SENTRY_DSN')
    
    if not sentry_dsn:
        logger.info("Sentry DSN no configurado, monitoreo deshabilitado")
        return False
    
    environment = os.getenv('DJANGO_ENV', 'local')
    release = os.getenv('RELEASE_VERSION', 'unknown')
    
    # Configuracion de logging para Sentry
    logging_integration = LoggingIntegration(
        level=logging.INFO,        # Capturar logs INFO y superiores como breadcrumbs
        event_level=logging.ERROR  # Enviar logs ERROR y superiores como eventos
    )
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        
        # Integraciones
        integrations=[
            DjangoIntegration(
                transaction_style='url',  # Usar URL pattern como nombre de transaccion
                middleware_spans=True,    # Crear spans para middleware
                signals_spans=True,       # Crear spans para signals
                cache_spans=True,         # Crear spans para cache
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,  # Monitorear tareas de Celery Beat
                propagate_traces=True,    # Propagar traces entre tareas
            ),
            RedisIntegration(),
            logging_integration,
        ],
        
        # Entorno y release
        environment=environment,
        release=release,
        
        # Muestreo de rendimiento
        traces_sample_rate=_get_traces_sample_rate(environment),
        profiles_sample_rate=_get_profiles_sample_rate(environment),
        
        # Muestreo de errores (100% por defecto)
        sample_rate=1.0,
        
        # Privacidad - NO enviar datos personales
        send_default_pii=False,
        
        # Filtrar datos sensibles
        before_send=_before_send,
        before_send_transaction=_before_send_transaction,
        
        # Configuracion adicional
        attach_stacktrace=True,
        include_source_context=True,
        include_local_variables=True,
        max_breadcrumbs=50,
        
        # Tags por defecto
        default_integrations=True,
    )
    
    # Configurar tags globales
    sentry_sdk.set_tag("app", "crm-django")
    sentry_sdk.set_tag("python_version", os.getenv('PYTHON_VERSION', 'unknown'))
    
    logger.info(f"Sentry inicializado - Entorno: {environment}, Release: {release}")
    return True


def _get_traces_sample_rate(environment: str) -> float:
    """
    Retorna el sample rate de transacciones segun el entorno.
    En produccion, muestrear menos para reducir costos.
    """
    rates = {
        'production': float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        'staging': 0.5,
        'local': 1.0,
    }
    return rates.get(environment, 0.1)


def _get_profiles_sample_rate(environment: str) -> float:
    """
    Retorna el sample rate de perfiles de rendimiento.
    """
    rates = {
        'production': float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '0.1')),
        'staging': 0.3,
        'local': 0.0,  # Deshabilitado en local
    }
    return rates.get(environment, 0.1)


def _before_send(event, hint):
    """
    Filtrar y modificar eventos antes de enviarlos a Sentry.
    Usar para:
    - Filtrar errores que no queremos reportar
    - Limpiar datos sensibles
    - Añadir contexto adicional
    """
    # Filtrar errores de autenticacion comunes
    if 'exc_info' in hint:
        exc_type, exc_value, _ = hint['exc_info']
        
        # No reportar errores 404
        from django.http import Http404
        if isinstance(exc_value, Http404):
            return None
        
        # No reportar errores de permisos (comunes en uso normal)
        from django.core.exceptions import PermissionDenied
        if isinstance(exc_value, PermissionDenied):
            return None
        
        # No reportar SuspiciousOperation (intentos de hacking)
        from django.core.exceptions import SuspiciousOperation
        if isinstance(exc_value, SuspiciousOperation):
            # Pero si loggearlo como warning
            logger.warning(f"SuspiciousOperation: {exc_value}")
            return None
    
    # Limpiar datos sensibles del request
    if 'request' in event:
        event = _scrub_request_data(event)
    
    return event


def _before_send_transaction(event, hint):
    """
    Filtrar transacciones antes de enviarlas.
    Util para excluir endpoints de health check, etc.
    """
    transaction_name = event.get('transaction', '')
    
    # No enviar transacciones de health checks
    if '/health' in transaction_name:
        return None
    
    # No enviar transacciones de estaticos
    if transaction_name.startswith('/static/'):
        return None
    
    if transaction_name.startswith('/media/'):
        return None
    
    return event


def _scrub_request_data(event):
    """
    Eliminar datos sensibles del request.
    """
    sensitive_fields = [
        'password', 'passwd', 'secret', 'token', 'api_key',
        'credit_card', 'card_number', 'cvv', 'ssn',
        'authorization', 'auth', 'cookie',
    ]
    
    request = event.get('request', {})
    
    # Limpiar headers
    if 'headers' in request:
        for header in list(request['headers'].keys()):
            if any(s in header.lower() for s in sensitive_fields):
                request['headers'][header] = '[Filtered]'
    
    # Limpiar datos del body
    if 'data' in request and isinstance(request['data'], dict):
        for key in list(request['data'].keys()):
            if any(s in key.lower() for s in sensitive_fields):
                request['data'][key] = '[Filtered]'
    
    # Limpiar cookies
    if 'cookies' in request:
        request['cookies'] = '[Filtered]'
    
    return event


# ==============================================
# FUNCIONES DE CONTEXTO
# ==============================================

def set_user_context(user):
    """
    Establecer contexto de usuario en Sentry.
    Llamar despues del login o en middleware.
    
    Args:
        user: Instancia de User de Django
    """
    if user and user.is_authenticated:
        sentry_sdk.set_user({
            'id': str(user.id),
            'email': user.email if hasattr(user, 'email') else None,
            'username': user.username if hasattr(user, 'username') else None,
            # NO incluir nombre completo por privacidad
        })
    else:
        sentry_sdk.set_user(None)


def set_gym_context(gym):
    """
    Establecer contexto de gimnasio en Sentry.
    
    Args:
        gym: Instancia de Gym
    """
    if gym:
        sentry_sdk.set_tag('gym_id', str(gym.id))
        sentry_sdk.set_tag('gym_name', gym.name)
        sentry_sdk.set_context('gym', {
            'id': str(gym.id),
            'name': gym.name,
            'plan': getattr(gym, 'plan', 'unknown'),
        })


def capture_message(message, level='info', **kwargs):
    """
    Enviar un mensaje a Sentry con contexto adicional.
    
    Args:
        message: Mensaje a enviar
        level: Nivel del mensaje (info, warning, error)
        **kwargs: Contexto adicional
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in kwargs.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_message(message, level=level)


def capture_exception(exception, **kwargs):
    """
    Capturar una excepcion con contexto adicional.
    
    Args:
        exception: Excepcion a capturar
        **kwargs: Contexto adicional
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in kwargs.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_exception(exception)
