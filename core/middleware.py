"""
Middleware para Sentry que anade contexto de usuario y gimnasio.
"""

import sentry_sdk
from django.conf import settings


class SentryContextMiddleware:
    """
    Middleware que establece el contexto de Sentry para cada request.
    
    Anade:
    - Informacion del usuario autenticado
    - Gimnasio actual (si aplica)
    - Tags personalizados
    
    Debe ir DESPUES de AuthenticationMiddleware y CurrentGymMiddleware.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Solo en produccion/staging donde Sentry esta activo
        if settings.DEBUG:
            return self.get_response(request)
        
        # Establecer contexto de usuario
        if hasattr(request, 'user') and request.user.is_authenticated:
            sentry_sdk.set_user({
                'id': str(request.user.id),
                'email': request.user.email,
                # No incluir nombre por privacidad (GDPR)
            })
            
            # Tags adicionales del usuario
            sentry_sdk.set_tag('user_type', self._get_user_type(request.user))
        else:
            sentry_sdk.set_user(None)
        
        # Establecer contexto de gimnasio
        if hasattr(request, 'current_gym') and request.current_gym:
            gym = request.current_gym
            sentry_sdk.set_tag('gym_id', str(gym.id))
            sentry_sdk.set_context('gym', {
                'id': str(gym.id),
                'name': gym.name,
            })
        
        # Contexto adicional del request
        sentry_sdk.set_context('request_info', {
            'path': request.path,
            'method': request.method,
            'is_ajax': request.headers.get('X-Requested-With') == 'XMLHttpRequest',
            'is_api': request.path.startswith('/api/'),
        })
        
        response = self.get_response(request)
        
        # Limpiar contexto despues del request
        sentry_sdk.set_user(None)
        
        return response
    
    def _get_user_type(self, user):
        """Determina el tipo de usuario para el tag."""
        if user.is_superuser:
            return 'superadmin'
        if user.is_staff:
            return 'staff'
        if hasattr(user, 'membership') and user.membership:
            return 'member'
        return 'user'
