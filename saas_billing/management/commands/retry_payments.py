from django.core.management.base import BaseCommand
from saas_billing.models import PaymentAttempt, Invoice, GymSubscription
from saas_billing.stripe_service import StripeService
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Retries failed payments that are due for retry'

    def handle(self, *args, **options):
        now = timezone.now()
        attempts = PaymentAttempt.objects.filter(
            status='RETRYING',
            next_retry__lte=now
        )
        
        self.stdout.write(f"Found {attempts.count()} payments to retry")
        
        service = StripeService()
        
        for attempt in attempts:
            try:
                # Logic to retry payment intent in Stripe
                # This depends on how the payment failed (card declined, authentication required, etc.)
                # For off-session payments, we might need to send an email instead of auto-retrying if it required 3DS
                
                # Placeholder for retry logic
                self.stdout.write(f"Retrying payment for invoice {attempt.invoice.invoice_number}...")
                
                # Update next retry or mark failed
                # attempt.next_retry = ...
                # attempt.save()
                
                pass
            except Exception as e:
                logger.error(f"Error retrying payment {attempt.id}: {e}")
