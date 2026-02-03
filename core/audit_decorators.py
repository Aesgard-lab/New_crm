"""
Decorador para logging de auditoría de acciones críticas
"""
from functools import wraps
from django.utils import timezone
import json
from core.ratelimit import get_client_ip

def log_action(action, module):
    """
    Decorador para registrar acciones en AuditLog
    
    Uso:
    @log_action("CREATE", "Clients")
    def my_view(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Ejecutar la vista
            response = view_func(request, *args, **kwargs)
            
            # Registrar en audit log si el usuario está autenticado
            if request.user.is_authenticated and hasattr(request, 'gym'):
                try:
                    from staff.models import AuditLog
                    
                    # Obtener IP
                    ip = get_client_ip(request)
                    
                    # Obtener detalles según el módulo
                    details = {
                        'method': request.method,
                        'path': request.path,
                        'args': str(args),
                        'kwargs': str(kwargs),
                    }
                    
                    AuditLog.objects.create(
                        gym=request.gym,
                        user=request.user,
                        action=action,
                        module=module,
                        target='',
                        details=json.dumps(details),
                        ip_address=ip,
                    )
                except Exception:
                    # No fallar la vista si el log falla
                    pass
            
            return response
        return wrapper
    return decorator
