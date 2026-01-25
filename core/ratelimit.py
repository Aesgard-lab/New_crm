"""
Sistema de Rate Limiting para proteccion contra abuso.

Proporciona:
- Decoradores para limitar requests por vista
- Middleware para rate limiting global
- Diferentes limites por tipo de endpoint
- Soporte para Redis como backend

Uso:
    from core.ratelimit import ratelimit_api, ratelimit_login
    
    @ratelimit_api
    def my_api_view(request):
        ...
    
    @ratelimit_login
    def login_view(request):
        ...
"""

import functools
import hashlib
import time
from typing import Optional, Callable

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse, HttpRequest
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited


# ==============================================
# CONFIGURACION DE LIMITES
# ==============================================

# Limites por defecto (requests/periodo)
RATE_LIMITS = {
    # API general
    'api': '100/m',           # 100 requests por minuto
    'api_heavy': '20/m',      # 20 para operaciones pesadas
    
    # Autenticacion (mas restrictivo)
    'login': '5/m',           # 5 intentos por minuto
    'register': '3/m',        # 3 registros por minuto
    'password_reset': '3/h',  # 3 por hora
    
    # Uploads
    'upload': '10/m',         # 10 uploads por minuto
    
    # Webhooks (mas permisivo)
    'webhook': '1000/m',      # 1000 por minuto
    
    # Public portal (mas restrictivo para anonimos)
    'public': '30/m',         # 30 requests por minuto
    
    # Admin/Backoffice
    'admin': '200/m',         # 200 por minuto (usuarios autenticados)
}


def get_rate_limit(key: str) -> str:
    """Obtener limite de rate por key, con soporte para override en settings."""
    custom_limits = getattr(settings, 'RATE_LIMITS', {})
    return custom_limits.get(key, RATE_LIMITS.get(key, '100/m'))


# ==============================================
# FUNCIONES DE IDENTIFICACION
# ==============================================

