"""
Shop views for the mobile app API
Allows clients to browse products and request info
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from clients.models import Client


class ShopView(APIView):
    """
    GET: List available products/memberships for sale in the app
    """
    permission_classes = [IsAuthenticated]
    
    def _calculate_duration_days(self, amount, unit):
        """Convert frequency amount and unit to days"""
        if unit == 'DAY':
            return amount
        elif unit == 'WEEK':
            return amount * 7
        elif unit == 'MONTH':
            return amount * 30
        elif unit == 'YEAR':
            return amount * 365
        return amount * 30  # default to months
    
    def get(self, request):
        try:
            client = get_object_or_404(Client, user=request.user)
            gym = client.gym
            
            # Get active membership plans available for online purchase
            from memberships.models import MembershipPlan
            plans_qs = MembershipPlan.objects.filter(
                gym=gym, 
                is_active=True,
                is_visible_online=True
            ).values('id', 'name', 'base_price', 'description', 'frequency_amount', 'frequency_unit')
            # Map fields to expected names
            plans = [
                {
                    'id': p['id'],
                    'name': p['name'],
                    'price': str(p['base_price']),
                    'description': p['description'] or '',
                    'duration_days': self._calculate_duration_days(p['frequency_amount'], p['frequency_unit'])
                }
                for p in plans_qs
            ]
            
            # Get active products available for online purchase
            from products.models import Product
            products_qs = Product.objects.filter(
                gym=gym,
                is_active=True,
                is_visible_online=True
            ).values('id', 'name', 'base_price', 'description', 'stock_quantity')
            # Map fields to expected names
            products = [
                {
                    'id': p['id'],
                    'name': p['name'],
                    'price': str(p['base_price']),
                    'description': p['description'] or '',
                    'stock': p['stock_quantity']
                }
                for p in products_qs
            ]
            
            # Get active services available for online booking
            from services.models import Service
            services_qs = Service.objects.filter(
                gym=gym,
                is_active=True,
                is_visible_online=True
            ).values('id', 'name', 'base_price', 'description', 'duration')
            # Map fields to expected names
            services = [
                {
                    'id': s['id'],
                    'name': s['name'],
                    'price': str(s['base_price']),
                    'description': s['description'] or '',
                    'duration_minutes': s['duration']
                }
                for s in services_qs
            ]
            
            return Response({
                'success': True,
                'membership_plans': plans,
                'products': products,
                'services': services
            })
            
        except Client.DoesNotExist:
            return Response({'error': 'Cliente no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class RequestInfoView(APIView):
    """
    POST: Request more information about a product/plan
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            client = get_object_or_404(Client, user=request.user)
            
            item_type = request.data.get('type')  # 'plan' or 'product'
            item_id = request.data.get('id')
            message = request.data.get('message', '')
            
            if not item_type or not item_id:
                return Response({'error': 'Tipo e ID requeridos'}, status=400)
            
            # Create a notification/task for the gym staff
            # For now, just log it
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Info request from {client}: {item_type} #{item_id} - {message}")
            
            return Response({
                'success': True,
                'message': 'Solicitud enviada correctamente'
            })
            
        except Client.DoesNotExist:
            return Response({'error': 'Cliente no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
