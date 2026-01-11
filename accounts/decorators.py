from functools import wraps
from django.shortcuts import redirect
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
