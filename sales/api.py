from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal
from datetime import timedelta, date
from django.template.loader import render_to_string
from django.conf import settings
from .models import Order, OrderItem, OrderPayment, OrderRefund
from products.models import Product
from services.models import Service
from clients.models import Client
from finance.models import PaymentMethod
from accounts.decorators import require_gym_permission
from memberships.models import MembershipPlan
import json
import datetime
from django.shortcuts import get_object_or_404

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
        'id': payment.id,
        'method_id': payment.payment_method.id, # Key for editing
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
        'internal_notes': order.internal_notes or '',
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
    
    # Refund Logic
    refund_notes = []
    
    # Check for refundable payments
    from finance.stripe_utils import refund_payment
    from finance.redsys_utils import get_redsys_client
    
    for payment in order.payments.all():
        if payment.transaction_id:
            # Try to identify provider. 
            # Heuristic: Stripe IDs usually start with pi_ or ch_. Redsys are usually numeric or short.
            # But we should probably store provider in OrderPayment? 
            # Current OrderPayment model doesn't have provider field, just payment_method relation.
            # Let's check the payment method name or infer from ID.
            
            # Stripe
            if payment.transaction_id.startswith('pi_') or payment.transaction_id.startswith('ch_'):
                success, msg = refund_payment(payment.transaction_id, amount_eur=float(payment.amount), gym=gym)
                if success:
                    refund_notes.append(f"Reembolso Stripe exitoso ({payment.amount}€)")
                else:
                    refund_notes.append(f"Error Reembolso Stripe: {msg}")
            
            # Redsys (If we have a numeric order ID as transaction_id)
            elif payment.transaction_id.isdigit(): # Redsys Order IDs are up to 12 digits
                 redsys = get_redsys_client(gym)
                 if redsys:
                     # Redsys Refund requires generating a NEW order ID for the refund transaction
                     from finance.views_redsys import generate_order_id
                     refund_order_id = generate_order_id()
                     success, msg = redsys.refund_request(refund_order_id, float(payment.amount), original_order_id=payment.transaction_id)
                     if success:
                         refund_notes.append(f"Reembolso Redsys exitoso ({payment.amount}€)")
                     else:
                         refund_notes.append(f"Error Reembolso Redsys: {msg}")
    
    order.status = 'CANCELLED'
    note = f"\n[Cancelado por {request.user.get_full_name() or request.user.username} el {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}]"
    if refund_notes:
        note += "\n" + "\n".join(refund_notes)
        
    order.internal_notes += note
    order.save()
    
    return JsonResponse({'success': True, 'message': 'Venta cancelada. ' + ', '.join(refund_notes)})


@require_http_methods(["POST", "DELETE"])
@require_gym_permission('sales.delete_sale')
def order_delete(request, order_id):
    """
    Elimina definitivamente una orden/ticket.
    Solo disponible para usuarios con permiso delete_sale.
    """
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym)
    
    # Guardar información para el log antes de eliminar
    client_name = f"{order.client.first_name} {order.client.last_name}".strip() if order.client else 'Sin cliente'
    order_info = f"Ticket #{order.id} - Cliente: {client_name} - Total: {order.total_amount}€"
    
    # No permitir eliminar si tiene pagos con transacciones externas activas
    has_external_payments = order.payments.filter(
        transaction_id__isnull=False
    ).exclude(transaction_id='').exists()
    
    if has_external_payments and order.status == 'PAID':
        return JsonResponse({
            'error': 'No se puede eliminar un ticket con pagos externos procesados. Usa la opción de devolución primero.'
        }, status=400)
    
    try:
        order.delete()
        return JsonResponse({
            'success': True, 
            'message': f'Ticket eliminado correctamente: {order_info}'
        })
    except Exception as e:
        return JsonResponse({
            'error': f'Error al eliminar: {str(e)}'
        }, status=500)


# ============================================
# REFUND ENDPOINTS (Devoluciones)
# ============================================

@require_http_methods(["GET"])
@require_gym_permission('sales.view_sale')
def order_refund_info(request, order_id):
    """
    Obtiene información para el modal de devolución.
    Incluye pagos con cantidades devolvibles y métodos de pago del gimnasio.
    """
    from finance.models import PaymentMethod
    
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym)
    
    # Métodos de pago del gimnasio (para devoluciones manuales)
    gym_payment_methods = [{
        'id': m.id,
        'name': m.name,
        'gateway': m.gateway
    } for m in PaymentMethod.objects.filter(gym=gym, is_active=True).order_by('display_order', 'name')]
    
    # Pagos con montos devolvibles
    payments_info = []
    for payment in order.payments.all():
        refundable = float(payment.refundable_amount)
        gateway = 'NONE'
        
        # Detectar gateway
        if payment.transaction_id:
            if payment.transaction_id.startswith('pi_') or payment.transaction_id.startswith('ch_'):
                gateway = 'STRIPE'
            elif payment.transaction_id.isdigit():
                gateway = 'REDSYS'
        
        payments_info.append({
            'id': payment.id,
            'method_name': payment.payment_method.name,
            'amount': float(payment.amount),
            'refundable_amount': refundable,
            'transaction_id': payment.transaction_id or '',
            'gateway': gateway,
            'can_auto_refund': gateway in ['STRIPE', 'REDSYS'] and refundable > 0
        })
    
    # Historial de devoluciones
    refunds_history = [{
        'id': r.id,
        'amount': float(r.amount),
        'reason': r.reason,
        'notes': r.notes,
        'status': r.status,
        'status_display': r.get_status_display(),
        'gateway': r.gateway,
        'gateway_display': r.get_gateway_display(),
        'refund_method_name': r.refund_method_name or (r.get_gateway_display() if r.gateway != 'NONE' else ''),
        'created_at': r.created_at.isoformat(),
        'created_by': r.created_by.get_full_name() or r.created_by.username
    } for r in order.refunds.all().select_related('created_by')]
    
    return JsonResponse({
        'order_id': order.id,
        'total_amount': float(order.total_amount),
        'total_refunded': float(order.total_refunded),
        'refundable_amount': float(order.refundable_amount),
        'is_fully_refunded': order.is_fully_refunded,
        'status': order.status,
        'payments': payments_info,
        'refunds_history': refunds_history,
        'gym_payment_methods': gym_payment_methods
    })


