"""
Sistema de Cache para optimizacion de rendimiento.

Proporciona:
- Decoradores para cachear vistas y funciones
- Utilidades para cache de queries
- Cache de sesiones
- Invalidacion inteligente

Uso:
    from core.cache import cache_response, cache_queryset, invalidate_cache
    
    @cache_response(timeout=300)
    def my_view(request):
        ...
    
    queryset = cache_queryset('clients', Client.objects.all(), timeout=60)
"""

import functools
import hashlib
import json
import logging
from typing import Any, Callable, Optional, Union

from django.conf import settings
from django.core.cache import cache, caches
from django.http import HttpRequest, HttpResponse
from django.utils.encoding import force_str

logger = logging.getLogger(__name__)


# ==============================================
# CONFIGURACION
# ==============================================

# Prefijos para keys de cache
CACHE_PREFIX = getattr(settings, 'CACHE_PREFIX', 'crm')

# Timeouts por defecto (segundos)
CACHE_TIMEOUTS = {
    'short': 60,           # 1 minuto
    'medium': 300,         # 5 minutos
    'long': 3600,          # 1 hora
    'day': 86400,          # 1 dia
    'week': 604800,        # 1 semana
}


# ==============================================
# GENERACION DE KEYS
# ==============================================

def make_cache_key(*args, prefix: str = '', **kwargs) -> str:
    """
    Generar key de cache unica basada en argumentos.
    
    Args:
        *args: Argumentos posicionales
        prefix: Prefijo opcional
        **kwargs: Argumentos con nombre
    
    Returns:
        Key de cache hasheada
    """
    key_parts = [CACHE_PREFIX]
    
    if prefix:
        key_parts.append(prefix)
    
    # Agregar args
    for arg in args:
        key_parts.append(force_str(arg))
    
    # Agregar kwargs ordenados
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{force_str(v)}")
    
    key_string = ':'.join(key_parts)
    
    # Hash si es muy largo
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{CACHE_PREFIX}:{prefix}:{key_hash}"
    
    return key_string


def make_view_cache_key(request: HttpRequest, prefix: str = 'view') -> str:
    """Generar key de cache para una vista basada en la request."""
    key_parts = [
        prefix,
        request.path,
        request.method,
    ]
    
    # Incluir query params
    if request.GET:
        query_string = request.GET.urlencode()
        key_parts.append(query_string)
    
    # Incluir user si esta autenticado
    if request.user.is_authenticated:
        key_parts.append(f"user:{request.user.id}")
    
    # Incluir gym si existe
    gym_id = getattr(request, 'gym_id', None) or request.session.get('gym_id')
    if gym_id:
        key_parts.append(f"gym:{gym_id}")
    
    return make_cache_key(*key_parts, prefix=prefix)


# ==============================================
# DECORADORES DE CACHE
# ==============================================

def cache_response(
    timeout: Union[int, str] = 'medium',
    key_prefix: str = 'view',
    cache_name: str = 'default',
    vary_on_user: bool = True,
    vary_on_gym: bool = True,
):
    """
    Decorador para cachear respuestas de vistas.
    
    Args:
        timeout: Segundos o nombre de timeout ('short', 'medium', 'long')
        key_prefix: Prefijo para la key de cache
        cache_name: Nombre del cache a usar
        vary_on_user: Variar cache por usuario
        vary_on_gym: Variar cache por gimnasio
    
    Uso:
        @cache_response(timeout=300)
        def my_view(request):
            return JsonResponse({'data': 'expensive_data'})
    """
    if isinstance(timeout, str):
        timeout = CACHE_TIMEOUTS.get(timeout, 300)
    
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # Solo cachear GET requests
            if request.method != 'GET':
                return view_func(request, *args, **kwargs)
            
            # Generar key
            cache_key = make_view_cache_key(request, prefix=key_prefix)
            
            # Intentar obtener del cache
            cache_backend = caches[cache_name]
            cached_response = cache_backend.get(cache_key)
            
            if cached_response is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_response
            
            # Ejecutar vista y cachear
            logger.debug(f"Cache MISS: {cache_key}")
            response = view_func(request, *args, **kwargs)
            
            # Solo cachear respuestas exitosas
            if response.status_code == 200:
                cache_backend.set(cache_key, response, timeout)
            
            return response
        
        return wrapped
    return decorator


def cache_function(
    timeout: Union[int, str] = 'medium',
    key_prefix: str = 'func',
    cache_name: str = 'default',
):
    """
    Decorador para cachear resultados de funciones.
    
    Args:
        timeout: Segundos o nombre de timeout
        key_prefix: Prefijo para la key
        cache_name: Nombre del cache
    
    Uso:
        @cache_function(timeout='long')
        def expensive_calculation(param1, param2):
            ...
    """
    if isinstance(timeout, str):
        timeout = CACHE_TIMEOUTS.get(timeout, 300)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            # Generar key basada en funcion y argumentos
            func_name = f"{func.__module__}.{func.__name__}"
            cache_key = make_cache_key(func_name, *args, prefix=key_prefix, **kwargs)
            
            # Intentar obtener del cache
            cache_backend = caches[cache_name]
            cached_result = cache_backend.get(cache_key)
            
            if cached_result is not None:
                logger.debug(f"Function cache HIT: {func_name}")
                return cached_result
            
            # Ejecutar y cachear
            logger.debug(f"Function cache MISS: {func_name}")
            result = func(*args, **kwargs)
            cache_backend.set(cache_key, result, timeout)
            
            return result
        
        # Agregar metodo para invalidar
        wrapped.invalidate = lambda *args, **kwargs: invalidate_function_cache(
            func, *args, prefix=key_prefix, **kwargs
        )
        
        return wrapped
    return decorator


