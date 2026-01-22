from django.urls import path
from .webhooks import StripeWebhookView
from . import gym_views

app_name = 'saas_billing'

urlpatterns = [
    # Webhooks
    path('webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
    
    # Gym Facing Views
    path('dashboard/', gym_views.billing_dashboard, name='gym_billing_dashboard'),
    path('invoice/<int:invoice_id>/download/', gym_views.download_invoice, name='download_invoice'),
    path('portal-session/', gym_views.portal_session, name='portal_session'),
    
    # Payment Method Management
    path('create-setup-intent/', gym_views.create_setup_intent, name='create_setup_intent'),
    path('save-payment-method/', gym_views.save_payment_method, name='save_payment_method'),
    path('delete-payment-method/', gym_views.delete_payment_method, name='delete_payment_method'),
]
