"""
API Views para Gamificación - App Flutter
==========================================
Endpoints para mostrar progreso, logros, ranking y retos en la app móvil.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from django.utils import timezone

from clients.models import Client
from gamification.models import (
    GamificationSettings,
    ClientProgress,
    Achievement,
    ClientAchievement,
    Challenge,
    ChallengeParticipation,
    XPTransaction,
)


def get_client_from_user(user):
    """Helper para obtener cliente desde el usuario"""
    try:
        return Client.objects.select_related('gym').get(user=user)
    except Client.DoesNotExist:
        return None


class GamificationStatusView(views.APIView):
    """
    GET: Obtiene el estado de gamificación y progreso del cliente
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        # Verificar si gamificación está habilitada
        try:
            settings = client.gym.gamification_settings
            if not settings.enabled or not settings.show_on_app:
                return Response({
                    'enabled': False,
                    'message': 'Gamificación no disponible'
                })
        except GamificationSettings.DoesNotExist:
            return Response({
                'enabled': False,
                'message': 'Gamificación no configurada'
            })
        
        # Obtener o crear progreso del cliente
        progress, created = ClientProgress.objects.get_or_create(client=client)
        
        # Obtener logros desbloqueados
        unlocked_count = ClientAchievement.objects.filter(client=client).count()
        total_achievements = Achievement.objects.filter(gym=client.gym, is_active=True).count()
        
        # Obtener retos activos
        today = timezone.now().date()
        active_challenges = Challenge.objects.filter(
            gym=client.gym,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        ).count()
        
        # Obtener posición en ranking
        rank_position = ClientProgress.objects.filter(
            client__gym=client.gym,
            total_xp__gt=progress.total_xp
        ).count() + 1
        
        rank_badge = progress.get_rank_badge()
        
        return Response({
            'enabled': True,
            'show_leaderboard': settings.show_leaderboard,
            'progress': {
                'total_xp': progress.total_xp,
                'current_level': progress.current_level,
                'xp_to_next_level': progress.xp_to_next_level(),
                'level_progress_percentage': progress.level_progress_percentage(),
                'current_streak': progress.current_streak,
                'longest_streak': progress.longest_streak,
                'total_visits': progress.total_visits,
                'rank_position': rank_position,
                'rank_badge': rank_badge,
            },
            'achievements': {
                'unlocked': unlocked_count,
                'total': total_achievements,
            },
            'challenges': {
                'active': active_challenges,
            }
        })


class LeaderboardView(views.APIView):
    """
    GET: Obtiene la tabla de clasificación
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        # Verificar configuración
        try:
            settings = client.gym.gamification_settings
            if not settings.enabled or not settings.show_on_app or not settings.show_leaderboard:
                return Response({'error': 'Leaderboard no disponible'}, status=status.HTTP_403_FORBIDDEN)
        except GamificationSettings.DoesNotExist:
            return Response({'error': 'Gamificación no configurada'}, status=status.HTTP_403_FORBIDDEN)
        
        # Top 50 jugadores
        top_clients = ClientProgress.objects.filter(
            client__gym=client.gym
        ).select_related('client').order_by('-total_xp')[:50]
        
        # Mi progreso
        my_progress, _ = ClientProgress.objects.get_or_create(client=client)
        my_rank = ClientProgress.objects.filter(
            client__gym=client.gym,
            total_xp__gt=my_progress.total_xp
        ).count() + 1
        
        leaderboard = []
        for idx, progress in enumerate(top_clients, 1):
            rank_badge = progress.get_rank_badge()
            leaderboard.append({
                'rank': idx,
                'client_id': progress.client.id,
                'name': progress.client.first_name,
                'initial': progress.client.last_name[:1] if progress.client.last_name else '',
                'level': progress.current_level,
                'total_xp': progress.total_xp,
                'badge_icon': rank_badge['icon'],
                'badge_name': rank_badge['name'],
                'is_me': progress.client.id == client.id,
            })
        
        return Response({
            'leaderboard': leaderboard,
            'my_rank': my_rank,
            'my_xp': my_progress.total_xp,
            'my_level': my_progress.current_level,
        })


class AchievementsView(views.APIView):
    """
    GET: Obtiene los logros del cliente
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        # Verificar configuración
        try:
            settings = client.gym.gamification_settings
            if not settings.enabled or not settings.show_on_app:
                return Response({'error': 'Gamificación no disponible'}, status=status.HTTP_403_FORBIDDEN)
        except GamificationSettings.DoesNotExist:
            return Response({'error': 'Gamificación no configurada'}, status=status.HTTP_403_FORBIDDEN)
        
        # Obtener todos los logros visibles
        all_achievements = Achievement.objects.filter(
            gym=client.gym,
            is_active=True
        ).order_by('category', 'order', 'name')
        
        # Obtener logros desbloqueados
        unlocked_ids = set(
            ClientAchievement.objects.filter(client=client)
            .values_list('achievement_id', flat=True)
        )
        
        # Mi progreso actual
        progress, _ = ClientProgress.objects.get_or_create(client=client)
        
        achievements_list = []
        for achievement in all_achievements:
            # Si es secreto y no desbloqueado, ocultarlo
            if achievement.is_secret and achievement.id not in unlocked_ids:
                continue
            
            # Calcular progreso hacia este logro
            current_value = 0
            if achievement.requirement_type == 'total_visits':
                current_value = progress.total_visits
            elif achievement.requirement_type == 'current_streak':
                current_value = progress.current_streak
            elif achievement.requirement_type == 'longest_streak':
                current_value = progress.longest_streak
            elif achievement.requirement_type == 'total_reviews':
                current_value = progress.total_reviews
            elif achievement.requirement_type == 'total_referrals':
                current_value = progress.total_referrals
            elif achievement.requirement_type == 'total_routines_completed':
                current_value = progress.total_routines_completed
            elif achievement.requirement_type == 'total_xp':
                current_value = progress.total_xp
            elif achievement.requirement_type == 'current_level':
                current_value = progress.current_level
            
            progress_pct = min(100, int((current_value / achievement.requirement_value) * 100)) if achievement.requirement_value > 0 else 0
            
            achievements_list.append({
                'id': achievement.id,
                'code': achievement.code,
                'name': achievement.name,
                'description': achievement.description,
                'icon': achievement.icon,
                'category': achievement.category,
                'category_display': achievement.get_category_display(),
                'xp_reward': achievement.xp_reward,
                'unlocked': achievement.id in unlocked_ids,
                'progress': {
                    'current': current_value,
                    'required': achievement.requirement_value,
                    'percentage': progress_pct,
                }
            })
        
        # Agrupar por categoría
        by_category = {}
        for ach in achievements_list:
            cat = ach['category']
            if cat not in by_category:
                by_category[cat] = {
                    'name': ach['category_display'],
                    'achievements': []
                }
            by_category[cat]['achievements'].append(ach)
        
        return Response({
            'achievements': achievements_list,
            'by_category': by_category,
            'summary': {
                'unlocked': len(unlocked_ids),
                'total': len(achievements_list),
            }
        })


