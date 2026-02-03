"""
API Views para el Sistema de Referidos
--------------------------------------
Endpoints para la app móvil Flutter.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone

from discounts.referral_service import (
    is_referral_enabled,
    get_active_referral_program,
    get_or_create_client_referral_code,
    get_share_data,
    get_referral_stats,
    get_referral_history,
    validate_referral_code,
)


class ReferralStatusView(APIView):
    """
    GET: Verifica si el programa de referidos está habilitado para el gym
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = getattr(request.user, 'client_profile', None)
        if not client:
            return Response({'error': 'Cliente no encontrado'}, status=404)
        
        gym = client.gym
        enabled = is_referral_enabled(gym)
        
        response_data = {
            'enabled': enabled,
        }
        
        if enabled:
            program = get_active_referral_program(gym)
            if program:
                response_data['program'] = {
                    'name': program.name,
                    'description': program.description,
                    'referrer_reward': program.get_referrer_reward_display(),
                    'referred_reward': program.get_referred_reward_display(),
                }
        
        return Response(response_data)


class ReferralCodeView(APIView):
    """
    GET: Obtiene el código de referido del cliente y datos para compartir
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = getattr(request.user, 'client_profile', None)
        if not client:
            return Response({'error': 'Cliente no encontrado'}, status=404)
        
        gym = client.gym
        
        # Verificar que está habilitado
        if not is_referral_enabled(gym):
            return Response({'error': 'Programa de referidos no disponible'}, status=400)
        
        # Obtener datos para compartir
        share_data = get_share_data(client, request)
        
        return Response(share_data)


class ReferralStatsView(APIView):
    """
    GET: Obtiene estadísticas de referidos del cliente
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = getattr(request.user, 'client_profile', None)
        if not client:
            return Response({'error': 'Cliente no encontrado'}, status=404)
        
        gym = client.gym
        
        # Verificar que está habilitado
        if not is_referral_enabled(gym):
            return Response({'error': 'Programa de referidos no disponible'}, status=400)
        
        stats = get_referral_stats(client)
        
        return Response(stats)


class ReferralHistoryView(APIView):
    """
    GET: Obtiene el historial de referidos del cliente
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = getattr(request.user, 'client_profile', None)
        if not client:
            return Response({'error': 'Cliente no encontrado'}, status=404)
        
        gym = client.gym
        
        # Verificar que está habilitado
        if not is_referral_enabled(gym):
            return Response({'error': 'Programa de referidos no disponible'}, status=400)
        
        referrals = get_referral_history(client)
        
        history = []
        for ref in referrals:
            referred_name = ""
            if ref.referred:
                referred_name = f"{ref.referred.first_name} {ref.referred.last_name}".strip()
            elif ref.referred_name:
                referred_name = ref.referred_name
            elif ref.referred_email:
                referred_name = ref.referred_email.split('@')[0]
            
            history.append({
                'id': ref.id,
                'referred_name': referred_name,
                'status': ref.status,
                'status_display': ref.get_status_display(),
                'invited_at': ref.invited_at.isoformat() if ref.invited_at else None,
                'registered_at': ref.registered_at.isoformat() if ref.registered_at else None,
                'completed_at': ref.completed_at.isoformat() if ref.completed_at else None,
                'credit_earned': str(ref.referrer_credit_given) if ref.referrer_credit_given else '0.00',
            })
        
        return Response({'referrals': history})


class ValidateReferralCodeView(APIView):
    """
    POST: Valida un código de referido (usado durante el registro)
    """
    
    def post(self, request):
        code = request.data.get('code', '').strip()
        gym_id = request.data.get('gym_id')
        
        if not code:
            return Response({'valid': False, 'error': 'Código vacío'}, status=400)
        
        if not gym_id:
            return Response({'valid': False, 'error': 'Gimnasio no especificado'}, status=400)
        
        from organizations.models import Gym
        try:
            gym = Gym.objects.get(id=gym_id)
        except Gym.DoesNotExist:
            return Response({'valid': False, 'error': 'Gimnasio no encontrado'}, status=404)
        
        # Verificar que está habilitado
        if not is_referral_enabled(gym):
            return Response({'valid': False, 'error': 'Programa de referidos no disponible'}, status=400)
        
        referrer, error = validate_referral_code(code, gym)
        
        if error:
            return Response({'valid': False, 'error': error})
        
        program = get_active_referral_program(gym)
        
        return Response({
            'valid': True,
            'referrer_name': referrer.first_name,
            'reward': program.get_referred_reward_display() if program else None,
        })


class InviteFriendView(APIView):
    """
    POST: Registra una invitación enviada (opcional, para tracking)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        client = getattr(request.user, 'client_profile', None)
        if not client:
            return Response({'error': 'Cliente no encontrado'}, status=404)
        
        gym = client.gym
        
        # Verificar que está habilitado
        if not is_referral_enabled(gym):
            return Response({'error': 'Programa de referidos no disponible'}, status=400)
        
        email = request.data.get('email', '').strip()
        name = request.data.get('name', '').strip()
        
        if not email and not name:
            return Response({'error': 'Proporciona email o nombre del invitado'}, status=400)
        
        # Verificar que no se invita a sí mismo
        if email and email.lower() == client.email.lower():
            return Response({'error': 'No puedes invitarte a ti mismo'}, status=400)
        
        program = get_active_referral_program(gym)
        if not program:
            return Response({'error': 'No hay programa activo'}, status=400)
        
        # Verificar límite de referidos
        from discounts.models import Referral
        if program.max_referrals_per_client > 0:
            current_count = Referral.objects.filter(
                referrer=client,
                program=program
            ).count()
            if current_count >= program.max_referrals_per_client:
                return Response({
                    'error': f'Has alcanzado el límite de {program.max_referrals_per_client} invitaciones'
                }, status=400)
        
        # Verificar si ya invitó a este email
        if email:
            existing = Referral.objects.filter(
                referrer=client,
                referred_email__iexact=email
            ).first()
            if existing:
                return Response({
                    'error': 'Ya has invitado a esta persona anteriormente'
                }, status=400)
        
        # Crear registro de invitación
        code = get_or_create_client_referral_code(client)
        
        referral = Referral.objects.create(
            program=program,
            referrer=client,
            referred_email=email,
            referred_name=name,
            referral_code=code,
            status=Referral.Status.PENDING
        )
        
        return Response({
            'success': True,
            'message': 'Invitación registrada',
            'referral_id': referral.id
        })
