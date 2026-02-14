"""
Shop views for the mobile app API
Allows clients to browse products and request info
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status as http_status
from django.shortcuts import get_object_or_404

from clients.models import Client

logger = logging.getLogger(__name__)


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
            
            # Get portal settings for membership purchase rules
            from organizations.models import PublicPortalSettings
            portal_settings, _ = PublicPortalSettings.objects.get_or_create(
                gym=gym,
                defaults={'public_slug': gym.name.lower().replace(' ', '-')[:50]}
            )
            
            # Check if client has active membership
            has_active_membership = client.memberships.filter(
                status__in=['ACTIVE', 'PENDING']
            ).exists()
            
            # Check if client has payment method
            has_payment_method = client.payment_methods.exists()
            
            # Check for scheduled changes
            from clients.models import ScheduledMembershipChange
            scheduled_change = ScheduledMembershipChange.objects.filter(
                client=client,
                status='PENDING'
            ).select_related('new_plan', 'current_membership').first()
            
            scheduled_change_data = None
            if scheduled_change:
                scheduled_change_data = {
                    'id': scheduled_change.id,
                    'new_plan_name': scheduled_change.new_plan.name,
                    'new_plan_id': scheduled_change.new_plan.id,
                    'scheduled_date': scheduled_change.scheduled_date.isoformat(),
                }
            
            # Get active membership plans available for online purchase
            from memberships.models import MembershipPlan
            plans_qs = MembershipPlan.objects.filter(
                gym=gym, 
                is_active=True,
                is_visible_online=True
            )
            
            # Filtrar planes según elegibilidad del cliente
            plans = []
            for plan in plans_qs:
                should_show, is_eligible, reason = plan.should_show_to_client(client)
                if not should_show:
                    continue  # Ocultar plan
                
                plan_data = {
                    'id': plan.id,
                    'name': plan.name,
                    'price': str(plan.base_price),
                    'description': plan.description or '',
                    'duration_days': self._calculate_duration_days(plan.frequency_amount, plan.frequency_unit),
                    'is_eligible': is_eligible,
                    'ineligible_reason': reason if not is_eligible else '',
                    'badge_text': plan.get_badge_text() if plan.has_eligibility_restriction() else '',
                    # Enrollment fee / Matrícula
                    'has_enrollment_fee': plan.has_enrollment_fee,
                    'enrollment_fee': str(plan.final_enrollment_fee) if plan.has_enrollment_fee else '0.00',
                    'enrollment_fee_channel': plan.enrollment_fee_channel if plan.has_enrollment_fee else '',
                    'first_payment_total': str(plan.first_payment_total) if plan.has_enrollment_fee else '',
                }
                plans.append(plan_data)
            
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
            )
            
            # Filtrar servicios según elegibilidad del cliente
            services = []
            for service in services_qs:
                should_show, is_eligible, reason = service.should_show_to_client(client)
                if not should_show:
                    continue  # Ocultar servicio
                
                service_data = {
                    'id': service.id,
                    'name': service.name,
                    'price': str(service.base_price),
                    'description': service.description or '',
                    'duration_minutes': service.duration,
                    'is_eligible': is_eligible,
                    'ineligible_reason': reason if not is_eligible else '',
                    'badge_text': service.get_badge_text() if service.has_eligibility_restriction() else '',
                }
                services.append(service_data)
            
            return Response({
                'success': True,
                'membership_plans': plans,
                'products': products,
                'services': services,
                # Membership purchase rules
                'membership_purchase_rules': {
                    'has_active_membership': has_active_membership,
                    'allow_duplicate_purchase': portal_settings.allow_duplicate_membership_purchase,
                    'duplicate_message': portal_settings.duplicate_membership_message,
                    'allow_change_at_renewal': portal_settings.allow_membership_change_at_renewal,
                    'has_payment_method': has_payment_method,
                    'scheduled_change': scheduled_change_data,
                }
            })
            
        except Client.DoesNotExist:
            return Response({'error': 'Cliente no encontrado'}, status=404)
        except Exception as e:
            logger.exception("Error loading shop data")
            return Response({'error': 'Error interno del servidor'}, status=500)


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
            logger.exception("Error processing info request")
            return Response({'error': 'Error interno del servidor'}, status=500)


class ScheduleMembershipChangeView(APIView):
    """
    POST: Schedule a membership plan change for when the current one ends
    DELETE: Cancel a scheduled membership change
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Schedule a membership change"""
        try:
            client = get_object_or_404(Client, user=request.user)
            gym = client.gym
            
            from organizations.models import PublicPortalSettings
            from memberships.models import MembershipPlan
            from clients.models import ScheduledMembershipChange
            from django.utils import timezone
            
            # Check settings
            portal_settings, _ = PublicPortalSettings.objects.get_or_create(
                gym=gym,
                defaults={'public_slug': gym.name.lower().replace(' ', '-')[:50]}
            )
            
            if not portal_settings.allow_membership_change_at_renewal:
                return Response({
                    'success': False,
                    'error': 'Esta función no está disponible.'
                }, status=http_status.HTTP_403_FORBIDDEN)
            
            # Check payment method
            if not client.payment_methods.exists():
                return Response({
                    'success': False,
                    'error': 'Necesitas tener una tarjeta de pago guardada.'
                }, status=http_status.HTTP_400_BAD_REQUEST)
            
            # Get current membership
            current_membership = client.memberships.filter(status='ACTIVE').first()
            if not current_membership:
                return Response({
                    'success': False,
                    'error': 'No tienes una cuota activa.'
                }, status=http_status.HTTP_400_BAD_REQUEST)
            
            # Get new plan
            plan_id = request.data.get('plan_id')
            try:
                new_plan = MembershipPlan.objects.get(
                    id=plan_id, 
                    gym=gym, 
                    is_active=True, 
                    is_visible_online=True
                )
            except MembershipPlan.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'El plan seleccionado no está disponible.'
                }, status=http_status.HTTP_404_NOT_FOUND)
            
            # Verificar elegibilidad del cliente para este plan
            if new_plan.has_eligibility_restriction():
                is_eligible, reason = new_plan.is_client_eligible(client)
                if not is_eligible:
                    return Response({
                        'success': False,
                        'error': reason
                    }, status=http_status.HTTP_403_FORBIDDEN)
            
            # Check not same plan
            if current_membership.plan and current_membership.plan.id == new_plan.id:
                return Response({
                    'success': False,
                    'error': 'Ya tienes este plan activo.'
                }, status=http_status.HTTP_400_BAD_REQUEST)
            
            # Cancel previous scheduled changes
            ScheduledMembershipChange.objects.filter(
                client=client,
                status='PENDING'
            ).update(status='CANCELLED')
            
            # Create new scheduled change
            scheduled_date = (
                current_membership.end_date or 
                current_membership.current_period_end or 
                timezone.now().date()
            )
            
            scheduled_change = ScheduledMembershipChange.objects.create(
                client=client,
                gym=gym,
                current_membership=current_membership,
                new_plan=new_plan,
                scheduled_date=scheduled_date
            )
            
            return Response({
                'success': True,
                'message': f'Cambio programado: Tu plan cambiará a "{new_plan.name}" el {scheduled_date.strftime("%d/%m/%Y")}',
                'scheduled_change': {
                    'id': scheduled_change.id,
                    'new_plan_name': new_plan.name,
                    'new_plan_id': new_plan.id,
                    'scheduled_date': scheduled_date.isoformat(),
                }
            })
            
        except Exception as e:
            logger.exception("Error scheduling membership change")
            return Response({'error': 'Error interno del servidor'}, status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request):
        """Cancel a scheduled membership change"""
        try:
            client = get_object_or_404(Client, user=request.user)
            
            from clients.models import ScheduledMembershipChange
            from django.utils import timezone
            
            change_id = request.data.get('change_id') or request.query_params.get('change_id')
            
            try:
                scheduled_change = ScheduledMembershipChange.objects.get(
                    id=change_id,
                    client=client,
                    status='PENDING'
                )
                scheduled_change.status = 'CANCELLED'
                scheduled_change.cancelled_at = timezone.now()
                scheduled_change.save()
                
                return Response({
                    'success': True,
                    'message': 'Cambio de plan cancelado correctamente.'
                })
            except ScheduledMembershipChange.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'No se encontró el cambio programado.'
                }, status=http_status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.exception("Error cancelling scheduled change")
            return Response({'error': 'Error interno del servidor'}, status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)