# ==============================================
# CACHE DE QUERYSETS
# ==============================================

def cache_queryset(
    key: str,
    queryset,
    timeout: Union[int, str] = 'medium',
    cache_name: str = 'default',
) -> list:
    """
    Cachear un queryset.
    
    Args:
        key: Key unica para este queryset
        queryset: QuerySet de Django
        timeout: Segundos o nombre de timeout
        cache_name: Nombre del cache
    
    Uso:
        clients = cache_queryset('gym_123_clients', Client.objects.filter(gym_id=123))
    """
    if isinstance(timeout, str):
        timeout = CACHE_TIMEOUTS.get(timeout, 300)
    
    cache_key = make_cache_key(key, prefix='qs')
    cache_backend = caches[cache_name]
    
    cached_result = cache_backend.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Evaluar queryset y cachear
    result = list(queryset)
    cache_backend.set(cache_key, result, timeout)
    
    return result


def cache_count(
    key: str,
    queryset,
    timeout: Union[int, str] = 'medium',
    cache_name: str = 'default',
) -> int:
    """Cachear el count de un queryset."""
    if isinstance(timeout, str):
        timeout = CACHE_TIMEOUTS.get(timeout, 300)
    
    cache_key = make_cache_key(key, prefix='count')
    cache_backend = caches[cache_name]
    
    cached_result = cache_backend.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    result = queryset.count()
    cache_backend.set(cache_key, result, timeout)
    
    return result


# ==============================================
# INVALIDACION DE CACHE
# ==============================================

def invalidate_cache(pattern: str, cache_name: str = 'default') -> int:
    """
    Invalidar cache por patron.
    
    Args:
        pattern: Patron de key (soporta * como wildcard)
        cache_name: Nombre del cache
    
    Returns:
        Numero de keys eliminadas
    
    Nota: Solo funciona con Redis backend
    """
    cache_backend = caches[cache_name]
    
    # Verificar si es Redis
    if hasattr(cache_backend, 'delete_pattern'):
        full_pattern = f"{CACHE_PREFIX}:{pattern}"
        return cache_backend.delete_pattern(full_pattern)
    
    # Fallback: no podemos hacer pattern delete
    logger.warning(f"Cache backend does not support pattern delete: {pattern}")
    return 0


def invalidate_function_cache(func: Callable, *args, prefix: str = 'func', **kwargs) -> bool:
    """Invalidar cache de una funcion especifica."""
    func_name = f"{func.__module__}.{func.__name__}"
    cache_key = make_cache_key(func_name, *args, prefix=prefix, **kwargs)
    return cache.delete(cache_key)


def invalidate_model_cache(model_name: str, instance_id: Optional[int] = None) -> int:
    """
    Invalidar cache relacionado a un modelo.
    
    Args:
        model_name: Nombre del modelo (ej: 'client', 'activity')
        instance_id: ID especifico o None para todos
    
    Uso:
        invalidate_model_cache('client')  # Todos los clientes
        invalidate_model_cache('client', 123)  # Cliente especifico
    """
    if instance_id:
        pattern = f"*{model_name}*{instance_id}*"
    else:
        pattern = f"*{model_name}*"
    
    return invalidate_cache(pattern)


def invalidate_gym_cache(gym_id: int) -> int:
    """Invalidar todo el cache de un gimnasio."""
    return invalidate_cache(f"*gym:{gym_id}*")


def invalidate_user_cache(user_id: int) -> int:
    """Invalidar todo el cache de un usuario."""
    return invalidate_cache(f"*user:{user_id}*")


# ==============================================
# CACHE WARMING
# ==============================================

def warm_cache(key: str, generator: Callable, timeout: Union[int, str] = 'long') -> Any:
    """
    Calentar cache: si no existe, generar y cachear.
    
    Uso:
        data = warm_cache('dashboard_stats', lambda: calculate_stats(), timeout='hour')
    """
    if isinstance(timeout, str):
        timeout = CACHE_TIMEOUTS.get(timeout, 3600)
    
    cache_key = make_cache_key(key, prefix='warm')
    
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    result = generator()
    cache.set(cache_key, result, timeout)
    
    return result


# ==============================================
# UTILIDADES
# ==============================================

def get_or_set(key: str, default: Callable, timeout: int = 300) -> Any:
    """
    Obtener del cache o generar y guardar.
    
    Similar a cache.get_or_set pero con prefix.
    """
    cache_key = make_cache_key(key)
    return cache.get_or_set(cache_key, default, timeout)


def cache_stats() -> dict:
    """Obtener estadisticas del cache (solo Redis)."""
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        info = redis_conn.info()
        
        return {
            'used_memory': info.get('used_memory_human'),
            'connected_clients': info.get('connected_clients'),
            'total_keys': redis_conn.dbsize(),
            'hits': info.get('keyspace_hits'),
            'misses': info.get('keyspace_misses'),
            'hit_rate': info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0)),
        }
    except Exception as e:
        logger.warning(f"Could not get cache stats: {e}")
        return {}


def clear_all_cache(cache_name: str = 'default') -> bool:
    """Limpiar todo el cache (usar con cuidado!)."""
    try:
        caches[cache_name].clear()
        logger.info("Cache cleared successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return False
