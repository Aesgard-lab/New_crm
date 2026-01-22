"""
API Views for Client Profile (Mobile App).
Profile viewing, editing, password change, and notifications.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.hashers import check_password

from clients.models import Client, ClientMembership


class ProfileView(views.APIView):
    """
    Get or update client profile.
    
    GET /api/profile/ - Get profile data
    PUT /api/profile/ - Update profile data
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            client = Client.objects.select_related('gym').get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get active membership
        active_membership = client.memberships.filter(status='ACTIVE').select_related('plan').first()
        membership_data = None
        
        if active_membership:
            plan = active_membership.plan
            membership_data = {
                'id': active_membership.id,
                'plan_name': plan.name if plan else 'Membresía',
                'status': active_membership.status,
                'start_date': active_membership.start_date.isoformat() if active_membership.start_date else None,
                'end_date': active_membership.end_date.isoformat() if active_membership.end_date else None,
                'sessions_remaining': getattr(active_membership, 'sessions_remaining', None),
                'sessions_total': plan.sessions_included if plan and hasattr(plan, 'sessions_included') else None,
                'is_unlimited': plan.duration_type == 'UNLIMITED' if plan else False,
            }
        
        return Response({
            'id': client.id,
            'first_name': client.first_name,
            'last_name': client.last_name,
            'full_name': client.full_name,
            'email': client.email,
            'phone': client.phone or '',
            'dni': client.dni or '',
            'birth_date_formatted': client.birth_date.strftime('%d/%m/%Y') if client.birth_date else '',
            'address': client.address or '',
            'client_type_display': client.get_client_type_display() if hasattr(client, 'client_type') and hasattr(client, 'get_client_type_display') else '',
            'access_code': client.access_code,
            'photo_url': client.photo.url if client.photo else None,
            'gym': {
                'id': client.gym.id,
                'name': client.gym.name,
            },
            'gym_name': client.gym.name,
            'created_at': client.created_at.isoformat() if hasattr(client, 'created_at') and client.created_at else None,
            'email_notifications': getattr(client, 'email_notifications', True),
            'membership': membership_data,
        })
    
    def put(self, request):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update allowed fields
        data = request.data
        
        if 'first_name' in data:
            client.first_name = data['first_name']
        if 'last_name' in data:
            client.last_name = data['last_name']
        if 'phone' in data:
            client.phone = data['phone']
        
        # Email change requires verification (for now just update)
        if 'email' in data and data['email'] != client.email:
            client.email = data['email']
            # Also update user email
            client.user.email = data['email']
            client.user.save()
        
        client.save()
        
        return Response({
            'message': 'Perfil actualizado correctamente',
            'client': {
                'first_name': client.first_name,
                'last_name': client.last_name,
                'email': client.email,
                'phone': client.phone or '',
            }
        })


class ChangePasswordView(views.APIView):
    """
    Change client password.
    
    POST /api/profile/change-password/
    Body: { current_password, new_password }
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
        
        current_password = request.data.get('current_password') or request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response(
                {'error': 'Se requieren contraseña actual y nueva'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify current password
        if not check_password(current_password, client.user.password):
            return Response(
                {'error': 'Contraseña actual incorrecta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate new password
        if len(new_password) < 8:
            return Response(
                {'error': 'La nueva contraseña debe tener al menos 8 caracteres'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        client.user.set_password(new_password)
        client.user.save()
        
        return Response({
            'message': 'Contraseña cambiada correctamente'
        })


class ToggleNotificationsView(views.APIView):
    """
    Toggle email notifications for the client.
    
    POST /api/profile/notifications/
    Body: { enabled: true/false }
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
        
        enabled = request.data.get('enabled', True)
        
        # Check if the field exists on the model
        if hasattr(client, 'email_notifications'):
            client.email_notifications = enabled
            client.save()
        
        return Response({
            'message': 'Notificaciones actualizadas',
            'email_notifications': enabled
        })


class MembershipDetailView(views.APIView):
    """
    Get detailed membership info.
    
    GET /api/profile/membership/
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
        
        # Get all memberships (active and past)
        memberships = client.memberships.select_related('plan').order_by('-start_date')
        
        memberships_data = []
        for membership in memberships:
            plan = membership.plan
            memberships_data.append({
                'id': membership.id,
                'plan_name': plan.name if plan else 'Membresía',
                'status': membership.status,
                'start_date': membership.start_date.isoformat() if membership.start_date else None,
                'end_date': membership.end_date.isoformat() if membership.end_date else None,
                'sessions_remaining': getattr(membership, 'sessions_remaining', None),
                'sessions_total': plan.sessions_included if plan and hasattr(plan, 'sessions_included') else None,
                'is_active': membership.status == 'ACTIVE',
            })
        
        active_membership = next((m for m in memberships_data if m['is_active']), None)
        
        return Response({
            'has_active_membership': active_membership is not None,
            'active_membership': active_membership,
            'all_memberships': memberships_data,
        })
