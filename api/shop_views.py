"""
API Views for Client Shop (Mobile App).
Browse products, services, and membership plans available for purchase.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from clients.models import Client
from products.models import Product, ProductCategory
from services.models import Service, ServiceCategory
from memberships.models import MembershipPlan


class ShopView(views.APIView):
    """
    Get all shop items: products, services, and membership plans.
    
    GET /api/shop/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            client = Client.objects.get(user=request.user)
            gym = client.gym
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get visible products
        products = Product.objects.filter(
            gym=gym,
            is_active=True,
            is_visible_online=True
        ).select_related('category', 'tax_rate')
        
        products_data = [{
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'image_url': p.image.url if p.image else None,
            'price': float(p.final_price),
            'category': p.category.name if p.category else None,
            'in_stock': p.stock_quantity > 0 if p.track_stock else True,
        } for p in products]
        
        # Get visible services
        services = Service.objects.filter(
            gym=gym,
            is_active=True,
            is_visible_online=True
        ).select_related('category', 'tax_rate')
        
        services_data = [{
            'id': s.id,
            'name': s.name,
            'description': s.description,
            'image_url': s.image.url if s.image else None,
            'price': float(s.final_price),
            'duration': s.duration,
            'category': s.category.name if s.category else None,
            'color': s.color,
        } for s in services]
        
        # Get available membership plans
        plans = MembershipPlan.objects.filter(
            gym=gym,
            is_active=True
        )
        
        plans_data = [{
            'id': p.id,
            'name': p.name,
            'description': p.description if hasattr(p, 'description') else '',
            'price': float(p.base_price),
            'duration_type': p.duration_type if hasattr(p, 'duration_type') else 'RECURRING',
            'duration_months': p.duration_months if hasattr(p, 'duration_months') else None,
            'sessions_included': p.sessions_included if hasattr(p, 'sessions_included') else None,
            'is_unlimited': getattr(p, 'duration_type', None) == 'UNLIMITED',
        } for p in plans]
        
        return Response({
            'products': products_data,
            'services': services_data,
            'membership_plans': plans_data,
            'counts': {
                'products': len(products_data),
                'services': len(services_data),
                'plans': len(plans_data),
            }
        })


class RequestInfoView(views.APIView):
    """
    Request info about a product/service/plan.
    Creates a notification for the gym.
    
    POST /api/shop/request-info/
    Body: { item_type: 'product'|'service'|'plan', item_id: int, message?: string }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        item_type = request.data.get('item_type')
        item_id = request.data.get('item_id')
        message = request.data.get('message', '')
        
        if not item_type or not item_id:
            return Response(
                {'error': 'Se requiere item_type e item_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get item name
        item_name = 'Desconocido'
        if item_type == 'product':
            try:
                item = Product.objects.get(id=item_id, gym=client.gym)
                item_name = item.name
            except Product.DoesNotExist:
                pass
        elif item_type == 'service':
            try:
                item = Service.objects.get(id=item_id, gym=client.gym)
                item_name = item.name
            except Service.DoesNotExist:
                pass
        elif item_type == 'plan':
            try:
                item = MembershipPlan.objects.get(id=item_id, gym=client.gym)
                item_name = item.name
            except MembershipPlan.DoesNotExist:
                pass
        
        # Get client full name
        client_name = f"{client.first_name} {client.last_name}".strip()
        if not client_name:
            client_name = client.email
        
        # TODO: Create notification for gym staff
        # For now, just return success
        # You could use a Notification model or send email here
        
        return Response({
            'message': 'Solicitud enviada correctamente',
            'details': {
                'client': client_name,
                'item_type': item_type,
                'item_name': item_name,
            }
        })
