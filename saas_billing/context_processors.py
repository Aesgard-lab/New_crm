from .models import GymSubscription

def subscription_warnings(request):
    """
    Context processor to add subscription warnings (past due, limits near)
    to the template context.
    """
    warnings = []
    show_upgrade_cta = False
    
    if request.user.is_authenticated and request.session.get('current_gym_id'):
        gym_id = request.session.get('current_gym_id')
        try:
            subscription = GymSubscription.objects.select_related('plan', 'gym').get(gym_id=gym_id)
            
            # Status Warning
            if subscription.status == 'PAST_DUE':
                warnings.append({
                    'type': 'danger', 
                    'message': 'Tu suscripción tiene un pago pendiente. Actualiza tu método de pago para evitar la suspensión.',
                    'link': 'saas_billing:gym_billing_dashboard'
                })
            
            # Limit Warnings (e.g. > 90% usage)
            plan = subscription.plan
            if plan.max_members:
                usage = subscription.gym.clients.count()
                if usage >= plan.max_members * 0.9:
                     warnings.append({
                        'type': 'warning',
                        'message': f"Estás cerca del límite de socios ({usage}/{plan.max_members}).",
                        'link': 'saas_billing:gym_billing_dashboard'
                    })
                     show_upgrade_cta = True

        except GymSubscription.DoesNotExist:
             warnings.append({
                'type': 'danger', 
                'message': 'No tienes una suscripción activa.',
                'link': 'saas_billing:gym_billing_dashboard'
            })
    
    return {
        'subscription_warnings': warnings,
        'show_upgrade_cta': show_upgrade_cta
    }


def system_branding(request):
    """
    Context processor to provide system branding (logo, name) 
    for white-label login pages.
    """
    from .models import BillingConfig
    
    try:
        config = BillingConfig.get_config()
        return {
            'system_name': config.system_name or 'New CRM',
            'system_logo': config.system_logo if config.system_logo else None,
        }
    except Exception:
        return {
            'system_name': 'New CRM',
            'system_logo': None,
        }
