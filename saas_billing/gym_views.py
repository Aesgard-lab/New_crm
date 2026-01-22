from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import GymSubscription, Invoice, SubscriptionPlan
from .stripe_service import StripeService
import json

@login_required
def billing_dashboard(request):
    """
    Dashboard for gym administrators to view their subscription status.
    """
    gym_id = request.session.get('current_gym_id')
    if not gym_id:
        return redirect('backoffice:dashboard')
        
    try:
        subscription = GymSubscription.objects.select_related('plan').get(gym_id=gym_id)
        invoices = Invoice.objects.filter(gym_id=gym_id).order_by('-issue_date')[:5]
        
        # Get payment methods from Stripe
        payment_methods = []
        if subscription.stripe_customer_id:
            stripe_service = StripeService()
            payment_methods = stripe_service.get_payment_methods(subscription.stripe_customer_id)
            
    except GymSubscription.DoesNotExist:
        subscription = None
        invoices = []
        payment_methods = []
    
    # Get Stripe publishable key
    from .models import BillingConfig
    config = BillingConfig.get_config()
    stripe_publishable_key = config.stripe_publishable_key if config else ''
        
    context = {
        'subscription': subscription,
        'invoices': invoices,
        'payment_methods': payment_methods,
        'STRIPE_PUBLISHABLE_KEY': stripe_publishable_key,
        'debug_mode': request.session.get('is_god_mode', False)
    }
    return render(request, 'saas_billing/gym/dashboard.html', context)

@login_required
def download_invoice(request, invoice_id):
    """
    Download PDF for a specific invoice.
    """
    gym_id = request.session.get('current_gym_id')
    invoice = get_object_or_404(Invoice, id=invoice_id, gym_id=gym_id)
    
    if invoice.pdf_file:
        from django.http import FileResponse
        return FileResponse(invoice.pdf_file, as_attachment=True)
    
    messages.error(request, "El PDF de la factura no está disponible.")
    return redirect('saas_billing:gym_billing_dashboard')

@login_required
def portal_session(request):
    """
    Redirects to Stripe Customer Portal for managing payment methods.
    """
    gym_id = request.session.get('current_gym_id')
    try:
        subscription = GymSubscription.objects.get(gym_id=gym_id)
        if subscription.stripe_customer_id:
            import stripe
            # This should ideally move to StripeService
            stripe.api_key = StripeService().api_key
            
            session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=request.build_absolute_uri('/finance/billing/') # Adjust return URL as needed
            )
            return redirect(session.url)
    except Exception as e:
        messages.error(request, f"Error accediendo al portal de pagos: {str(e)}")
        
    return redirect('saas_billing:gym_billing_dashboard')


@login_required
@require_POST
def create_setup_intent(request):
    """
    Create a SetupIntent to add a payment method.
    """
    gym_id = request.session.get('current_gym_id')
    if not gym_id:
        return JsonResponse({'error': 'No gym selected'}, status=400)
    
    try:
        subscription = GymSubscription.objects.get(gym_id=gym_id)
        
        # Create Stripe customer if doesn't exist
        if not subscription.stripe_customer_id:
            from organizations.models import Gym
            gym = Gym.objects.get(id=gym_id)
            stripe_service = StripeService()
            customer = stripe_service.create_customer(gym)
            subscription.stripe_customer_id = customer.id
            subscription.save()
        
        # Create SetupIntent
        stripe_service = StripeService()
        setup_intent = stripe_service.create_setup_intent(subscription.stripe_customer_id)
        
        return JsonResponse({
            'clientSecret': setup_intent.client_secret,
            'customerId': subscription.stripe_customer_id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def save_payment_method(request):
    """
    Save a payment method after SetupIntent is confirmed.
    """
    gym_id = request.session.get('current_gym_id')
    if not gym_id:
        return JsonResponse({'error': 'No gym selected'}, status=400)
    
    try:
        data = json.loads(request.body)
        payment_method_id = data.get('payment_method_id')
        
        if not payment_method_id:
            return JsonResponse({'error': 'Missing payment_method_id'}, status=400)
        
        subscription = GymSubscription.objects.get(gym_id=gym_id)
        stripe_service = StripeService()
        
        # Attach payment method to customer
        stripe_service.attach_payment_method(payment_method_id, subscription.stripe_customer_id)
        
        # Get payment method details to update local record
        import stripe
        stripe.api_key = stripe_service.api_key
        pm = stripe.PaymentMethod.retrieve(payment_method_id)
        
        if pm.card:
            subscription.payment_method_last4 = pm.card.last4
            subscription.payment_method_brand = pm.card.brand
            subscription.save()
        
        messages.success(request, 'Método de pago guardado correctamente')
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def delete_payment_method(request):
    """
    Delete a payment method.
    """
    gym_id = request.session.get('current_gym_id')
    if not gym_id:
        return JsonResponse({'error': 'No gym selected'}, status=400)
    
    try:
        data = json.loads(request.body)
        payment_method_id = data.get('payment_method_id')
        
        if not payment_method_id:
            return JsonResponse({'error': 'Missing payment_method_id'}, status=400)
        
        stripe_service = StripeService()
        stripe_service.detach_payment_method(payment_method_id)
        
        # Clear local record if it was the saved one
        subscription = GymSubscription.objects.get(gym_id=gym_id)
        subscription.payment_method_last4 = ''
        subscription.payment_method_brand = ''
        subscription.save()
        
        messages.success(request, 'Método de pago eliminado correctamente')
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
