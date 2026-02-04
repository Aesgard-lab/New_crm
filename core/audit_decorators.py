"""
Decorador para logging de auditoría de acciones críticas
"""
from functools import wraps
from django.utils import timezone
import json
from core.ratelimit import get_client_ip

def log_action(action, module, get_target=None):
    """
    Decorador para registrar acciones en AuditLog
    
    Uso:
    @log_action("CREATE", "Clientes")
    def my_view(request):
        ...
    
    @log_action("UPDATE", "Clientes", get_target=lambda req, args, kwargs: f"Cliente #{kwargs.get('client_id')}")
    def client_edit(request, client_id):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Ejecutar la vista
            response = view_func(request, *args, **kwargs)
            
            # Solo registrar si la acción fue exitosa (redirect o 2xx)
            should_log = False
            if hasattr(response, 'status_code'):
                should_log = 200 <= response.status_code < 400
            elif hasattr(response, 'url'):  # HttpResponseRedirect
                should_log = True
            
            # Registrar en audit log si el usuario está autenticado
            if should_log and request.user.is_authenticated and hasattr(request, 'gym'):
                try:
                    from staff.models import AuditLog
                    
                    # Obtener IP
                    ip = get_client_ip(request)
                    
                    # Obtener target dinámicamente si se proporcionó la función
                    target = ''
                    if callable(get_target):
                        try:
                            target = get_target(request, args, kwargs)
                        except Exception:
                            pass
                    
                    # Obtener detalles según el módulo
                    details = {
                        'method': request.method,
                        'path': request.path,
                    }
                    
                    # Añadir datos POST relevantes (sin contraseñas)
                    if request.method == 'POST' and request.POST:
                        safe_data = {k: v for k, v in request.POST.items() 
                                    if 'password' not in k.lower() and 'token' not in k.lower() and 'csrf' not in k.lower()}
                        if safe_data:
                            details['form_data'] = safe_data
                    
                    AuditLog.objects.create(
                        gym=request.gym,
                        user=request.user,
                        action=action,
                        module=module,
                        target=target[:255] if target else '',
                        details=json.dumps(details, default=str, ensure_ascii=False),
                        ip_address=ip,
                    )
                except Exception:
                    # No fallar la vista si el log falla
                    pass
            
            return response
        return wrapper
    return decorator


def log_login(request, success=True):
    """
    Helper para registrar logins directamente (no como decorador)
    """
    if hasattr(request, 'gym') and request.user.is_authenticated:
        try:
            from staff.models import AuditLog
            
            ip = get_client_ip(request)
            
            AuditLog.objects.create(
                gym=request.gym,
                user=request.user,
                action='LOGIN' if success else 'LOGIN_FAILED',
                module='Auth',
                target=request.user.email or request.user.username,
                details=json.dumps({
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                    'success': success,
                }),
                ip_address=ip,
            )
        except Exception:
            pass
