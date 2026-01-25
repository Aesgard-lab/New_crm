"""
Feature Flags System

Sistema de feature flags para activar/desactivar funcionalidades
sin necesidad de hacer deploy.
"""
from django.db import models
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from functools import wraps
import hashlib
import random


class FeatureFlag(models.Model):
    """Modelo para almacenar feature flags en la base de datos."""
    
    class RolloutStrategy(models.TextChoices):
        ALL = 'all', 'Todos los usuarios'
        NONE = 'none', 'Ninguno'
        PERCENTAGE = 'percentage', 'Porcentaje de usuarios'
        USER_IDS = 'user_ids', 'IDs de usuarios especificos'
        GROUPS = 'groups', 'Grupos de usuarios'
        STAFF = 'staff', 'Solo staff'
        SUPERUSER = 'superuser', 'Solo superusuarios'
    
    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Nombre unico del feature flag (snake_case)'
    )
    description = models.TextField(
        blank=True,
        help_text='Descripcion de la funcionalidad'
    )
    enabled = models.BooleanField(
        default=False,
        help_text='Flag activo globalmente'
    )
    rollout_strategy = models.CharField(
        max_length=20,
        choices=RolloutStrategy.choices,
        default=RolloutStrategy.NONE
    )
    rollout_percentage = models.PositiveIntegerField(
        default=0,
        help_text='Porcentaje de usuarios (0-100)'
    )
    user_ids = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de IDs de usuarios especificos'
    )
    group_names = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de nombres de grupos'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_flags'
    )
    
    # Scheduling
    enable_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Activar automaticamente en esta fecha'
    )
    disable_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Desactivar automaticamente en esta fecha'
    )
    
    class Meta:
        verbose_name = 'Feature Flag'
        verbose_name_plural = 'Feature Flags'
        ordering = ['name']
    
    def __str__(self):
        status = 'ON' if self.enabled else 'OFF'
        return f"{self.name} [{status}]"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate cache
        cache.delete(f'feature_flag:{self.name}')
        cache.delete('feature_flags:all')
    
    def is_enabled_for_user(self, user=None):
        """Verifica si el flag esta activo para un usuario especifico."""
        # Check scheduling
        now = timezone.now()
        if self.enable_at and now < self.enable_at:
            return False
        if self.disable_at and now > self.disable_at:
            return False
        
        if not self.enabled:
            return False
        
        strategy = self.rollout_strategy
        
        if strategy == self.RolloutStrategy.ALL:
            return True
        
        if strategy == self.RolloutStrategy.NONE:
            return False
        
        if user is None or not user.is_authenticated:
            return False
        
        if strategy == self.RolloutStrategy.STAFF:
            return user.is_staff
        
        if strategy == self.RolloutStrategy.SUPERUSER:
            return user.is_superuser
        
        if strategy == self.RolloutStrategy.USER_IDS:
            return user.id in self.user_ids
        
        if strategy == self.RolloutStrategy.GROUPS:
            user_groups = set(user.groups.values_list('name', flat=True))
            flag_groups = set(self.group_names)
            return bool(user_groups & flag_groups)
        
        if strategy == self.RolloutStrategy.PERCENTAGE:
            # Deterministic percentage based on user ID
            hash_input = f"{self.name}:{user.id}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            user_percentage = hash_value % 100
            return user_percentage < self.rollout_percentage
        
        return False


class FeatureFlagService:
    """Servicio para consultar feature flags con cache."""
    
    CACHE_TIMEOUT = 300  # 5 minutos
    
    @classmethod
    def get_flag(cls, name: str) -> FeatureFlag | None:
        """Obtiene un flag por nombre con cache."""
        cache_key = f'feature_flag:{name}'
        flag = cache.get(cache_key)
        
        if flag is None:
            try:
                flag = FeatureFlag.objects.get(name=name)
                cache.set(cache_key, flag, cls.CACHE_TIMEOUT)
            except FeatureFlag.DoesNotExist:
                return None
        
        return flag
    
    @classmethod
    def is_enabled(cls, name: str, user=None) -> bool:
        """Verifica si un flag esta activo para un usuario."""
        flag = cls.get_flag(name)
        if flag is None:
            return False
        return flag.is_enabled_for_user(user)
    
    @classmethod
    def get_all_flags(cls) -> dict:
        """Obtiene todos los flags como diccionario."""
        cache_key = 'feature_flags:all'
        flags = cache.get(cache_key)
        
        if flags is None:
            flags = {
                f.name: f.enabled
                for f in FeatureFlag.objects.all()
            }
            cache.set(cache_key, flags, cls.CACHE_TIMEOUT)
        
        return flags
    
    @classmethod
    def get_enabled_flags_for_user(cls, user=None) -> list:
        """Obtiene lista de flags activos para un usuario."""
        enabled = []
        for flag in FeatureFlag.objects.filter(enabled=True):
            if flag.is_enabled_for_user(user):
                enabled.append(flag.name)
        return enabled
    
    @classmethod
    def invalidate_cache(cls, name: str = None):
        """Invalida cache de flags."""
        if name:
            cache.delete(f'feature_flag:{name}')
        cache.delete('feature_flags:all')


# Decorator for views
def feature_flag_required(flag_name: str, fallback_view=None):
    """
    Decorator que requiere que un feature flag este activo.
    
    Usage:
        @feature_flag_required('new_dashboard')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            
            if FeatureFlagService.is_enabled(flag_name, user):
                return view_func(request, *args, **kwargs)
            
            if fallback_view:
                return fallback_view(request, *args, **kwargs)
            
            from django.http import Http404
            raise Http404(f"Feature '{flag_name}' is not available")
        
        return wrapper
    return decorator


# Context processor
def feature_flags_context(request):
    """
    Context processor para acceder a feature flags en templates.
    
    Usage en templates:
        {% if feature_flags.new_dashboard %}
            <a href="{% url 'new_dashboard' %}">New Dashboard</a>
        {% endif %}
    """
    user = getattr(request, 'user', None)
    enabled_flags = FeatureFlagService.get_enabled_flags_for_user(user)
    
    return {
        'feature_flags': {flag: True for flag in enabled_flags}
    }


# Helper functions for use in code
def is_feature_enabled(name: str, user=None) -> bool:
    """Helper function para verificar si un flag esta activo."""
    return FeatureFlagService.is_enabled(name, user)


def get_feature_flags(user=None) -> list:
    """Helper function para obtener flags activos."""
    return FeatureFlagService.get_enabled_flags_for_user(user)
