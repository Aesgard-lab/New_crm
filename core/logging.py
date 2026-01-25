"""
Sistema de Logging Estructurado para produccion.

Proporciona:
- JSON logging para facil parsing
- Contexto automatico (request_id, user, gym)
- Integracion con Sentry
- Rotacion de logs

Uso:
    from core.logging import get_logger, log_with_context
    
    logger = get_logger(__name__)
    logger.info("Mensaje", extra={'client_id': 123})
"""

import json
import logging
import sys
import traceback
import uuid
from datetime import datetime
from typing import Any, Optional

from django.conf import settings


# ==============================================
# JSON FORMATTER
# ==============================================

class JSONFormatter(logging.Formatter):
    """
    Formatter que produce logs en formato JSON.
    
    Ideal para:
    - ELK Stack (Elasticsearch, Logstash, Kibana)
    - CloudWatch Logs
    - Datadog
    - Splunk
    """
    
    def __init__(self, *args, **kwargs):
        self.app_name = kwargs.pop('app_name', 'crm')
        self.environment = kwargs.pop('environment', 'production')
        super().__init__(*args, **kwargs)
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'app': self.app_name,
            'environment': self.environment,
        }
        
        # Agregar ubicacion del codigo
        log_data['source'] = {
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName,
        }
        
        # Agregar contexto extra
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'gym_id'):
            log_data['gym_id'] = record.gym_id
        
        # Agregar cualquier extra adicional
        extra_keys = set(record.__dict__.keys()) - set(logging.LogRecord('', 0, '', 0, '', (), None).__dict__.keys())
        for key in extra_keys:
            if key not in ['request_id', 'user_id', 'gym_id', 'message']:
                value = getattr(record, key)
                if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    log_data[key] = value
        
        # Agregar exception info
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': ''.join(traceback.format_exception(*record.exc_info)),
            }
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """
    Formatter con colores para desarrollo local.
    """
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


# ==============================================
# CONTEXT FILTER
# ==============================================

class RequestContextFilter(logging.Filter):
    """
    Filter que agrega contexto de request a los logs.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Intentar obtener request actual
        try:
            from django.contrib.auth.models import AnonymousUser
            from threading import local
            
            _thread_local = getattr(self, '_thread_local', None)
            if _thread_local is None:
                self._thread_local = local()
                _thread_local = self._thread_local
            
            # Agregar request_id si no existe
            if not hasattr(record, 'request_id'):
                record.request_id = getattr(_thread_local, 'request_id', '-')
            
            if not hasattr(record, 'user_id'):
                record.user_id = getattr(_thread_local, 'user_id', None)
            
            if not hasattr(record, 'gym_id'):
                record.gym_id = getattr(_thread_local, 'gym_id', None)
                
        except Exception:
            record.request_id = '-'
            record.user_id = None
            record.gym_id = None
        
        return True


# ==============================================
# LOGGING MIDDLEWARE
# ==============================================

class RequestLoggingMiddleware:
    """
    Middleware para logging automatico de requests.
    
    Logs:
    - Request start/end
    - Duration
    - Status code
    - User y Gym context
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('django.request')
    
    def __call__(self, request):
        # Generar request_id
        request_id = request.META.get('HTTP_X_REQUEST_ID') or str(uuid.uuid4())[:8]
        request.request_id = request_id
        
        # Guardar en thread local para el filter
        from threading import local
        _thread_local = local()
        _thread_local.request_id = request_id
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            _thread_local.user_id = request.user.id
        
        gym_id = getattr(request, 'gym_id', None) or request.session.get('gym_id')
        if gym_id:
            _thread_local.gym_id = gym_id
        
        # Log request start
        import time
        start_time = time.time()
        
        # Procesar request
        response = self.get_response(request)
        
        # Calcular duracion
        duration_ms = (time.time() - start_time) * 1000
        
        # Log request end
        log_data = {
            'request_id': request_id,
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration_ms, 2),
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            'gym_id': gym_id,
            'ip': self._get_client_ip(request),
        }
        
        # Determinar nivel de log basado en status
        if response.status_code >= 500:
            self.logger.error("Request completed", extra=log_data)
        elif response.status_code >= 400:
            self.logger.warning("Request completed", extra=log_data)
        else:
            self.logger.info("Request completed", extra=log_data)
        
        # Agregar header de request_id a la respuesta
        response['X-Request-ID'] = request_id
        
        return response
    
    def _get_client_ip(self, request) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


# ==============================================
# HELPER FUNCTIONS
# ==============================================

def get_logger(name: str) -> logging.Logger:
    """
    Obtener logger con configuracion correcta.
    
    Uso:
        logger = get_logger(__name__)
        logger.info("Mensaje")
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context
) -> None:
    """
    Log con contexto adicional.
    
    Uso:
        log_with_context(logger, 'info', 'Client created', client_id=123, gym_id=1)
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra=context)


def log_exception(
    logger: logging.Logger,
    message: str = "Exception occurred",
    **context
) -> None:
    """
    Log exception con traceback completo.
    
    Uso:
        try:
            ...
        except Exception:
            log_exception(logger, "Failed to process", client_id=123)
    """
    logger.exception(message, extra=context)


# ==============================================
# CONFIGURACION DE LOGGING
# ==============================================

def get_logging_config(environment: str = 'production', log_level: str = 'INFO') -> dict:
    """
    Obtener configuracion de logging segun entorno.
    
    Args:
        environment: 'local', 'staging', 'production'
        log_level: 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    
    Returns:
        dict: Configuracion para LOGGING setting
    """
    
    if environment == 'local':
        # Desarrollo: logs coloridos a consola
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'colored': {
                    '()': ColoredFormatter,
                    'format': '%(levelname)s %(asctime)s %(name)s %(message)s',
                    'datefmt': '%H:%M:%S',
                },
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'colored',
                    'stream': sys.stdout,
                },
            },
            'root': {
                'handlers': ['console'],
                'level': log_level,
            },
            'loggers': {
                'django': {'level': 'INFO', 'propagate': True},
                'django.db.backends': {'level': 'WARNING', 'propagate': False},
            },
        }
    
    else:
        # Produccion/Staging: JSON logs
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'filters': {
                'request_context': {
                    '()': RequestContextFilter,
                },
            },
            'formatters': {
                'json': {
                    '()': JSONFormatter,
                    'app_name': 'crm',
                    'environment': environment,
                },
                'simple': {
                    'format': '%(levelname)s %(asctime)s %(name)s %(message)s',
                },
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'json',
                    'filters': ['request_context'],
                    'stream': sys.stdout,
                },
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': 'logs/app.log',
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': 5,
                    'formatter': 'json',
                    'filters': ['request_context'],
                },
                'error_file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': 'logs/error.log',
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': 10,
                    'formatter': 'json',
                    'filters': ['request_context'],
                    'level': 'ERROR',
                },
            },
            'root': {
                'handlers': ['console', 'file'],
                'level': log_level,
            },
            'loggers': {
                'django': {
                    'handlers': ['console', 'file'],
                    'level': 'INFO',
                    'propagate': False,
                },
                'django.request': {
                    'handlers': ['console', 'file', 'error_file'],
                    'level': 'INFO',
                    'propagate': False,
                },
                'django.db.backends': {
                    'handlers': ['console'],
                    'level': 'WARNING',
                    'propagate': False,
                },
                'celery': {
                    'handlers': ['console', 'file'],
                    'level': 'INFO',
                    'propagate': False,
                },
            },
        }
