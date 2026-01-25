from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

from clients.models import Client, ClientMembership, ClientPaymentMethod
from finance.models import FinanceSettings, ClientPayment
from sales.models import Order, OrderItem
from organizations.models import Gym
from django.contrib.contenttypes.models import ContentType


@login_required
def advance_payment_view(request):
    """Vista para adelantar el pago de la siguiente cuota"""
    client = Client.objects.get(user=request.user)
    gym = client.gym
    
    # Verificar si está habilitado
    finance_settings = FinanceSettings.objects.filter(gym=gym).first()
    if not finance_settings or not finance_settings.allow_client_pay_next_fee:
        messages.error(request, 'Esta funcionalidad no está disponible.')
        return redirect('portal_dashboard')
    
    # Obtener membresía activa
    membership = ClientMembership.objects.filter(
        client=client,
        status='ACTIVE',
        is_recurring=True
    ).first()
    
    if not membership:
        messages.error(request, 'No tienes una membresía activa con pagos recurrentes.')
        return redirect('portal_dashboard')
    
    # Verificar método de pago
    has_payment_method = ClientPaymentMethod.objects.filter(
        client=client,
        is_default=True
    ).exists() or (client.stripe_customer_id and client.stripe_payment_method_id)
    
    context = {
        'membership': membership,
        'next_billing_date': membership.next_billing_date,
        'amount': membership.plan.price_monthly,
        'has_payment_method': has_payment_method,
    }
    
    return render(request, 'public_portal/advance_payment.html', context)


@login_required
@require_POST
@transaction.atomic
def process_advance_payment(request):
    """Procesar el pago adelantado de la siguiente cuota"""
    client = Client.objects.get(user=request.user)
    gym = client.gym
    
    # Verificar configuración
    finance_settings = FinanceSettings.objects.filter(gym=gym).first()
    if not finance_settings or not finance_settings.allow_client_pay_next_fee:
        return JsonResponse({'success': False, 'message': 'Funcionalidad no disponible'}, status=403)
    
    # Obtener membresía activa
    membership = ClientMembership.objects.filter(
        client=client,
        status='ACTIVE',
        is_recurring=True
    ).first()
    
    if not membership:
        return JsonResponse({'success': False, 'message': 'No tienes membresía activa'}, status=400)
    
    # Verificar método de pago
    if not client.stripe_customer_id or not client.stripe_payment_method_id:
        return JsonResponse({
            'success': False, 
            'message': 'Debes vincular un medio de pago antes de adelantar el cobro'
        }, status=400)
    
    # Intentar cobrar
    amount = membership.plan.price_monthly
    concept = f"Adelanto de cuota - {membership.plan.name}"
    
    try:
        # Importar función de cobro
        from finance.stripe_utils import charge_client
        
        # Use client's saved payment method
        payment_method_id = client.stripe_payment_method_id
        success, message = charge_client(client, float(amount), payment_method_id, concept)
        
        if success:
            # Crear registro de pago
            ClientPayment.objects.create(
                client=client,
                amount=amount,
                status='PAID',
                concept=concept,
                payment_method='Tarjeta guardada'
            )
            
            # Extender la membresía (adelantar fecha de fin)
            if membership.end_date:
                membership.end_date = membership.end_date + timedelta(days=30)
            
            # Actualizar siguiente fecha de cobro
            if membership.next_billing_date:
                membership.next_billing_date = membership.next_billing_date + timedelta(days=30)
            
            membership.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Pago procesado correctamente. Tu membresía ha sido extendida.',
                'new_end_date': membership.end_date.strftime('%d/%m/%Y') if membership.end_date else None,
                'new_billing_date': membership.next_billing_date.strftime('%d/%m/%Y') if membership.next_billing_date else None
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Error al procesar el pago: {message}'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error inesperado: {str(e)}'
        }, status=500)
