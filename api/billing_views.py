"""
API Views for Client Billing (Mobile App).
View invoices and payment history.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from clients.models import Client
from sales.models import Order

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
                
            data.append({
                'id': order.id,
                'date': order.created_at.isoformat(),
                'total_amount': str(order.total_amount),
                'status': order.status, # PENDING, PAID, CANCELLED
                'invoice_number': order.invoice_number,
                'items': items
            })
            
        return Response({
            'count': len(data),
            'invoices': data
        })
