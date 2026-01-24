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
    
    def get(self, request):
        try:
            client = get_object_or_404(Client, user=request.user)
            gym = client.gym
            
            # Get active membership plans available for online purchase
            from memberships.models import MembershipPlan
            plans = MembershipPlan.objects.filter(
                gym=gym, 
                is_active=True,
                available_online=True
            ).values('id', 'name', 'price', 'duration_days', 'description')
            
            # Get active products available for online purchase
            from products.models import Product
            products = Product.objects.filter(
                gym=gym,
                is_active=True,
                available_online=True
            ).values('id', 'name', 'price', 'description', 'stock')
            
            return Response({
                'membership_plans': list(plans),
                'products': list(products)
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
