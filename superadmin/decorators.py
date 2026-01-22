"""
Decorators for superadmin access control.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def superuser_required(view_func):
    """
    Decorator that ensures the user is a superuser.
    Combines @login_required and superuser check.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("❌ Acceso denegado. Solo superadmins pueden acceder a este panel.")
        return view_func(request, *args, **kwargs)
    return wrapper


def log_superadmin_action(action_type, description):
    """
    Decorator to automatically log superadmin actions to AuditLog.
    Usage: @log_superadmin_action('CREATE_GYM', 'Created new gym')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from saas_billing.models import AuditLog
            
            # Execute the view
            response = view_func(request, *args, **kwargs)
            
            # Log the action (only on successful responses)
            if response.status_code < 400:
                try:
                    AuditLog.objects.create(
                        superadmin=request.user,
                        action=action_type,
                        description=description,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                    )
                except Exception as e:
                    # Don't fail the request if logging fails
                    print(f"Failed to log superadmin action: {e}")
            
            return response
        return wrapper
    return decorator


def get_client_ip(request):
    """Get the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