@require_http_methods(["POST"])
@require_gym_permission('sales.change_sale')
def order_process_refund(request, order_id):
    """
    Procesa una devolución parcial o total.
    
    Body JSON:
    {
        "amount": 25.50,  // Cantidad a devolver
        "reason": "Producto defectuoso",
        "payment_id": 123,  // Opcional: pago específico a devolver
        "auto_refund": true  // Si intentar devolución automática por pasarela
    }
    """
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    amount = Decimal(str(data.get('amount', 0)))
    reason = data.get('reason', '')
    notes = data.get('notes', '')  # Notas adicionales
    payment_id = data.get('payment_id')
    refund_method_id = data.get('refund_method_id')  # Método de devolución seleccionado
    auto_refund = data.get('auto_refund', False)
    accounting_mode = data.get('accounting_mode', 'negative')  # 'negative' or 'record_only'
    
    # Validaciones
    if amount <= 0:
        return JsonResponse({'error': 'La cantidad debe ser mayor a 0'}, status=400)
    
    if amount > order.refundable_amount:
        return JsonResponse({
            'error': f'La cantidad máxima devolvible es {order.refundable_amount}€'
        }, status=400)
    
    # Si se especifica un pago
    payment = None
    if payment_id:
        payment = order.payments.filter(id=payment_id).first()
        if not payment:
            return JsonResponse({'error': 'Pago no encontrado'}, status=400)
        if amount > payment.refundable_amount:
            return JsonResponse({
                'error': f'La cantidad máxima devolvible de este pago es {payment.refundable_amount}€'
            }, status=400)
    
    # Crear registro de devolución
    refund = OrderRefund.objects.create(
        order=order,
        payment=payment,
        amount=amount,
        reason=reason,
        notes=notes,
        status='PENDING',
        created_by=request.user
    )
    
    gateway_result = None
    
    # Intentar devolución automática si se solicita
    if auto_refund and payment and payment.transaction_id:
        gateway_result = _process_gateway_refund(payment, amount, gym, refund)
    elif auto_refund and not payment:
        # Buscar el primer pago con transacción que pueda cubrir el monto
        for p in order.payments.all():
            if p.transaction_id and p.refundable_amount >= amount:
                gateway_result = _process_gateway_refund(p, amount, gym, refund)
                refund.payment = p
                refund.save(update_fields=['payment'])
                break
    
    # Si no hubo intento de gateway o fue manual, marcar como completado
    if not auto_refund or refund.gateway == 'NONE':
        refund.status = 'COMPLETED'
        refund.gateway = 'NONE'
        refund.save()
    
    # Actualizar total devuelto de la orden
    order.update_refund_total()
    
    # Registrar en notas
    note = f"\n[Devolución de {amount}€ por {request.user.get_full_name() or request.user.username} - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}]"
    if reason:
        note += f"\nMotivo: {reason}"
    if notes:
        note += f"\nNotas: {notes}"
    
    # Registrar método de devolución
    if refund.gateway != 'NONE':
        note += f"\nMétodo: {refund.get_gateway_display()}"
    elif refund_method_id:
        from finance.models import PaymentMethod
        refund_method = PaymentMethod.objects.filter(id=refund_method_id).first()
        if refund_method:
            note += f"\nMétodo: {refund_method.name}"
            refund.refund_method_name = refund_method.name  # Guardar referencia
            refund.save(update_fields=['refund_method_name'])
    
    if gateway_result:
        note += f"\n{gateway_result}"
    order.internal_notes += note
    order.save(update_fields=['internal_notes'])
    
    # Si accounting_mode es 'negative', crear una orden de venta con importe negativo
    negative_order = None
    if accounting_mode == 'negative':
        # Obtener el método de pago para el cobro negativo
        refund_payment_method = None
        if refund_method_id:
            from finance.models import PaymentMethod
            refund_payment_method = PaymentMethod.objects.filter(id=refund_method_id, gym=gym).first()
        elif payment:
            refund_payment_method = payment.payment_method
        else:
            # Usar el método del primer pago de la orden original
            first_payment = order.payments.first()
            if first_payment:
                refund_payment_method = first_payment.payment_method
        
        # Crear orden negativa (devolución contable)
        negative_order = Order.objects.create(
            gym=gym,
            client=order.client,
            status='PAID',
            total_amount=-amount,  # Importe NEGATIVO
            discount_amount=Decimal('0'),
            internal_notes=f"Devolución del Ticket #{order.id} - {reason or 'Sin motivo'}\nRef. Devolución #{refund.id}",
            created_by=request.user
        )
        
        # Crear el item negativo
        OrderItem.objects.create(
            order=negative_order,
            description=f"Devolución - Ticket #{order.id}",
            quantity=1,
            unit_price=-amount,
            tax_rate=Decimal('0')  # La devolución no genera impuesto adicional
        )
        
        # Crear el pago negativo si hay método
        if refund_payment_method:
            OrderPayment.objects.create(
                order=negative_order,
                payment_method=refund_payment_method,
                amount=-amount
            )
        
        # Vincular la orden negativa a la devolución
        refund.negative_order = negative_order
        refund.save(update_fields=['negative_order'])
    
    return JsonResponse({
        'success': True,
        'refund_id': refund.id,
        'status': refund.status,
        'gateway_result': gateway_result,
        'new_total_refunded': float(order.total_refunded),
        'new_refundable_amount': float(order.refundable_amount),
        'negative_order_id': negative_order.id if negative_order else None,
        'accounting_mode': accounting_mode
    })


def _process_gateway_refund(payment, amount, gym, refund):
    """
    Procesa la devolución a través de la pasarela de pago.
    Retorna mensaje de resultado.
    """
    transaction_id = payment.transaction_id
    amount_float = float(amount)
    
    # Stripe
    if transaction_id.startswith('pi_') or transaction_id.startswith('ch_'):
        from finance.stripe_utils import refund_payment
        success, result = refund_payment(transaction_id, amount_eur=amount_float, gym=gym)
        
        refund.gateway = 'STRIPE'
        if success:
            refund.status = 'COMPLETED'
            refund.gateway_refund_id = result
            refund.save()
            return f"Reembolso Stripe exitoso (ID: {result})"
        else:
            refund.status = 'FAILED'
            refund.error_message = result
            refund.save()
            return f"Error Stripe: {result}"
    
    # Redsys
    elif transaction_id.isdigit():
        from finance.redsys_utils import get_redsys_client
        from finance.views_redsys import generate_order_id
        
        redsys = get_redsys_client(gym)
        if redsys:
            refund_order_id = generate_order_id()
            success, result = redsys.refund_request(
                refund_order_id, 
                amount_float, 
                original_order_id=transaction_id
            )
            
            refund.gateway = 'REDSYS'
            if success:
                refund.status = 'COMPLETED'
                refund.gateway_refund_id = refund_order_id
                refund.save()
                return f"Reembolso Redsys exitoso (ID: {refund_order_id})"
            else:
                refund.status = 'FAILED'
                refund.error_message = str(result)
                refund.save()
                return f"Error Redsys: {result}"
        else:
            refund.status = 'FAILED'
            refund.error_message = "Redsys no configurado"
            refund.save()
            return "Error: Redsys no configurado para este gimnasio"
    
    return None


@require_http_methods(["POST"])
@require_gym_permission('sales.change_sale')
def order_refund_retry(request, order_id, refund_id):
    """
    Reintenta una devolución fallida.
    """
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym)
    refund = get_object_or_404(OrderRefund, id=refund_id, order=order)
    
    if refund.status != 'FAILED':
        return JsonResponse({'error': 'Solo se pueden reintentar devoluciones fallidas'}, status=400)
    
    if not refund.payment or not refund.payment.transaction_id:
        return JsonResponse({'error': 'Esta devolución no tiene pago asociado para reintentar'}, status=400)
    
    # Reintentar
    refund.status = 'PENDING'
    refund.error_message = ''
    refund.save()
    
    result = _process_gateway_refund(refund.payment, refund.amount, gym, refund)
    
    if refund.status == 'COMPLETED':
        order.update_refund_total()
    
    return JsonResponse({
        'success': refund.status == 'COMPLETED',
        'status': refund.status,
        'message': result
    })



@require_gym_permission('sales.change_sale')
def order_update(request, order_id):
    """
    Updates an order's date, time, internal notes, and payment methods.
    """
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym)
    
    try:
        data = json.loads(request.body)
        
        # Update date/time if provided
        if data.get('date') and data.get('time'):
            from datetime import datetime as dt
            new_datetime = dt.strptime(f"{data['date']} {data['time']}", "%Y-%m-%d %H:%M")
            order.created_at = new_datetime
        
        # Update internal notes
        if 'internal_notes' in data:
            order.internal_notes = data['internal_notes']
            
        # Update Payments (Record keeping only)
        if 'payments' in data and isinstance(data['payments'], list):
            # This replaces existing payment records with new ones
            # WARNING: This does NOT refund or charge cards. It is for record correction.
            with transaction.atomic():
                order.payments.all().delete()
                for p_data in data['payments']:
                    method_id = p_data.get('method_id') or p_data.get('id') # Handle both formats if needed
                    amount = float(p_data.get('amount', 0))
                    if amount > 0:
                         method = PaymentMethod.objects.get(id=method_id)
                         OrderPayment.objects.create(
                             order=order,
                             payment_method=method,
                             amount=amount,
                             transaction_id=p_data.get('transaction_id', '')
                         )
        
        order.save()
        return JsonResponse({'success': True, 'message': 'Venta actualizada'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["POST"])
@require_gym_permission('sales.change_sale')
def order_generate_invoice(request, order_id):
    """
    Generates an invoice number if missing and sends email.
    """
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not order.invoice_number:
            # Simple sequential generation. 
            # Ideally this should be more robust (Year-Sequence).
            # For now: INV-{Year}-{Order_ID}
            year = datetime.datetime.now().year
            # Check last invoice number for this gym/year to increment?
            # Or just use ID based unique
            order.invoice_number = f"INV-{year}-{order.id:06d}"
            order.save()
            
        # Send Email
        if email:
             # Reuse ticket template or specialized invoice template
             send_invoice_email(order, email)
             msg = f"Factura {order.invoice_number} generada y enviada a {email}"
        else:
             msg = f"Factura {order.invoice_number} generada"

        return JsonResponse({'success': True, 'message': msg, 'invoice_number': order.invoice_number})
    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["POST"])