def get_client_ip(request: HttpRequest) -> str:
    """
    Obtener IP del cliente, considerando proxies.
    
    Prioridad:
    1. X-Forwarded-For (primer IP)
    2. X-Real-IP
    3. REMOTE_ADDR
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Tomar la primera IP (cliente original)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '')
    return ip


def get_rate_key_ip(group: str, request: HttpRequest) -> str:
    """Key basado en IP."""
    ip = get_client_ip(request)
    return f"{group}:{ip}"


def get_rate_key_user(group: str, request: HttpRequest) -> str:
    """Key basado en usuario autenticado o IP."""
    if request.user.is_authenticated:
        return f"{group}:user:{request.user.id}"
    return get_rate_key_ip(group, request)


def get_rate_key_gym(group: str, request: HttpRequest) -> str:
    """Key basado en gym (para multi-tenant)."""
    gym_id = getattr(request, 'gym_id', None) or request.session.get('gym_id')
    if gym_id:
        return f"{group}:gym:{gym_id}"
    return get_rate_key_user(group, request)


# ==============================================
# DECORADORES DE RATE LIMITING
# ==============================================

def ratelimit_api(view_func: Callable = None, rate: str = None, key: str = 'user'):
    """
    Decorador para rate limiting de endpoints API.
    
    Uso:
        @ratelimit_api
        def my_view(request): ...
        
        @ratelimit_api(rate='50/m')
        def custom_view(request): ...
    """
    actual_rate = rate or get_rate_limit('api')
    
    key_func = {
        'ip': get_rate_key_ip,
        'user': get_rate_key_user,
        'gym': get_rate_key_gym,
    }.get(key, get_rate_key_user)
    
    def decorator(func):
        @functools.wraps(func)
        @ratelimit(key=key_func, rate=actual_rate, method=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
        def wrapped(request, *args, **kwargs):
            return func(request, *args, **kwargs)
        return wrapped
    
    if view_func:
        return decorator(view_func)
    return decorator


def ratelimit_login(view_func: Callable):
    """Decorador especifico para login (muy restrictivo)."""
    rate = get_rate_limit('login')
    
    @functools.wraps(view_func)
    @ratelimit(key=get_rate_key_ip, rate=rate, method=['POST'])
    def wrapped(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapped


def ratelimit_register(view_func: Callable):
    """Decorador para registro de usuarios."""
    rate = get_rate_limit('register')
    
    @functools.wraps(view_func)
    @ratelimit(key=get_rate_key_ip, rate=rate, method=['POST'])
    def wrapped(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapped


def ratelimit_password_reset(view_func: Callable):
    """Decorador para reset de password."""
    rate = get_rate_limit('password_reset')
    
    @functools.wraps(view_func)
    @ratelimit(key=get_rate_key_ip, rate=rate, method=['POST'])
    def wrapped(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapped


def ratelimit_upload(view_func: Callable):
    """Decorador para uploads de archivos."""
    rate = get_rate_limit('upload')
    
    @functools.wraps(view_func)
    @ratelimit(key=get_rate_key_user, rate=rate, method=['POST'])
    def wrapped(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapped


def ratelimit_public(view_func: Callable):
    """Decorador para endpoints publicos."""
    rate = get_rate_limit('public')
    
    @functools.wraps(view_func)
    @ratelimit(key=get_rate_key_ip, rate=rate, method=['GET', 'POST'])
    def wrapped(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapped


# ==============================================
# MIDDLEWARE DE RATE LIMITING
# ==============================================

class RateLimitMiddleware:
    """
    Middleware para rate limiting global.
    
    Aplica limites basicos a todas las requests como capa de proteccion adicional.
    Los decoradores proporcionan control mas granular.
    """
    
    # Paths excluidos del rate limiting
    EXCLUDED_PATHS = [
        '/health/',
        '/static/',
        '/media/',
        '/favicon.ico',
    ]
    
    # Limite global (muy alto, solo para prevenir DDoS extremo)
    GLOBAL_RATE_LIMIT = 1000  # requests
    GLOBAL_RATE_WINDOW = 60   # segundos
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'RATELIMIT_ENABLE', True)
    
    def __call__(self, request):
        # Verificar si esta habilitado
        if not self.enabled:
            return self.get_response(request)
        
        # Verificar si el path esta excluido
        if self._is_excluded(request.path):
            return self.get_response(request)
        
        # Verificar limite global
        if self._is_rate_limited(request):
            return self._rate_limited_response(request)
        
        response = self.get_response(request)
        
        # Agregar headers de rate limit
        self._add_rate_headers(request, response)
        
        return response
    
    def _is_excluded(self, path: str) -> bool:
        """Verificar si el path esta excluido."""
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)
    
    def _get_cache_key(self, request: HttpRequest) -> str:
        """Generar key de cache para rate limiting."""
        ip = get_client_ip(request)
        return f"ratelimit:global:{ip}"
    
    def _is_rate_limited(self, request: HttpRequest) -> bool:
        """Verificar si la request excede el limite global."""
        cache_key = self._get_cache_key(request)
        
        # Obtener contador actual
        current = cache.get(cache_key, 0)
        
        if current >= self.GLOBAL_RATE_LIMIT:
            return True
        
        # Incrementar contador
        try:
            cache.incr(cache_key)
        except ValueError:
            # Key no existe, crear con timeout
            cache.set(cache_key, 1, self.GLOBAL_RATE_WINDOW)
        
        return False
    
    def _rate_limited_response(self, request: HttpRequest) -> JsonResponse:
        """Generar respuesta de rate limited."""
        return JsonResponse({
            'error': 'rate_limited',
            'message': 'Too many requests. Please slow down.',
            'retry_after': self.GLOBAL_RATE_WINDOW,
        }, status=429)
    
    def _add_rate_headers(self, request: HttpRequest, response) -> None:
        """Agregar headers de rate limit a la respuesta."""
        cache_key = self._get_cache_key(request)
        current = cache.get(cache_key, 0)
        remaining = max(0, self.GLOBAL_RATE_LIMIT - current)
        
        response['X-RateLimit-Limit'] = str(self.GLOBAL_RATE_LIMIT)
        response['X-RateLimit-Remaining'] = str(remaining)
        response['X-RateLimit-Window'] = str(self.GLOBAL_RATE_WINDOW)


# ==============================================
# HANDLER DE EXCEPCIONES
# ==============================================

def ratelimit_handler(request, exception):
    """
    Handler para excepciones de rate limit.
    Usar en urls.py o con middleware.
    """
    return JsonResponse({
        'error': 'rate_limited',
        'message': 'You have exceeded the rate limit for this endpoint.',
        'detail': 'Please wait before making more requests.',
    }, status=429)


# ==============================================
# UTILIDADES
# ==============================================

def check_rate_limit(key: str, limit: int, window: int) -> tuple[bool, int]:
    """
    Verificar rate limit manualmente.
    
    Returns:
        tuple: (is_allowed, remaining_requests)
    """
    cache_key = f"ratelimit:manual:{key}"
    current = cache.get(cache_key, 0)
    
    if current >= limit:
        return False, 0
    
    try:
        new_count = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, window)
        new_count = 1
    
    remaining = max(0, limit - new_count)
    return True, remaining


def reset_rate_limit(key: str) -> None:
    """Resetear rate limit para una key especifica."""
    cache_key = f"ratelimit:manual:{key}"
    cache.delete(cache_key)


def get_rate_limit_status(request: HttpRequest) -> dict:
    """Obtener estado actual de rate limit para una request."""
    ip = get_client_ip(request)
    cache_key = f"ratelimit:global:{ip}"
    current = cache.get(cache_key, 0)
    
    return {
        'ip': ip,
        'current_requests': current,
        'limit': RateLimitMiddleware.GLOBAL_RATE_LIMIT,
        'remaining': max(0, RateLimitMiddleware.GLOBAL_RATE_LIMIT - current),
        'window_seconds': RateLimitMiddleware.GLOBAL_RATE_WINDOW,
    }
