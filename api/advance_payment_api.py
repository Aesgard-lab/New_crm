from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from decimal import Decimal

from clients.models import Client, ClientPaymentMethod
from finance.models import FinanceSettings, ClientPayment
from finance.stripe_utils import charge_client
from sales.models import Order, OrderItem
from django.contrib.contenttypes.models import ContentType


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def advance_payment_info(request):
    """
    GET /api/v1/advance-payment/info/
    
    Returns information about the client's ability to advance payment,
    including membership details, next billing date, amount, and payment method status.
    """
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Cliente no encontrado'
        }, status=404)
    
    # Check if feature is enabled
    finance_settings = getattr(client.gym, 'finance_settings', None)
    if not finance_settings or not finance_settings.allow_client_pay_next_fee:
        return Response({
            'success': False,
            'enabled': False,
            'error': 'Esta funcionalidad no está habilitada para este gimnasio'
        }, status=403)
    
    # Get active recurring membership
    from clients.models import ClientMembership
    membership = ClientMembership.objects.filter(
        client=client,
        status='ACTIVE',
        is_recurring=True
    ).first()
    
    if not membership:
        return Response({
            'success': False,
            'enabled': True,
            'error': 'No tienes una membresía activa recurrente',
            'membership': None
        }, status=200)
    
    # Check payment method
    has_payment_method = False
    payment_method_details = {}
    
    if client.stripe_customer_id and client.stripe_payment_method_id:
        has_payment_method = True
        payment_method_details = {
            'type': 'stripe',
            'has_method': True
        }
    else:
        # Check for ClientPaymentMethod
        payment_method = ClientPaymentMethod.objects.filter(
            client=client,
            is_default=True
        ).first()
        if payment_method:
            has_payment_method = True
            payment_method_details = {
                'type': 'saved_card',
                'has_method': True,
                'last4': getattr(payment_method, 'last4', None)
            }
    
    # Calculate next billing info
    next_billing_date = membership.next_billing_date or membership.end_date
    amount = float(membership.plan.final_price) if membership.plan else 0.0
    
    return Response({
        'success': True,
        'enabled': True,
        'has_payment_method': has_payment_method,
        'payment_method': payment_method_details,
        'membership': {
            'id': membership.id,
            'plan_name': membership.plan.name if membership.plan else 'Sin plan',
            'status': membership.status,
            'is_recurring': membership.is_recurring,
            'start_date': membership.start_date.isoformat() if membership.start_date else None,
            'end_date': membership.end_date.isoformat() if membership.end_date else None,
            'next_billing_date': next_billing_date.isoformat() if next_billing_date else None,
            'amount': amount,
        }
    }, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def process_advance_payment(request):
    """
    POST /api/v1/advance-payment/process/
    
    Processes an advance payment for the client's next membership fee.
    Requires the client to have an active recurring membership and a valid payment method.
    """
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Cliente no encontrado'
        }, status=404)
    
    # Check if feature is enabled
    finance_settings = getattr(client.gym, 'finance_settings', None)
    if not finance_settings or not finance_settings.allow_client_pay_next_fee:
        return Response({
            'success': False,
            'error': 'Esta funcionalidad no está habilitada'
        }, status=403)
    
    # Get active recurring membership
    from clients.models import ClientMembership
    membership = ClientMembership.objects.filter(
        client=client,
        status='ACTIVE',
        is_recurring=True
    ).select_for_update().first()
    
    if not membership:
        return Response({
            'success': False,
            'error': 'No tienes una membresía activa recurrente para adelantar el pago'
        }, status=400)
    
    # Verify payment method
    if not (client.stripe_customer_id and client.stripe_payment_method_id):
        return Response({
            'success': False,
            'error': 'No tienes un método de pago vinculado. Por favor, agrega una tarjeta antes de continuar.'
        }, status=400)
    
    # Calculate amount and concept
    amount = membership.plan.final_price if membership.plan else Decimal('0.00')
    next_billing_date = membership.next_billing_date or membership.end_date
    concept = f"Adelanto de cuota - {membership.plan.name if membership.plan else 'Membresía'} - Fecha: {next_billing_date.strftime('%d/%m/%Y')}"
    
    # Process payment
    try:
        payment_method_id = client.stripe_payment_method_id
        success, message = charge_client(client, float(amount), payment_method_id, concept)
        
        if not success:
            return Response({
                'success': False,
                'error': f'Error al procesar el pago: {message}'
            }, status=400)
        
        # Create payment record
        ClientPayment.objects.create(
            client=client,
            gym=client.gym,
            amount=amount,
            status='PAID',
            concept=concept,
            payment_method='Tarjeta guardada',
            paid_at=timezone.now()
        )
        
        # Extend membership by 30 days
        if membership.end_date:
            membership.end_date += timedelta(days=30)
        
        if membership.next_billing_date:
            membership.next_billing_date += timedelta(days=30)
        
        membership.save()
        
        return Response({
            'success': True,
            'message': '✅ Pago procesado exitosamente. Tu membresía ha sido extendida.',
            'new_end_date': membership.end_date.isoformat() if membership.end_date else None,
            'new_billing_date': membership.next_billing_date.isoformat() if membership.next_billing_date else None,
            'amount_charged': float(amount),
            'payment_date': timezone.now().isoformat()
        }, status=200)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error inesperado al procesar el pago: {str(e)}'
        }, status=500)
