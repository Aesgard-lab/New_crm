from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from .models import GymSubscription
import logging

logger = logging.getLogger(__name__)

class SubscriptionMiddleware:
    """
    Middleware to enforce subscription status.
    Redirects to billing dashboard if subscription is SUSPENDED or CANCELLED,
    or if there is no active subscription for the gym.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Paths that are always accessible regardless of subscription status
        self.exempt_paths = [
            reverse('saas_billing:gym_billing_dashboard'),
            reverse('saas_billing:portal_session'),
            '/admin/', # Django admin
            '/superadmin/', # Superadmin panel
            '/accounts/logout/',
            '/accounts/login/',
            '/public/', # Public portal
            '/embed/', # Embed widgets
            '/webhook/', # Stripe webhooks (though usually handled by URL conf exclusion)
        ]

    def __call__(self, request):
        if self._is_exempt(request.path):
            return self.get_response(request)

        # Only check for authenticated users in a gym context
        if request.user.is_authenticated and request.session.get('current_gym_id'):
            gym_id = request.session.get('current_gym_id')
            
            # Skip if superuser (optional, depending on requirements)
            if request.user.is_superuser:
                return self.get_response(request)

            try:
                # Check subscription status
                # Optimization: Cache this query or store simple status in session
                subscription = GymSubscription.objects.get(gym_id=gym_id)
                
                # If subscription is unusable (e.g. cancelled/suspended)
                if subscription.status in ['CANCELLED', 'SUSPENDED']:
                     # Allow viewing billing to fix it
                     if not request.path.startswith('/finance/billing/'):
                         return redirect('saas_billing:gym_billing_dashboard')
                         
            except GymSubscription.DoesNotExist:
                # No subscription found - redirect to billing to set one up
                if not request.path.startswith('/finance/billing/'):
                    return redirect('saas_billing:gym_billing_dashboard')

        return self.get_response(request)

    def _is_exempt(self, path):
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False
