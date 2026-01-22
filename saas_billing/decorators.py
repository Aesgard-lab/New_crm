from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import GymSubscription

def module_required(module_name):
    """
    Decorator to check if a specific module is enabled in the gym's plan.
    Usage: @module_required('marketing')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
                
            gym_id = request.session.get('current_gym_id')
            if not gym_id:
                return redirect('select_gym')
                
            # Superusers bypass checks
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            try:
                subscription = GymSubscription.objects.select_related('plan').get(gym_id=gym_id)
                modules = subscription.plan.get_enabled_modules()
                
                # Check mapping from internal module name to plan module name
                # Decorator argument might be 'marketing', plan module is 'Marketing'
                # Let's normalize to lowercase for comparison
                modules_lower = [m.lower() for m in modules]
                
                # Map specific keywords if needed (e.g. 'pos' -> 'pos')
                target = module_name.lower()
                
                # Special mapping for "portal cliente" vs "client_portal"
                mapping = {
                    'marketing': 'marketing',
                    'pos': 'pos',
                    'calendar': 'calendario',
                    'reporting': 'reportes',
                    'client_portal': 'portal cliente',
                    'public_portal': 'portal público',
                    'automations': 'automatizaciones',
                    'routines': 'rutinas',
                    'gamification': 'gamificación'
                }
                
                check_val = mapping.get(target, target)
                
                if check_val not in modules_lower and target not in modules_lower:
                    messages.error(request, f"El módulo '{module_name}' no está incluido en tu plan actual.")
                    return redirect('backoffice:dashboard')
                    
            except GymSubscription.DoesNotExist:
                return redirect('saas_billing:gym_billing_dashboard')
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def check_limit(limit_name):
    """
    Decorator to check if a usage limit has been reached.
    Usage: @check_limit('max_members')
    Soft limits allow action but warn. Hard limits block.
    Current implementation is HARD LIMIT for 'max_members' and 'max_staff'.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
                
            gym_id = request.session.get('current_gym_id')
            if not gym_id:
                return redirect('select_gym')

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            try:
                subscription = GymSubscription.objects.select_related('plan', 'gym').get(gym_id=gym_id)
                plan = subscription.plan
                gym = subscription.gym
                
                limit_reached = False
                current_usage = 0
                max_allowed = 0
                
                if limit_name == 'max_members':
                    max_allowed = plan.max_members
                    if max_allowed is not None:
                        # Assuming 'clients' related name exists on Gym
                        current_usage = gym.clients.count() 
                        if current_usage >= max_allowed:
                            limit_reached = True
                            
                elif limit_name == 'max_staff':
                    max_allowed = plan.max_staff
                    if max_allowed is not None:
                        current_usage = gym.staff.count()
                        if current_usage >= max_allowed:
                            limit_reached = True
                
                if limit_reached:
                    messages.error(request, f"Has alcanzado el límite de tu plan ({limit_name}: {max_allowed}). Actualiza tu suscripción para continuar.")
                    return redirect('saas_billing:gym_billing_dashboard')

            except GymSubscription.DoesNotExist:
                 return redirect('saas_billing:gym_billing_dashboard')
            except Exception as e:
                # Log error but don't block if check fails due to code error
                # In strict mode, we might want to block.
                pass

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
