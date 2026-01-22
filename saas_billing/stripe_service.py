import stripe
from django.conf import settings
from .models import BillingConfig, SubscriptionPlan, GymSubscription, PaymentAttempt
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class StripeService:
    """
    Service class to handle all Stripe interactions.
    Uses keys from BillingConfig singleton.
    """
    
    def __init__(self):
        config = BillingConfig.get_config()
        # Decrypt key in production! Here assuming plain for MVP or implementing decryption logic
        self.api_key = config.stripe_secret_key
        stripe.api_key = self.api_key
        
    def create_customer(self, gym):
        """
        Create a Stripe customer for a gym.
        """
        try:
            customer = stripe.Customer.create(
                email=gym.email,
                name=gym.name,
                metadata={
                    'gym_id': gym.id,
                    'environment': settings.ENVIRONMENT
                }
            )
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Customer Creation Error: {e}")
            raise e

    def create_subscription(self, customer_id, price_id):
        """
        Create a subscription for a customer.
        """
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent'],
            )
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Subscription Creation Error: {e}")
            raise e
            
    def get_checkout_session(self, price_id, gym_id, success_url, cancel_url):
        """
        Create a checkout session for setting up subscription.
        """
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=str(gym_id),
                metadata={'gym_id': gym_id}
            )
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Checkout Session Error: {e}")
            raise e

    def sync_plans(self):
        """
        Sync local SubscriptionPlans with Stripe Products/Prices.
        Run this when plans change.
        """
        plans = SubscriptionPlan.objects.all()
        
        for plan in plans:
            try:
                # 1. Create/Update Product
                if not plan.stripe_product_id:
                    product = stripe.Product.create(
                        name=plan.name,
                        description=plan.description or "SaaS Subscription",
                        metadata={'plan_id': plan.id}
                    )
                    plan.stripe_product_id = product.id
                    plan.save()
                else:
                    stripe.Product.modify(
                        plan.stripe_product_id,
                        name=plan.name
                    )
                
                # 2. Create/Update Monthly Price
                if not plan.stripe_price_monthly_id:
                    price = stripe.Price.create(
                        unit_amount=int(plan.price_monthly * 100),
                        currency='eur',
                        recurring={'interval': 'month'},
                        product=plan.stripe_product_id
                    )
                    plan.stripe_price_monthly_id = price.id
                    plan.save()
                    
                # 3. Create/Update Yearly Price (if exists)
                if plan.price_yearly and not plan.stripe_price_yearly_id:
                    price = stripe.Price.create(
                        unit_amount=int(plan.price_yearly * 100),
                        currency='eur',
                        recurring={'interval': 'year'},
                        product=plan.stripe_product_id
                    )
                    plan.stripe_price_yearly_id = price.id
                    plan.save()
                    
            except stripe.error.StripeError as e:
                logger.error(f"Error syncing plan {plan.name}: {e}")
                
    def verify_webhook_signature(self, payload, sig_header):
        """
        Verify Stripe webhook signature.
        """
        config = BillingConfig.get_config()
        endpoint_secret = config.stripe_webhook_secret
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            return event
        except ValueError as e:
            return None
        except stripe.error.SignatureVerificationError as e:
            return None
    
    def create_setup_intent(self, customer_id):
        """
        Create a SetupIntent for adding a payment method without charging.
        """
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=['card'],
            )
            return setup_intent
        except stripe.error.StripeError as e:
            logger.error(f"Stripe SetupIntent Creation Error: {e}")
            raise e
    
    def attach_payment_method(self, payment_method_id, customer_id):
        """
        Attach a payment method to a customer and set it as default.
        """
        try:
            # Attach the payment method to the customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id,
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id
                }
            )
            
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Attach Payment Method Error: {e}")
            raise e
    
    def get_payment_methods(self, customer_id):
        """
        Get all payment methods for a customer.
        """
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            return payment_methods.data
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Get Payment Methods Error: {e}")
            return []
    
    def detach_payment_method(self, payment_method_id):
        """
        Detach a payment method from a customer.
        """
        try:
            stripe.PaymentMethod.detach(payment_method_id)
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Detach Payment Method Error: {e}")
            raise e
