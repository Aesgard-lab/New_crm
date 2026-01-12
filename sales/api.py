from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from .models import Order, OrderItem, OrderPayment
from products.models import Product
from services.models import Service
from clients.models import Client
from finance.models import PaymentMethod
from accounts.decorators import require_gym_permission
from memberships.models import MembershipPlan
import json
import json
import datetime
from django.shortcuts import get_object_or_404
from django.db import transaction

@require_gym_permission('sales.view_sale')
def get_client_cards(request, client_id):
    """
    Returns list of saved cards for a client (Stripe + Redsys)
    """
    gym = request.gym
    client = get_object_or_404(Client, id=client_id, gym=gym)
    
    cards = []
    
    # 1. Stripe Cards
    from finance.stripe_utils import list_payment_methods
    try:
        stripe_cards = list_payment_methods(client)
        for card in stripe_cards:
            cards.append({
                'id': card.id,
                'provider': 'stripe',
                'brand': card.card.brand.upper(),
                'last4': card.card.last4,
                'display': f"💳 {card.card.brand.upper()} **** {card.card.last4}"
            })
    except Exception as e:
        print(f"Error fetching Stripe cards: {e}")
    
    # 2. Redsys Cards
    from finance.models import ClientRedsysToken
    for token in client.redsys_tokens.all():
        last4 = token.card_number[-4:] if token.card_number else '****'
        cards.append({
            'id': token.id,
            'provider': 'redsys',
            'brand': token.card_brand or 'CARD',
            'last4': last4,
            'display': f"💳 {token.card_brand or 'TARJETA'} {token.card_number or '**** ****'}"
        })
    
    return JsonResponse(cards, safe=False)

@require_gym_permission('sales.view_sale')
def order_detail_json(request, order_id):
    """
    Returns order details as JSON for inline expansion in client profile.
    """
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym)
    
    items = [{
        'id': item.id,
        'description': item.description,
        'quantity': item.quantity,
        'unit_price': float(item.unit_price),
        'discount': float(item.discount_amount),
        'subtotal': float(item.subtotal),
        'tax_rate': float(item.tax_rate)
    } for item in order.items.all()]
    
    payments = [{
        'method': payment.payment_method.name,
        'amount': float(payment.amount),
        'transaction_id': payment.transaction_id or ''
    } for payment in order.payments.all()]
    
    return JsonResponse({
        'id': order.id,
        'status': order.status,
        'status_display': order.get_status_display(),
        'total_amount': float(order.total_amount),
        'total_discount': float(order.total_discount),
        'created_at': order.created_at.isoformat(),
        'invoice_number': order.invoice_number or '',
        'items': items,
        'payments': payments
    })

@require_http_methods(["POST"])
@require_gym_permission('sales.delete_sale')
def order_cancel(request, order_id):
    """
    Cancels an order (sets status to CANCELLED).
    """
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym)
    
    if order.status == 'CANCELLED':
        return JsonResponse({'error': 'Esta venta ya está cancelada'}, status=400)
    
    order.status = 'CANCELLED'
    order.internal_notes += f"\n[Cancelado por {request.user.get_full_name() or request.user.username} el {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}]"
    order.save()
    
    return JsonResponse({'success': True, 'message': 'Venta cancelada correctamente'})

from decimal import Decimal

@require_gym_permission('sales.view_sale')
def search_products(request):
    query = request.GET.get('q', '').strip()
    gym = request.gym
    results = []

    # Search Products
    products = Product.objects.filter(gym=gym, is_active=True)
    if query:
        products = products.filter(name__icontains=query)
    
    for p in products[:10]:
        try:
            results.append({
                'type': 'product',
                'id': p.id,
                'name': p.name,
                'price': float(p.final_price),
                'image': p.image.url if p.image else None,
                'category': p.category.name if p.category else 'Sin Categoría'
            })
        except Exception as e:
            print(f"Error prod {p.id}: {e}")

    # Search Services
    services = Service.objects.filter(gym=gym, is_active=True)
    if query:
        services = services.filter(name__icontains=query)

    for s in services[:10]:
        try:
            results.append({
                'type': 'service',
                'id': s.id,
                'name': s.name,
                'price': float(s.final_price),
                'image': s.image.url if s.image else None,
                'category': s.category.name if s.category else 'Sin Categoría'
            })
        except Exception:
            pass

    # Search Memberships (Plans)
    plans = MembershipPlan.objects.filter(gym=gym, is_active=True)
    if query:
        plans = plans.filter(name__icontains=query)
    
    for plan in plans[:10]:
        try:
            results.append({
                'type': 'membership',
                'id': plan.id,
                'name': plan.name,
                'price': float(plan.final_price),
                'image': plan.image.url if plan.image else None,
                'category': 'Cuota / Plan'
            })
        except Exception:
            pass

    return JsonResponse({'results': results})

@require_gym_permission('sales.view_sale')
def search_clients(request):
    query = request.GET.get('q', '').strip()
    gym = request.gym
    
    clients = Client.objects.filter(gym=gym)
    if query:
        # Check if query is numeric for ID search
        if query.isdigit():
             clients = clients.filter(id=query) | clients.filter(dni__icontains=query)
        else:
             clients = clients.filter(first_name__icontains=query) | clients.filter(last_name__icontains=query) | clients.filter(dni__icontains=query)
    
    results = []
    for c in clients[:10]:
        results.append({
            'id': c.id,
            'text': str(c),
            'email': c.email
        })
    
    return JsonResponse({'results': results})

