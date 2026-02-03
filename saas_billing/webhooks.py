import stripe
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .stripe_service import StripeService
from .models import GymSubscription, PaymentAttempt, Invoice
from .health import health_monitor
from .alerts import alert_service
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Endpoint to receive Stripe webhooks.
    """
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        service = StripeService()
        
        event = service.verify_webhook_signature(payload, sig_header)
        
        if not event:
            health_monitor.record_webhook_event('unknown', False, 'Invalid signature')
            return HttpResponse(status=400)
        
        event_type = event['type']
        
        try:
            # Handle the event
            if event_type == 'invoice.payment_succeeded':
                self.handle_invoice_paid(event['data']['object'])
                
            elif event_type == 'invoice.payment_failed':
                self.handle_invoice_failed(event['data']['object'])
                
            elif event_type == 'customer.subscription.deleted':
                self.handle_subscription_deleted(event['data']['object'])
                
            elif event_type == 'customer.subscription.updated':
                self.handle_subscription_updated(event['data']['object'])
            
            # Record successful webhook
            health_monitor.record_webhook_event(event_type, True)
            return HttpResponse(status=200)
            
        except Exception as e:
            logger.error(f"Webhook handler error: {e}")
            health_monitor.record_webhook_event(event_type, False, str(e))
            return HttpResponse(status=500)

    def handle_invoice_paid(self, invoice):
        """
        Handle successful payment.
        """
        try:
            # Find subscription by stripe ID
            sub_id = invoice.get('subscription')
            subscription = GymSubscription.objects.get(stripe_subscription_id=sub_id)
            
            # Update subscription status
            subscription.status = 'ACTIVE'
            subscription.current_period_end = datetime.fromtimestamp(invoice['lines']['data'][0]['period']['end']).date()
            subscription.suspension_date = None # Clear any suspension
            subscription.save()
            
            # TODO: Create local Invoice record if not exists
            # TODO: Send confirmation email
            
        except GymSubscription.DoesNotExist:
            logger.warning(f"Subscription {sub_id} not found for paid invoice {invoice['id']}")
            
    def handle_invoice_failed(self, invoice):
        """
        Handle failed payment.
        """
        try:
            sub_id = invoice.get('subscription')
            subscription = GymSubscription.objects.get(stripe_subscription_id=sub_id)
            
            # Update status to past due
            subscription.status = 'PAST_DUE'
            
            # Set suspension date if not already set (grace period starts now)
            if not subscription.suspension_date:
                subscription.suspension_date = date.today()
            
            subscription.save()
            
            # Create PaymentAttempt record
            attempt_count = PaymentAttempt.objects.filter(
                gym_subscription=subscription
            ).count() + 1
            
            PaymentAttempt.objects.create(
                invoice=Invoice.objects.filter(
                    gym=subscription.gym,
                    stripe_invoice_id=invoice['id']
                ).first() or Invoice.objects.filter(gym=subscription.gym).last(),
                gym_subscription=subscription,
                stripe_payment_intent_id=invoice.get('payment_intent', ''),
                amount=invoice.get('amount_due', 0) / 100,
                status='FAILED',
                failure_reason=invoice.get('last_payment_error', {}).get('message', 'Unknown error')
            )
            
            # Send alert to superadmin
            alert_service.alert_payment_failed(
                gym=subscription.gym,
                invoice=Invoice.objects.filter(gym=subscription.gym).last(),
                failure_reason=invoice.get('last_payment_error', {}).get('message', 'Unknown'),
                attempt_number=attempt_count
            )
            
            logger.warning(f"Payment failed for {subscription.gym.name}, attempt #{attempt_count}")
            
        except GymSubscription.DoesNotExist:
            logger.warning(f"Subscription {sub_id} not found for failed invoice {invoice['id']}")

    def handle_subscription_deleted(self, stripe_sub):
        """
        Handle cancellation.
        """
        try:
            subscription = GymSubscription.objects.get(stripe_subscription_id=stripe_sub['id'])
            subscription.status = 'CANCELLED'
            subscription.auto_renew = False
            subscription.save()
        except GymSubscription.DoesNotExist:
            pass

    def handle_subscription_updated(self, stripe_sub):
        """
        Handle updates (e.g. plan change).
        """
        # Logic to sync local state with Stripe state
        pass