class ChallengesView(views.APIView):
    """
    GET: Obtiene los retos activos y participación
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        # Verificar configuración
        try:
            settings = client.gym.gamification_settings
            if not settings.enabled or not settings.show_on_app:
                return Response({'error': 'Gamificación no disponible'}, status=status.HTTP_403_FORBIDDEN)
        except GamificationSettings.DoesNotExist:
            return Response({'error': 'Gamificación no configurada'}, status=status.HTTP_403_FORBIDDEN)
        
        today = timezone.now().date()
        
        # Retos activos
        active_challenges = Challenge.objects.filter(
            gym=client.gym,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        ).annotate(participants_count=Count('participants'))
        
        # Mis participaciones
        my_participations = set(
            ChallengeParticipation.objects.filter(client=client)
            .values_list('challenge_id', flat=True)
        )
        
        challenges_list = []
        for challenge in active_challenges:
            # Obtener mi progreso si estoy participando
            my_progress = None
            if challenge.id in my_participations:
                participation = ChallengeParticipation.objects.get(
                    challenge=challenge, client=client
                )
                my_progress = {
                    'current': participation.current_progress,
                    'target': challenge.target_value,
                    'percentage': min(100, int((participation.current_progress / challenge.target_value) * 100)) if challenge.target_value > 0 else 0,
                    'completed': participation.completed,
                }
            
            days_left = (challenge.end_date - today).days
            
            challenges_list.append({
                'id': challenge.id,
                'name': challenge.name,
                'description': challenge.description,
                'icon': challenge.icon,
                'xp_reward': challenge.xp_reward,
                'target_value': challenge.target_value,
                'target_type': challenge.target_type,
                'start_date': challenge.start_date.isoformat(),
                'end_date': challenge.end_date.isoformat(),
                'days_left': days_left,
                'participants_count': challenge.participants_count,
                'is_participating': challenge.id in my_participations,
                'my_progress': my_progress,
            })
        
        return Response({
            'challenges': challenges_list,
            'summary': {
                'active': len(challenges_list),
                'participating': len([c for c in challenges_list if c['is_participating']]),
            }
        })


class JoinChallengeView(views.APIView):
    """
    POST: Unirse a un reto
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, challenge_id):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            challenge = Challenge.objects.get(
                id=challenge_id,
                gym=client.gym,
                is_active=True
            )
        except Challenge.DoesNotExist:
            return Response({'error': 'Reto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar que no haya terminado
        today = timezone.now().date()
        if challenge.end_date < today:
            return Response({'error': 'Este reto ya ha terminado'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar que no esté ya participando
        if ChallengeParticipation.objects.filter(challenge=challenge, client=client).exists():
            return Response({'error': 'Ya estás participando en este reto'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear participación
        ChallengeParticipation.objects.create(
            challenge=challenge,
            client=client,
            joined_at=timezone.now()
        )
        
        return Response({
            'success': True,
            'message': f'Te has unido al reto "{challenge.name}"'
        })


class XPHistoryView(views.APIView):
    """
    GET: Historial de transacciones XP
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        # Últimas 50 transacciones
        transactions = XPTransaction.objects.filter(
            client=client
        ).order_by('-created_at')[:50]
        
        history = []
        for tx in transactions:
            history.append({
                'id': tx.id,
                'amount': tx.amount,
                'reason': tx.reason,
                'balance_after': tx.balance_after,
                'created_at': tx.created_at.isoformat(),
            })
        
        return Response({
            'history': history,
        })
