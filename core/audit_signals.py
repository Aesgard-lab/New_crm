"""
Sistema de Signals para auditoría automática de cambios en modelos.

Registra automáticamente:
- Creación de entidades críticas
- Modificaciones importantes
- Eliminaciones

Uso:
    En el archivo apps.py del app:
    
    class MyAppConfig(AppConfig):
        def ready(self):
            from core import audit_signals  # noqa: F401
"""
import json
import logging
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

logger = logging.getLogger('audit')

# Modelos a auditar automáticamente
AUDITED_MODELS = [
    'clients.Client',
    'clients.ClientMembership',
    'memberships.MembershipPlan',
    'activities.ActivitySessionBooking',
    'finance.Payment',
    'finance.Invoice',
    'organizations.Gym',
    'accounts.User',
]

# Campos sensibles que no se deben loggear
SENSITIVE_FIELDS = {
    'password', 'password_hash', 'secret_key', 'api_key',
    'stripe_secret_key', 'stripe_customer_id', 'card_number',
    'cvv', 'pin', 'access_token', 'refresh_token',
}


def get_model_label(instance) -> str:
    """Obtiene el label del modelo (app_label.model_name)."""
    return f"{instance._meta.app_label}.{instance._meta.model_name}"


def get_model_changes(instance) -> dict:
    """
    Detecta los cambios en un modelo comparando con la versión en DB.
    
    Returns:
        dict con campos modificados: {field: {'old': x, 'new': y}}
    """
    if not instance.pk:
        return {}
    
    try:
        old_instance = instance.__class__.objects.get(pk=instance.pk)
    except instance.__class__.DoesNotExist:
        return {}
    
    changes = {}
    for field in instance._meta.fields:
        field_name = field.name
        
        # Skip campos sensibles
        if field_name in SENSITIVE_FIELDS:
            continue
        
        old_value = getattr(old_instance, field_name, None)
        new_value = getattr(instance, field_name, None)
        
        if old_value != new_value:
            changes[field_name] = {
                'old': str(old_value) if old_value is not None else None,
                'new': str(new_value) if new_value is not None else None,
            }
    
    return changes


def sanitize_for_json(obj: Any) -> Any:
    """Convierte objetos a formatos serializables en JSON."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    return str(obj)


def log_audit_event(
    action: str,
    instance,
    user=None,
    changes: dict = None,
    extra: dict = None,
):
    """
    Registra un evento de auditoría.
    
    En producción, esto debería escribir a un AuditLog model.
    Por ahora, usa logging estructurado.
    """
    model_label = get_model_label(instance)
    
    audit_data = {
        'action': action,
        'model': model_label,
        'object_id': str(instance.pk) if instance.pk else None,
        'object_repr': str(instance)[:200],
    }
    
    if user:
        audit_data['user_id'] = str(user.pk)
        audit_data['user_email'] = getattr(user, 'email', str(user))
    
    if changes:
        audit_data['changes'] = sanitize_for_json(changes)
    
    if extra:
        audit_data['extra'] = sanitize_for_json(extra)
    
    # Log estructurado
    logger.info(
        f"AUDIT: {action} {model_label} (id={instance.pk})",
        extra={'audit': audit_data}
    )
    
    # Intentar guardar en modelo AuditLog si existe
    try:
        if not settings.DEBUG:  # Solo en producción
            from staff.models import AuditLog
            
            gym = None
            if hasattr(instance, 'gym'):
                gym = instance.gym
            elif hasattr(instance, 'client') and hasattr(instance.client, 'gym'):
                gym = instance.client.gym
            
            if gym and user:
                AuditLog.objects.create(
                    gym=gym,
                    user=user,
                    action=action,
                    module=instance._meta.model_name,
                    target=str(instance.pk),
                    details=json.dumps(sanitize_for_json(audit_data)),
                )
    except Exception as e:
        logger.warning(f"Failed to save audit log to DB: {e}")


class AuditMiddleware:
    """
    Middleware que captura el usuario actual para auditoría.
    
    Almacena el usuario en thread-local para que las signals
    puedan acceder a él.
    """
    
    _current_user = None
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        AuditMiddleware._current_user = getattr(request, 'user', None)
        response = self.get_response(request)
        AuditMiddleware._current_user = None
        return response
    
    @classmethod
    def get_current_user(cls):
        return cls._current_user


def get_current_user():
    """Obtiene el usuario actual del contexto del request."""
    user = AuditMiddleware.get_current_user()
    if user and getattr(user, 'is_authenticated', False):
        return user
    return None


# ==============================================
# SIGNAL RECEIVERS
# ==============================================

@receiver(pre_save)
def capture_pre_save_state(sender, instance, **kwargs):
    """Captura el estado antes de guardar para detectar cambios."""
    model_label = f"{sender._meta.app_label}.{sender._meta.model_name}"
    
    if model_label not in AUDITED_MODELS:
        return
    
    # Guardar cambios en el instance para uso posterior
    if instance.pk:
        instance._audit_changes = get_model_changes(instance)
    else:
        instance._audit_changes = None


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """Registra creaciones y actualizaciones."""
    model_label = f"{sender._meta.app_label}.{sender._meta.model_name}"
    
    if model_label not in AUDITED_MODELS:
        return
    
    action = 'CREATE' if created else 'UPDATE'
    changes = getattr(instance, '_audit_changes', None)
    
    # Solo loggear updates si hay cambios reales
    if action == 'UPDATE' and not changes:
        return
    
    log_audit_event(
        action=action,
        instance=instance,
        user=get_current_user(),
        changes=changes,
    )


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    """Registra eliminaciones."""
    model_label = f"{sender._meta.app_label}.{sender._meta.model_name}"
    
    if model_label not in AUDITED_MODELS:
        return
    
    log_audit_event(
        action='DELETE',
        instance=instance,
        user=get_current_user(),
    )


# ==============================================
# DECORADORES PARA ACCIONES ESPECÍFICAS
# ==============================================

def audit_action(action: str, description: str = None):
    """
    Decorador para auditar acciones específicas en vistas.
    
    Uso:
        @audit_action('LOGIN', 'Usuario inició sesión')
        def login_view(request):
            ...
    """
    from functools import wraps
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            
            # Solo auditar si la acción fue exitosa
            if hasattr(response, 'status_code'):
                if 200 <= response.status_code < 300:
                    logger.info(
                        f"AUDIT ACTION: {action}",
                        extra={
                            'audit': {
                                'action': action,
                                'description': description,
                                'user_id': str(request.user.pk) if request.user.is_authenticated else None,
                                'path': request.path,
                                'method': request.method,
                            }
                        }
                    )
            
            return response
        return wrapper
    return decorator
