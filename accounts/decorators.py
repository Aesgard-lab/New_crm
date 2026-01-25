from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from accounts.permissions import user_has_gym_permission

def require_gym_permission(permission_code):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            gym_id = request.session.get("current_gym_id")
            if not gym_id:
                return redirect("home")

            if not user_has_gym_permission(request.user, gym_id, permission_code):
                return redirect("home")

            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def require_staff(view_func):
    """
    Decorador que requiere que el usuario sea staff para acceder al backoffice.
    Redirige a los clientes al portal de clientes.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        # Verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Verificar si es staff o superuser
        if not (request.user.is_staff or request.user.is_superuser):
            # Si es un cliente, redirigir al portal de clientes
            if hasattr(request.user, 'client_profile'):
                messages.warning(request, 'No tienes permiso para acceder al backoffice.')
                return redirect('portal_home')
            else:
                messages.error(request, 'No tienes permisos para acceder a esta área.')
                return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped
