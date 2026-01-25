"""
API Views for Client Billing (Mobile App).
View invoices and payment history.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from clients.models import Client
from sales.models import Order, OrderRefund

class BillingHistoryView(views.APIView):
    """
    List client orders/invoices.
    
    GET /api/billing/history/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        orders = Order.objects.filter(client=client).order_by('-created_at')
        
        data = []
        for order in orders:
            items = []
            for item in order.items.all():
                items.append({
                    'description': item.description,
                    'quantity': item.quantity,
                    'subtotal': str(item.subtotal)
                })
            
            # Incluir devoluciones asociadas a esta orden
            refunds = []
            for refund in order.refunds.filter(status='COMPLETED'):
                refunds.append({
                    'id': refund.id,
                    'date': refund.created_at.isoformat(),
                    'amount': str(refund.amount),
                    'reason': refund.reason,
                    'method': refund.refund_method_name or refund.get_gateway_display()
                })
            
            # Determinar si es un ticket de devolución (importe negativo)
            is_refund_ticket = float(order.total_amount) < 0
                
            data.append({
                'id': order.id,
                'date': order.created_at.isoformat(),
                'total_amount': str(order.total_amount),
                'total_refunded': str(order.total_refunded) if hasattr(order, 'total_refunded') else '0.00',
                'status': order.status, # PENDING, PAID, CANCELLED
                'is_refund': is_refund_ticket,  # True si es un ticket de devolución con importe negativo
                'invoice_number': order.invoice_number,
                'items': items,
                'refunds': refunds  # Lista de devoluciones parciales/totales
            })
            
        return Response({
            'count': len(data),
            'invoices': data
        })
