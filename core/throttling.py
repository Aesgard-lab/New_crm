"""
Throttling para Django REST Framework.

Proporciona clases de throttling personalizadas para la API.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, SimpleRateThrottle
from django.conf import settings


class BaseAPIThrottle(SimpleRateThrottle):
    """Base para throttles personalizados."""
    
    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class APIAnonThrottle(AnonRateThrottle):
    """Throttle para usuarios anonimos."""
    scope = 'anon'
    rate = '30/min'


class APIUserThrottle(UserRateThrottle):
    """Throttle para usuarios autenticados."""
    scope = 'user'
    rate = '100/min'


class APIBurstThrottle(BaseAPIThrottle):
    """Throttle para rafagas cortas."""
    scope = 'burst'
    rate = '10/sec'


class LoginThrottle(AnonRateThrottle):
    """Throttle especifico para login."""
    scope = 'login'
    rate = '5/min'


class RegistrationThrottle(AnonRateThrottle):
    """Throttle para registro."""
    scope = 'registration'
    rate = '3/min'


class PasswordResetThrottle(AnonRateThrottle):
    """Throttle para reset de password."""
    scope = 'password_reset'
    rate = '3/hour'


class UploadThrottle(UserRateThrottle):
    """Throttle para uploads."""
    scope = 'upload'
    rate = '10/min'


class WebhookThrottle(SimpleRateThrottle):
    """Throttle para webhooks (mas permisivo)."""
    scope = 'webhook'
    rate = '1000/min'
    
    def get_cache_key(self, request, view):
        # Identificar por IP para webhooks
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }


class HeavyOperationThrottle(UserRateThrottle):
    """Throttle para operaciones pesadas (exports, reports)."""
    scope = 'heavy'
    rate = '10/min'


# Configuracion para settings.py
DRF_THROTTLE_RATES = {
    'anon': '30/min',
    'user': '100/min',
    'burst': '10/sec',
    'login': '5/min',
    'registration': '3/min',
    'password_reset': '3/hour',
    'upload': '10/min',
    'webhook': '1000/min',
    'heavy': '10/min',
}