@require_gym_permission('sales.view_sale')
def order_send_ticket(request, order_id):
    """
    Sends ticket/receipt via email to client.
    Uses the unified email service.
    """
    from core.email_service import send_email, NoEmailConfigurationError, EmailLimitExceededError
    
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({'error': 'Email requerido'}, status=400)
        
        # Render email template
        html_content = render_to_string('emails/ticket_receipt.html', {
            'order': order,
            'gym': gym,
            'items': order.items.all(),
            'payments': order.payments.all()
        })
        
        send_email(
            gym=gym,
            to=email,
            subject=f'Tu ticket de compra - {gym.name} #{order.id}',
            body=f'Gracias por tu compra en {gym.name}. Adjuntamos tu ticket.',
            html_body=html_content,
        )
        
        return JsonResponse({'success': True, 'message': f'Ticket enviado a {email}'})
    except (NoEmailConfigurationError, EmailLimitExceededError) as e:
        return JsonResponse({'error': f'No se puede enviar email: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

from decimal import Decimal

@require_gym_permission('sales.view_sale')
def search_products(request):
    query = request.GET.get('q', '').strip()
    gym = request.gym
    results = []

    # Search Products - Incluye búsqueda por código de barras y SKU
    products = Product.objects.filter(gym=gym, is_active=True)
    if query:
        # Búsqueda por barcode exacto (escaneo)
        barcode_match = products.filter(barcode=query).first()
        if barcode_match:
            # Si hay coincidencia exacta por barcode, retornar solo ese producto
            return JsonResponse({'results': [{
                'type': 'product',
                'id': barcode_match.id,
                'name': barcode_match.name,
                'price': float(barcode_match.final_price),
                'image': barcode_match.image.url if barcode_match.image else None,
                'category': barcode_match.category.name if barcode_match.category else 'Sin Categoría',
                'barcode': barcode_match.barcode,
                'sku': barcode_match.sku,
                'exact_match': True
            }]})
        
        # Búsqueda por SKU exacto
        sku_match = products.filter(sku__iexact=query).first()
        if sku_match:
            return JsonResponse({'results': [{
                'type': 'product',
                'id': sku_match.id,
                'name': sku_match.name,
                'price': float(sku_match.final_price),
                'image': sku_match.image.url if sku_match.image else None,
                'category': sku_match.category.name if sku_match.category else 'Sin Categoría',
                'barcode': sku_match.barcode,
                'sku': sku_match.sku,
                'exact_match': True
            }]})
        
        # Búsqueda por nombre (parcial)
        from django.db.models import Q
        products = products.filter(
            Q(name__icontains=query) |
            Q(barcode__icontains=query) |
            Q(sku__icontains=query)
        )
    
    for p in products[:10]:
        try:
            results.append({
                'type': 'product',
                'id': p.id,
                'name': p.name,
                'price': float(p.final_price),
                'image': p.image.url if p.image else None,
                'category': p.category.name if p.category else 'Sin Categoría',
                'barcode': p.barcode or '',
                'sku': p.sku or ''
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
    client_id = request.GET.get('id')  # Direct ID lookup
    gym = request.gym
    
    clients = Client.objects.filter(gym=gym)
    
    # Direct ID lookup takes priority
    if client_id:
        clients = clients.filter(id=client_id)
    elif query:
        # Check if query is numeric for ID search
        if query.isdigit():
             clients = clients.filter(id=query) | clients.filter(dni__icontains=query)
        else:
             clients = clients.filter(first_name__icontains=query) | clients.filter(last_name__icontains=query) | clients.filter(dni__icontains=query)
    else:
        # Sin query: mostrar todos los clientes ordenados alfabéticamente
        clients = clients.order_by('first_name', 'last_name')
    
    # Limitar resultados
    clients = clients[:20]
    
    results = []
    for c in clients:
        results.append({
            'id': c.id,
            'text': str(c),
            'email': c.email,
            'first_name': c.first_name,
            'last_name': c.last_name,
            'status': c.status
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
        
        # Deferred Payment Fields
        is_deferred = data.get('is_deferred', False)
        scheduled_payment_date = data.get('scheduled_payment_date')
        auto_charge = data.get('auto_charge', False)
        deferred_notes = data.get('deferred_notes', '')
        
        if not items:
            return JsonResponse({'error': 'El carrito está vacío'}, status=400)

        # 2. Create Order
        client = None
        if client_id:
            client = Client.objects.filter(gym=gym, pk=client_id).first()

        # Custom Date/Time
        created_at_val = None
        if data.get('date') and data.get('time'):
            try:
                from datetime import datetime as dt
                created_at_str = f"{data['date']} {data['time']}"
                created_at_val = dt.strptime(created_at_str, "%Y-%m-%d %H:%M")
            except ValueError:
                pass # Ignore invalid format, use auto_now_add logic (actually need to set explicit if we want to override)
        
        # Custom Staff
        sale_user = user
        if data.get('staff_id'):
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                sale_user = User.objects.get(id=data['staff_id'], gym_memberships__gym=gym)
            except User.DoesNotExist:
                pass

        # Determine initial status
        initial_status = 'DEFERRED' if is_deferred else 'PAID'
        
        order = Order.objects.create(
            gym=gym,
            client=client,
            created_by=sale_user,
            status=initial_status, 
            total_amount=0
        )
        
        # Handle deferred payment fields
        if is_deferred and scheduled_payment_date:
            try:
                order.scheduled_payment_date = datetime.datetime.strptime(scheduled_payment_date, '%Y-%m-%d').date()
            except:
                order.scheduled_payment_date = None
            order.auto_charge = auto_charge
            order.deferred_notes = deferred_notes
            order.save()
        
        if created_at_val:
            order.created_at = created_at_val
            order.save() # Needed because auto_now_add might have set it to now

        # Normalizar acumuladores monetarios a Decimal para evitar mezclas float/Decimal
        order.total_base = Decimal(0)
        order.total_tax = Decimal(0)


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

            # Calculate Base and Tax (Assuming tax-inclusive prices)
            # Base = Total / (1 + Rate)
            item_tax_rate_decimal = Decimal(0)
            if obj.tax_rate:
                item_tax_rate_decimal = obj.tax_rate.rate_percent / Decimal(100)
            
            # Prevent division by zero or weirdness
            item_base = final_subtotal / (Decimal(1) + item_tax_rate_decimal)
            item_tax = final_subtotal - item_base

            ct = ContentType.objects.get_for_model(obj)

            newItem = OrderItem.objects.create(
                order=order,
                content_type=ct,
                object_id=obj.id,
                description=obj.name,
                quantity=qty,
                unit_price=unit_price,
                subtotal=final_subtotal,
                tax_rate=obj.tax_rate.rate_percent if obj.tax_rate else 0,
                discount_amount=item_discount
            )
            
            total_amount += final_subtotal
            total_discount += item_discount
            
            # Update order totals (in-memory)
            order.total_base += item_base
            order.total_tax += item_tax

        # 4. Create Payments (handle mixed) - Skip for deferred orders
        total_paid = Decimal(0)
        
        # For deferred orders, skip payment processing
        if is_deferred:
            # No payments needed, just save the totals
            order.total_amount = total_amount
            order.total_discount = total_discount
            order.save()
            
            return JsonResponse({
                'success': True, 
                'order_id': order.id,
                'deferred': True,
                'message': f'Venta diferida guardada. Fecha de cobro: {scheduled_payment_date}'
            })
        
        # Process Payments (only for non-deferred orders)
        payments_valid = True
        
        for p in payments:
            method_id = p.get('method_id')
            amount = Decimal(str(p.get('amount', 0) or 0))
            
            stripe_pm_id = p.get('stripe_payment_method_id') # Legacy/Stripe specific
            
            # New params for unified cards
            provider = p.get('provider') # 'stripe' or 'redsys'
            payment_token = p.get('payment_token') # The ID (pm_... or DB ID for Redsys)
            
            # Normalize inputs
            if stripe_pm_id and not provider:
                provider = 'stripe'
                payment_token = stripe_pm_id
            
            # Get Method Name (Cash, Card, etc)
            # Get Method Name (Cash, Card, etc)
            try:
                method = PaymentMethod.objects.get(id=method_id)
            except:
                # If using integration, maybe method provided is invalid?
                # Try to find a generic "Card" method
                if provider: # stripe or redsys
                    method = PaymentMethod.objects.filter(name__icontains='tarjeta', gym=gym).first()
                    if not method:
                        method = PaymentMethod.objects.filter(name__icontains='stripe', gym=gym).first()
                    if not method:
                         # Fallback to ANY active method if we have no choice (better than crash?)
                         # Or create one?
                         method = PaymentMethod.objects.filter(gym=gym, is_active=True).exclude(name__icontains='efectivo').first()
                         if not method:
                             method = PaymentMethod.objects.filter(gym=gym, is_active=True).first()
                             
                if not method:
                     # Critical failure if we can't find a method
                     # But don't crash yet, let valid validation handle it or create dummy?
                     # We must have a method.
                     raise Exception("No se encontró un método de pago válido en la configuración")
                
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
            
        order.total_amount = total_amount
        order.total_discount = total_discount
        order.save()
        
        return JsonResponse({'success': True, 'order_id': order.id})
    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, status=500)

def send_invoice_email(order, email):
    """
    Generates PDF invoice and sends it via email.
    Uses the unified email service.
    """
    from core.email_service import send_email, NoEmailConfigurationError, EmailLimitExceededError
    
    try:
        # 1. Render HTML
        html_content = render_to_string('emails/invoice.html', {
            'order': order,
            'gym': order.gym,
            'items': order.items.all(),
            'payments': order.payments.all()
        })
        
        # 2. Send Email using unified service
        send_email(
            gym=order.gym,
            to=email,
            subject=f'Factura {order.invoice_number} - {order.gym.name}',
            body=f"Adjuntamos su factura {order.invoice_number}.\n\nGracias por su confianza.",
            html_body=html_content,
        )
        
        print(f"Invoice {order.invoice_number} sent to {email}")
    except (NoEmailConfigurationError, EmailLimitExceededError) as e:
        print(f"Email no enviado (configuración): {e}")
    except Exception as e:
        print(f"Error sending invoice email: {e}")


def send_ticket_email(order, email):
    # Stub for sending email
    print(f"Sending Ticket #{order.id} to {email}")
    pass

@require_gym_permission('sales.charge')
@require_POST
def subscription_charge(request, pk):
    """
    Attempts to charge a subscription (ClientMembership) using stored payment methods.
    SECURITY: Validates membership belongs to the authenticated user's gym.
    """
    try:
        from clients.models import ClientMembership
        from memberships.models import MembershipPlan
        
        # SECURITY FIX: Validate membership belongs to the current gym
        gym = request.gym
        membership = get_object_or_404(ClientMembership, pk=pk, client__gym=gym)
        client = membership.client

        import json
        
        # Parse Body if needed (Alpine fetch sends JSON often, but we used key-value before. Let's support both)
        data = {}
        if request.body:
             try:
                 data = json.loads(request.body)
             except:
                 pass
        
        # Allow custom amount from request, otherwise use membership price
        custom_amount = data.get('amount') or request.POST.get('amount')
        if custom_amount:
            amount = Decimal(str(custom_amount))
        else:
            amount = membership.price
        
        if amount <= 0:
             return JsonResponse({'error': 'El importe es 0, no se puede cobrar'}, status=400)
        
        explicit_method_id = request.POST.get('method_id') or data.get('method_id')

        # Anti-duplicado: evitar cobrar dos veces la misma cuota sin confirmación explícita
        from django.contrib.contenttypes.models import ContentType
        from sales.models import OrderItem
        force = request.GET.get('force') or data.get('force') or request.POST.get('force')
        recent_order_item = OrderItem.objects.filter(
            content_type=ContentType.objects.get_for_model(ClientMembership),
            object_id=membership.id,
            order__status__in=['PAID', 'PENDING']
        ).order_by('-order__created_at').first()
        if recent_order_item and not force:
            return JsonResponse({
                'duplicate': True,
                'warning': 'Ya existe un cobro reciente para esta cuota. Si continúas podrías duplicar la cuota.'
            }, status=409)

        # 1. Determine Payment Method & Token
        provider = None
        token = None
        method = None
        
        # A) Explicit Method Selection (Manual or Specific Auto)
        if explicit_method_id:
            method = get_object_or_404(PaymentMethod, pk=explicit_method_id, gym=gym)
            
            # Check if it's an auto method or manual
            # For now, we assume if it has a specific provider_code it might be auto, 
            # but usually manual methods are just "Cash", "Card (Physical)".
            # We can check name or provider_code.
            if method.name.lower() in ['stripe', 'redsys'] or (method.provider_code and method.provider_code in ['stripe', 'redsys']):
                 # It is an auto method, try to find token for it
                 pass # Fallthrough to auto logic but using this method
            else:
                 # It is a MANUAL method
                 provider = 'manual'
        
        # B) Auto-Detect (only if no manual provider selected)
        if not provider:
            # Priority: Stripe > Redsys > Fail
            if client.stripe_customer_id:
                provider = 'stripe'
                if client.stripe_customer_id.startswith('cus_test'): # TEST MODE
                     token = 'pm_card_test_success'
                else:
                     token = client.stripe_customer_id 
                # Find generic Stripe method if not set
                if not method:
                    method = PaymentMethod.objects.filter(gym=gym, name__icontains='Stripe').first()
                
            elif client.redsys_tokens.exists():
                provider = 'redsys'
                merchant_token = client.redsys_tokens.last()
                token = merchant_token.id 
                if not method:
                    method = PaymentMethod.objects.filter(gym=gym, name__icontains='Tarjeta').first()

        # Validation
        if provider != 'manual' and not provider:
             return JsonResponse({'error': 'El cliente no tiene tarjeta vinculada (Stripe/Redsys)', 'error_code': 'NO_CARD'}, status=400)
             
        if not method:
             # Fallback
             method = PaymentMethod.objects.filter(gym=gym, is_active=True).first()

        # 2. Create Order (Pending)
        order = Order.objects.create(
            gym=gym,
            client=client,
            status='PENDING',
            total_amount=amount,
            total_base=amount / Decimal(1.21), # Approx
            total_tax=amount - (amount / Decimal(1.21)),
            created_by=request.user if request.user.is_authenticated else None,
            internal_notes=f"Renovación: {membership.name}"
        )
        
        # Add Item
        OrderItem.objects.create(
            order=order,
            content_type=ContentType.objects.get_for_model(ClientMembership),
            object_id=membership.id,
            description=f"Cuota: {membership.name}",
            quantity=1,
            unit_price=amount,
            subtotal=amount
        )
        
        # 3. Attempt Charge
        success = False
        transaction_id = None
        error_msg = ""
        
        if provider == 'stripe':
             from finance.stripe_utils import charge_client
             # charge_client expects (client, amount, payment_method_id)
             # If using Customer ID, we might need a different call or ensure charge_client handles it.
             # Assuming charge_client handles it for now or we pass a source.
             # Let's try passing the customer_id as token
             s_success, s_res = charge_client(client, amount, token) 
             if s_success:
                 success = True
                 transaction_id = s_res
             else:
                 error_msg = str(s_res)
                 
        elif provider == 'redsys':
             from finance.redsys_utils import get_redsys_client
             from finance.models import ClientRedsysToken
             from finance.views_redsys import generate_order_id
             
             try:
                 r_token = ClientRedsysToken.objects.get(id=token)
                 r_client = get_redsys_client(gym)
                 order_code = generate_order_id()
                 r_success, r_res = r_client.charge_request(order_code, amount, r_token.token, f"Ord {order.id}")
                 
                 if r_success:
                     success = True
                     transaction_id = order_code
                 else:
                     error_msg = "Error Redsys"
             except Exception as e:
                 error_msg = str(e)

        elif provider == 'manual':
             success = True
             transaction_id = f"MANUAL-{request.user.id}-{date.today()}"
             # Check if Cash control is needed? 
             # For now, simple record. If is_cash, maybe we should open shift? 
             # We assume Shift is open or we just record it.
             pass
        
        # 4. Handle Result
        if success:
            # Payment Record
            OrderPayment.objects.create(
                order=order,
                payment_method=method,
                amount=amount,
                transaction_id=transaction_id
            )
            order.status = 'PAID'
            order.save()
            
            # Extend Membership
            # Look up plan by name to get frequency
            plan = MembershipPlan.objects.filter(gym=gym, name=membership.name).first()
            if plan:
                # Add frequency
                from dateutil.relativedelta import relativedelta
                if plan.frequency_unit == 'MONTH':
                    delta = relativedelta(months=plan.frequency_amount)
                elif plan.frequency_unit == 'YEAR':
                    delta = relativedelta(years=plan.frequency_amount)
                elif plan.frequency_unit == 'WEEK':
                    delta = relativedelta(weeks=plan.frequency_amount)
                elif plan.frequency_unit == 'DAY':
                     delta = timedelta(days=plan.frequency_amount)
                else:
                     delta = relativedelta(months=1)
            else:
                # Default 1 month
                from dateutil.relativedelta import relativedelta
                delta = relativedelta(months=1)
                
            # Update end_date
            if membership.end_date:
                # If expired long ago, maybe start from today? 
                # User said "cobros futuros" ... "fecha de vencimiento". 
                # Ideally we add to the existing end_date to keep the cycle.
                membership.end_date += delta
            else:
                membership.end_date = date.today() + delta
            
            # Reset failed attempts on success
            from django.utils import timezone
            membership.failed_charge_attempts = 0
            membership.last_charge_error = ''
            membership.last_charge_attempt = timezone.now()
            membership.save()
            
            return JsonResponse({'success': True, 'message': f'Cobrado Correctamente. Nueva fecha: {membership.end_date}'})
        else:
            # Failed - update tracking
            from django.utils import timezone
            membership.failed_charge_attempts += 1
            membership.last_charge_attempt = timezone.now()
            membership.last_charge_error = error_msg[:255] if error_msg else 'Error desconocido'
            membership.save()
            
            order.status = 'CANCELLED' # Or failed
            order.internal_notes += f" | Fallo cobro: {error_msg}"
            order.save()
            return JsonResponse({
                'error': f'Fallo en el cobro: {error_msg}', 
                'error_code': 'CHARGE_FAILED',
                'attempts': membership.failed_charge_attempts
            }, status=400)
            


    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@require_gym_permission('sales.change_sale')
def order_update_status(request, order_id):
    """
    Updates an order's status and other fields (amount, payment method, notes).
    """
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status', '').upper()
        
        if new_status not in ['PAID', 'PENDING', 'REFUNDED', 'CANCELLED']:
            return JsonResponse({'error': f'Estado inválido: {new_status}'}, status=400)
        
        old_status = order.status
        changes = []
        
        # Update status
        if old_status != new_status:
            order.status = new_status
            changes.append(f"Estado: {old_status} → {new_status}")
        
        # Update amount if provided
        if 'amount' in data:
            new_amount = float(data['amount'])
            if new_amount != order.total_amount:
                changes.append(f"Importe: {order.total_amount}€ → {new_amount}€")
                order.total_amount = new_amount
        
        # Update payment method if provided (update first payment)
        if 'payment_method_id' in data:
            from finance.models import PaymentMethod
            try:
                payment_method = PaymentMethod.objects.get(id=data['payment_method_id'], gym=gym)
                # Update the first payment or create one if doesn't exist
                if order.payments.exists():
                    first_payment = order.payments.first()
                    old_method = first_payment.payment_method.name
                    first_payment.payment_method = payment_method
                    first_payment.save()
                    changes.append(f"Método de pago: {old_method} → {payment_method.name}")
                else:
                    # Create a new payment record
                    from sales.models import OrderPayment
                    OrderPayment.objects.create(
                        order=order,
                        payment_method=payment_method,
                        amount=order.total_amount
                    )
                    changes.append(f"Método de pago agregado: {payment_method.name}")
            except PaymentMethod.DoesNotExist:
                return JsonResponse({'error': 'Método de pago no encontrado'}, status=400)
        
        # Update internal notes if provided
        if 'internal_notes' in data:
            new_notes = data['internal_notes']
            if new_notes:
                order.internal_notes = (order.internal_notes or '') + f" | {new_notes}"
        
        # Update date if provided
        if 'date' in data:
            from datetime import datetime as dt
            try:
                new_date = dt.strptime(data['date'], "%Y-%m-%d")
                # Keep the original time but change the date
                old_datetime = order.created_at
                new_datetime = new_date.replace(
                    hour=old_datetime.hour,
                    minute=old_datetime.minute,
                    second=old_datetime.second
                )
                changes.append(f"Fecha: {old_datetime.strftime('%d/%m/%Y')} → {new_date.strftime('%d/%m/%Y')}")
                order.created_at = new_datetime
            except ValueError:
                return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
                changes.append("Notas actualizadas")
        
        # Save all changes
        if changes:
            order.save()
            change_summary = " | ".join(changes)
        else:
            change_summary = "Sin cambios"
        
        return JsonResponse({
            'success': True, 
            'message': f'Operación actualizada: {change_summary}',
            'new_status': new_status
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_gym_permission('sales.charge')
@require_POST
def bulk_subscription_charge(request):
    """
    Attempts to charge multiple subscriptions (ClientMemberships) at once.
    Returns a summary of successful and failed charges.
    SECURITY: Requires gym permission and validates all memberships belong to gym.
    """
    try:
        from clients.models import ClientMembership
        from memberships.models import MembershipPlan
        from django.utils import timezone
        
        # SECURITY: gym is set from authenticated user's session
        gym = request.gym
        if not gym:
            return JsonResponse({'error': 'Acceso no autorizado'}, status=403)
        
        data = {}
        if request.body:
            try:
                data = json.loads(request.body)
            except:
                pass
        
        membership_ids = data.get('membership_ids', [])
        
        if not membership_ids:
            return JsonResponse({'error': 'No se proporcionaron membresías para cobrar'}, status=400)
        
        results = {
            'total': len(membership_ids),
            'success_count': 0,
            'failed_count': 0,
            'successful': [],
            'failed': []
        }
        
        for membership_id in membership_ids:
            try:
                membership = ClientMembership.objects.get(pk=membership_id, client__gym=gym)
                client = membership.client
                amount = membership.price
                
                if amount <= 0:
                    results['failed'].append({
                        'membership_id': membership_id,
                        'client_name': f"{client.first_name} {client.last_name}",
                        'reason': 'Importe es 0'
                    })
                    results['failed_count'] += 1
                    membership.failed_charge_attempts += 1
                    membership.last_charge_attempt = timezone.now()
                    membership.last_charge_error = 'Importe es 0'
                    membership.save()
                    continue
                
                # Determine payment method
                provider = None
                token = None
                method = None
                
                if client.stripe_customer_id:
                    provider = 'stripe'
                    if client.stripe_customer_id.startswith('cus_test'):
                        token = 'pm_card_test_success'
                    else:
                        token = client.stripe_customer_id
                    method = PaymentMethod.objects.filter(gym=gym, name__icontains='Stripe').first()
                elif client.redsys_tokens.exists():
                    provider = 'redsys'
                    merchant_token = client.redsys_tokens.last()
                    token = merchant_token.id
                    method = PaymentMethod.objects.filter(gym=gym, name__icontains='Tarjeta').first()
                
                if not provider:
                    results['failed'].append({
                        'membership_id': membership_id,
                        'client_name': f"{client.first_name} {client.last_name}",
                        'reason': 'Sin tarjeta vinculada'
                    })
                    results['failed_count'] += 1
                    membership.failed_charge_attempts += 1
                    membership.last_charge_attempt = timezone.now()
                    membership.last_charge_error = 'Sin tarjeta vinculada'
                    membership.save()
                    continue
                
                if not method:
                    method = PaymentMethod.objects.filter(gym=gym, is_active=True).first()
                
                # Create Order
                order = Order.objects.create(
                    gym=gym,
                    client=client,
                    status='PENDING',
                    total_amount=amount,
                    total_base=amount / Decimal(1.21),
                    total_tax=amount - (amount / Decimal(1.21)),
                    created_by=request.user if request.user.is_authenticated else None,
                    internal_notes=f"Cobro masivo - Renovación: {membership.name}"
                )
                
                from django.contrib.contenttypes.models import ContentType
                OrderItem.objects.create(
                    order=order,
                    content_type=ContentType.objects.get_for_model(ClientMembership),
                    object_id=membership.id,
                    description=f"Cuota: {membership.name}",
                    quantity=1,
                    unit_price=amount,
                    subtotal=amount
                )
                
                # Attempt charge
                success = False
                transaction_id = None
                error_msg = ""
                
                if provider == 'stripe':
                    from finance.stripe_utils import charge_client
                    s_success, s_res = charge_client(client, amount, token)
                    if s_success:
                        success = True
                        transaction_id = s_res
                    else:
                        error_msg = str(s_res)
                        
                elif provider == 'redsys':
                    from finance.redsys_utils import get_redsys_client
                    from finance.models import ClientRedsysToken
                    from finance.views_redsys import generate_order_id
                    
                    try:
                        r_token = ClientRedsysToken.objects.get(id=token)
                        r_client = get_redsys_client(gym)
                        order_code = generate_order_id()
                        r_success, r_res = r_client.charge_request(order_code, amount, r_token.token, f"Ord {order.id}")
                        
                        if r_success:
                            success = True
                            transaction_id = order_code
                        else:
                            error_msg = "Error Redsys"
                    except Exception as e:
                        error_msg = str(e)
                
                if success:
                    OrderPayment.objects.create(
                        order=order,
                        payment_method=method,
                        amount=amount,
                        transaction_id=transaction_id
                    )
                    order.status = 'PAID'
                    order.save()
                    
                    # Extend membership
                    plan = MembershipPlan.objects.filter(gym=gym, name=membership.name).first()
                    if plan:
                        from dateutil.relativedelta import relativedelta
                        if plan.frequency_unit == 'MONTH':
                            delta = relativedelta(months=plan.frequency_amount)
                        elif plan.frequency_unit == 'YEAR':
                            delta = relativedelta(years=plan.frequency_amount)
                        elif plan.frequency_unit == 'WEEK':
                            delta = relativedelta(weeks=plan.frequency_amount)
                        elif plan.frequency_unit == 'DAY':
                            delta = timedelta(days=plan.frequency_amount)
                        else:
                            delta = relativedelta(months=1)
                    else:
                        from dateutil.relativedelta import relativedelta
                        delta = relativedelta(months=1)
                    
                    if membership.end_date:
                        membership.end_date += delta
                    else:
                        membership.end_date = date.today() + delta
                    
                    # Reset failed attempts on success
                    membership.failed_charge_attempts = 0
                    membership.last_charge_error = ''
                    membership.last_charge_attempt = timezone.now()
                    membership.save()
                    
                    results['successful'].append({
                        'membership_id': membership_id,
                        'client_name': f"{client.first_name} {client.last_name}",
                        'new_end_date': str(membership.end_date)
                    })
                    results['success_count'] += 1
                else:
                    order.status = 'CANCELLED'
                    order.internal_notes += f" | Fallo cobro masivo: {error_msg}"
                    order.save()
                    
                    membership.failed_charge_attempts += 1
                    membership.last_charge_attempt = timezone.now()
                    membership.last_charge_error = error_msg[:255] if error_msg else 'Error desconocido'
                    membership.save()
                    
                    results['failed'].append({
                        'membership_id': membership_id,
                        'client_name': f"{client.first_name} {client.last_name}",
                        'reason': error_msg or 'Error desconocido',
                        'attempts': membership.failed_charge_attempts
                    })
                    results['failed_count'] += 1
                    
            except ClientMembership.DoesNotExist:
                results['failed'].append({
                    'membership_id': membership_id,
                    'client_name': 'Desconocido',
                    'reason': 'Membresía no encontrada'
                })
                results['failed_count'] += 1
            except Exception as e:
                results['failed'].append({
                    'membership_id': membership_id,
                    'client_name': 'Error',
                    'reason': str(e)
                })
                results['failed_count'] += 1
        
        return JsonResponse(results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


# ============================================
# Deferred Orders API
# ============================================

@require_http_methods(["POST"])
@require_gym_permission('sales.charge')
def deferred_order_charge(request, order_id):
    """
    Charge a deferred order. Attempts auto-charge if client has saved card,
    otherwise marks it as ready for manual payment in TPV.
    """
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym, status='DEFERRED')
    client = order.client
    
    if not client:
        return JsonResponse({'error': 'Esta venta no tiene cliente asociado'}, status=400)
    
    try:
        amount = order.total_amount
        
        # Try auto-charge if order has auto_charge enabled
        if order.auto_charge:
            # Attempt Stripe first
            if client.stripe_customer_id:
                from finance.stripe_utils import charge_client, list_payment_methods
                payment_methods = list_payment_methods(client)
                if payment_methods:
                    success, result = charge_client(client, amount, payment_methods[0].id)
                    if success:
                        # Create payment record
                        method = PaymentMethod.objects.filter(gym=gym, name__icontains='stripe').first()
                        if not method:
                            method = PaymentMethod.objects.filter(gym=gym, name__icontains='tarjeta').first()
                        if not method:
                            method = PaymentMethod.objects.filter(gym=gym, is_active=True).first()
                        
                        OrderPayment.objects.create(
                            order=order,
                            payment_method=method,
                            amount=amount,
                            transaction_id=result,
                            gateway_used='STRIPE'
                        )
                        order.status = 'PAID'
                        order.save()
                        return JsonResponse({'success': True, 'message': 'Cobro automático realizado correctamente (Stripe)'})
                    else:
                        return JsonResponse({'error': f'Error en cobro Stripe: {result}'}, status=400)
            
            # Try Redsys if Stripe failed/unavailable
            if client.redsys_tokens.exists():
                from finance.redsys_utils import get_redsys_client
                from finance.models import ClientRedsysToken
                from finance.views_redsys import generate_order_id
                
                redsys_token = client.redsys_tokens.first()
                redsys_client = get_redsys_client(gym)
                
                if redsys_client and redsys_token:
                    redsys_order_id = generate_order_id()
                    success, result = redsys_client.charge_request(
                        redsys_order_id, amount, redsys_token.token, f"Deferred Order {order.id}"
                    )
                    if success:
                        method = PaymentMethod.objects.filter(gym=gym, name__icontains='redsys').first()
                        if not method:
                            method = PaymentMethod.objects.filter(gym=gym, name__icontains='tarjeta').first()
                        if not method:
                            method = PaymentMethod.objects.filter(gym=gym, is_active=True).first()
                        
                        OrderPayment.objects.create(
                            order=order,
                            payment_method=method,
                            amount=amount,
                            transaction_id=redsys_order_id,
                            gateway_used='REDSYS'
                        )
                        order.status = 'PAID'
                        order.save()
                        return JsonResponse({'success': True, 'message': 'Cobro automático realizado correctamente (Redsys)'})
                    else:
                        return JsonResponse({'error': f'Error en cobro Redsys: {result}'}, status=400)
        
        # If no auto-charge or auto-charge failed, mark as PENDING for manual
        order.status = 'PENDING'
        order.save()
        return JsonResponse({
            'success': True, 
            'message': 'Venta marcada como pendiente. Complete el cobro manualmente.',
            'requires_manual': True,
            'redirect_url': f'/sales/pos/?order_id={order.id}'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@require_gym_permission('sales.change_sale')
def deferred_order_cancel(request, order_id):
    """
    Cancel a deferred order.
    """
    gym = request.gym
    order = get_object_or_404(Order, id=order_id, gym=gym, status='DEFERRED')
    
    try:
        order.status = 'CANCELLED'
        order.internal_notes += f" | Venta diferida cancelada el {date.today().strftime('%d/%m/%Y')}"
        order.save()
        
        return JsonResponse({'success': True, 'message': 'Venta diferida cancelada correctamente'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================
# Subscription Cancellation API
# ============================================

@require_http_methods(["POST"])
@require_gym_permission('sales.change_sale')
def subscription_cancel(request, pk):
    """
    Cancel a subscription (ClientMembership).
    
    Two modes:
    - skip_period: Only skip the next billing period (keeps membership active but extends date)
    - full_cancel: Cancel membership completely and deactivate client
    
    SECURITY: Validates membership belongs to the authenticated user's gym.
    """
    import json
    from clients.models import ClientMembership
    
    gym = request.gym
    membership = get_object_or_404(ClientMembership, pk=pk, client__gym=gym)
    client = membership.client
    
    try:
        data = json.loads(request.body) if request.body else {}
        cancel_type = data.get('cancel_type', '')
        
        if cancel_type not in ['skip_period', 'full_cancel']:
            return JsonResponse({'error': 'Tipo de cancelación inválido'}, status=400)
        
        if cancel_type == 'skip_period':
            # Skip only the next billing period
            # Extend the end_date by one billing cycle without charging
            from memberships.models import MembershipPlan
            from dateutil.relativedelta import relativedelta
            
            plan = MembershipPlan.objects.filter(gym=gym, name=membership.name).first()
            
            if plan:
                if plan.frequency_unit == 'MONTH':
                    delta = relativedelta(months=plan.frequency_amount)
                elif plan.frequency_unit == 'YEAR':
                    delta = relativedelta(years=plan.frequency_amount)
                elif plan.frequency_unit == 'WEEK':
                    delta = relativedelta(weeks=plan.frequency_amount)
                elif plan.frequency_unit == 'DAY':
                    delta = timedelta(days=plan.frequency_amount)
                else:
                    delta = relativedelta(months=1)
            else:
                # Default to 1 month if plan not found
                delta = relativedelta(months=1)
            
            # Extend end_date (skip period)
            if membership.end_date:
                membership.end_date += delta
            else:
                membership.end_date = date.today() + delta
            
            # Add note about skipped period
            if not membership.notes:
                membership.notes = ''
            membership.notes += f"\n[{date.today().strftime('%d/%m/%Y')}] Periodo saltado - próximo cobro: {membership.end_date.strftime('%d/%m/%Y')}"
            membership.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Próximo periodo cancelado. Nueva fecha de cobro: {membership.end_date.strftime("%d/%m/%Y")}',
                'new_end_date': str(membership.end_date)
            })
            
        elif cancel_type == 'full_cancel':
            # Full cancellation - deactivate membership and optionally deactivate client
            
            # Mark membership as inactive
            membership.is_active = False
            membership.end_date = date.today()
            if not membership.notes:
                membership.notes = ''
            membership.notes += f"\n[{date.today().strftime('%d/%m/%Y')}] Membresía CANCELADA y cliente dado de baja"
            membership.save()
            
            # Deactivate the client
            client.is_active = False
            if not client.notes:
                client.notes = ''
            client.notes += f"\n[{date.today().strftime('%d/%m/%Y')}] Dado de baja - Membresía cancelada: {membership.name}"
            client.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Membresía "{membership.name}" cancelada y cliente dado de baja',
                'membership_deactivated': True,
                'client_deactivated': True
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)