@transaction.atomic
@require_gym_permission('sales.add_sale')
@require_http_methods(["POST"])
def process_sale(request):
    try:
        data = json.loads(request.body)
        gym = request.gym
        user = request.user
        
        # 1. Helper: Validate Data
        client_id = data.get('client_id')
        items = data.get('items', [])
        # 'payments' list of { method_id: 1, amount: 50 }
        payments = data.get('payments', [])
        # Legacy support for single payment_method_id
        payment_method_id = data.get('payment_method_id') 

        action = data.get('action') 
        
        if not items:
            return JsonResponse({'error': 'El carrito está vacío'}, status=400)

        # 2. Create Order
        client = None
        if client_id:
            client = Client.objects.filter(gym=gym, pk=client_id).first()

        order = Order.objects.create(
            gym=gym,
            client=client,
            created_by=user,
            status='PAID', 
            total_amount=0 
        )

        total_amount = Decimal(0)
        total_discount = Decimal(0)

        # 3. Create Items
        for item in items:
            obj_id = item['id']
            obj_type = item['type']
            qty = int(item['qty'])
            
            discount_info = item.get('discount', {})
            disc_type = discount_info.get('type', 'fixed')
            disc_val = Decimal(str(discount_info.get('value', 0) or 0))

            if obj_type == 'product':
                obj = Product.objects.get(pk=obj_id, gym=gym)
            elif obj_type == 'service':
                obj = Service.objects.get(pk=obj_id, gym=gym)
            else:
                obj = MembershipPlan.objects.get(pk=obj_id, gym=gym)
            
            unit_price = obj.final_price 
            base_total = unit_price * qty
            
            item_discount = Decimal(0)
            if disc_val > 0:
                if disc_type == 'percent':
                    if disc_val > 100: disc_val = 100
                    item_discount = base_total * (disc_val / 100)
                else:
                    item_discount = disc_val
            
            if item_discount > base_total:
                item_discount = base_total
                
            final_subtotal = base_total - item_discount

            tax_rate = 0
            if obj.tax_rate:
                tax_rate = obj.tax_rate.rate_percent

            OrderItem.objects.create(
                order=order,
                content_object=obj,
                description=obj.name,
                quantity=qty,
                unit_price=unit_price,
                subtotal=final_subtotal,
                tax_rate=tax_rate,
                discount_amount=item_discount
            )
            total_amount += final_subtotal
            total_discount += item_discount

        # 4. Create Payments (handle mixed)
        total_paid = Decimal(0)
        
        # Process Payments
        total_paid = 0
        payments_valid = True
        
        for p in payments:
            method_id = p.get('method_id')
            amount = float(p.get('amount', 0))
            
            stripe_pm_id = p.get('stripe_payment_method_id') # Legacy/Stripe specific
            
            # New params for unified cards
            provider = p.get('provider') # 'stripe' or 'redsys'
            payment_token = p.get('payment_token') # The ID (pm_... or DB ID for Redsys)
            
            # Normalize inputs
            if stripe_pm_id and not provider:
                provider = 'stripe'
                payment_token = stripe_pm_id
            
            # Get Method Name (Cash, Card, etc)
            try:
                method = PaymentMethod.objects.get(id=method_id)
            except:
                # If using integration, maybe method is generic "Card"?
                # But frontend usually sends the generic PaymentMethod ID (e.g. "Tarjeta") selected.
                method = None
                
            transaction_id = None
            
            # Integrations
            if provider == 'stripe' and payment_token:
                 from finance.stripe_utils import charge_client
                 success, result = charge_client(client, amount, payment_token)
                 if success:
                     transaction_id = result # It's the PaymentIntent ID
                 else:
                     payments_valid = False
                     break
                     
            elif provider == 'redsys' and payment_token:
                 from finance.redsys_utils import get_redsys_client
                 from finance.models import ClientRedsysToken
                 
                 # Retrieve Token
                 try:
                     redsys_db_token = ClientRedsysToken.objects.get(id=payment_token, client=client)
                     redsys_client = get_redsys_client(gym)
                     
                     if not redsys_client:
                          raise Exception("Redsys not configured")
                          
                     # Generate unique order id for THIS charge
                     from finance.views_redsys import generate_order_id
                     order_id = generate_order_id()
                     
                     success, result = redsys_client.charge_request(order_id, amount, redsys_db_token.token, f"Order {order.id}")
                     
                     if success:
                         transaction_id = order_id # Or result.get('Ds_Order')
                     else:
                         # fail
                         raise Exception(result)
                         
                 except Exception as e:
                     print(f"Redsys Charge Error: {e}")
                     payments_valid = False
                     break
            
            OrderPayment.objects.create(
                order=order,
                payment_method=method,
                amount=amount,
                transaction_id=transaction_id
            )
            total_paid += amount
            
        if not payments_valid:
             order.status = 'CANCELLED' # Or failed
             order.save()
             return JsonResponse({'error': 'Error procesando el pago con tarjeta'}, status=400)
             
        # Check Total
        if total_paid >= total_amount:
            order.status = 'PAID'
        elif total_paid > 0:
            order.status = 'PARTIAL'
            
        order.save()
        
        return JsonResponse({'success': True, 'order_id': order.id})
    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, status=500)

def send_invoice_email(order, email):
    # Stub for sending email
    print(f"Sending Invoice {order.invoice_number} to {email}")
    pass

def send_ticket_email(order, email):
    # Stub for sending email
    print(f"Sending Ticket #{order.id} to {email}")
    pass
