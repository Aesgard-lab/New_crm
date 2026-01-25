"""
Feature Flags Middleware

Agrega informacion de feature flags al request.
"""
from .feature_flags import FeatureFlagService


class FeatureFlagsMiddleware:
    """
    Middleware que agrega feature flags al request.
    
    Uso:
        request.feature_flags.is_enabled('new_feature')
        request.feature_flags.all()
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Agregar helper de feature flags al request
        request.feature_flags = FeatureFlagsHelper(request)
        
        response = self.get_response(request)
        return response


class FeatureFlagsHelper:
    """Helper class para acceder a feature flags desde el request."""
    
    def __init__(self, request):
        self.request = request
        self._user = getattr(request, 'user', None)
        self._enabled_flags = None
    
    def is_enabled(self, name: str) -> bool:
        """Verifica si un flag esta activo para el usuario actual."""
        return FeatureFlagService.is_enabled(name, self._user)
    
    def all(self) -> list:
        """Obtiene todos los flags activos para el usuario."""
        if self._enabled_flags is None:
            self._enabled_flags = FeatureFlagService.get_enabled_flags_for_user(self._user)
        return self._enabled_flags
    
    def __contains__(self, name: str) -> bool:
        """Permite usar 'in' operator: 'new_feature' in request.feature_flags"""
        return self.is_enabled(name)
    
    def __getitem__(self, name: str) -> bool:
        """Permite acceso por key: request.feature_flags['new_feature']"""
        return self.is_enabled(name)
