from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta

from organizations.models import Gym
from clients.models import Client
from .models import (
    GamificationSettings,
    ClientProgress,
    Achievement,
    ClientAchievement,
    Challenge,
    ChallengeParticipation,
    XPTransaction,
)


@login_required
def gamification_settings_view(request, gym_id):
    """Vista para configurar el sistema de gamificación"""
    gym = get_object_or_404(Gym, id=gym_id)
    
    # Verificar permisos
    if not request.user.has_perm('can_manage_gym', gym):
        messages.error(request, "No tienes permisos para gestionar este gimnasio")
        return redirect('home')
    
    # Obtener o crear configuración
    settings, created = GamificationSettings.objects.get_or_create(gym=gym)
    
    if request.method == 'POST':
        # Actualizar configuración
        settings.enabled = request.POST.get('enabled') == 'on'
        settings.xp_per_attendance = int(request.POST.get('xp_per_attendance', 10))
        settings.xp_per_routine_completion = int(request.POST.get('xp_per_routine_completion', 15))
        settings.xp_per_review = int(request.POST.get('xp_per_review', 10))
        settings.xp_per_referral = int(request.POST.get('xp_per_referral', 100))
        settings.xp_per_level = int(request.POST.get('xp_per_level', 100))
        settings.max_level = int(request.POST.get('max_level', 50))
        settings.show_leaderboard = request.POST.get('show_leaderboard') == 'on'
        settings.show_on_portal = request.POST.get('show_on_portal') == 'on'
        settings.show_on_app = request.POST.get('show_on_app') == 'on'
        settings.save()
        
        messages.success(request, "✅ Configuración de gamificación actualizada")
        return redirect('gamification_settings', gym_id=gym_id)
    
    context = {
        'gym': gym,
        'settings': settings,
        'page_title': 'Configuración de Gamificación',
    }
    
    return render(request, 'gamification/settings.html', context)


@login_required
def leaderboard_view(request, gym_id):
    """Vista de tabla de clasificación"""
    gym = get_object_or_404(Gym, id=gym_id)
    
    # Obtener o crear configuración de gamificación
    settings, created = GamificationSettings.objects.get_or_create(gym=gym)
    if not settings.enabled:
        messages.info(request, "💡 La gamificación no está activa. Actívala en Ajustes para que los clientes acumulen puntos.")
    
    # Obtener top 100 clientes por XP
    top_clients = ClientProgress.objects.filter(
        client__gym=gym
    ).select_related('client__user').order_by('-total_xp')[:100]
    
    # Estadísticas generales
    stats = {
        'total_players': ClientProgress.objects.filter(client__gym=gym).count(),
        'total_xp_awarded': ClientProgress.objects.filter(client__gym=gym).aggregate(
            total=Sum('total_xp')
        )['total'] or 0,
        'avg_level': ClientProgress.objects.filter(client__gym=gym).aggregate(
            avg=Sum('current_level')
        )['avg'] or 0,
        'longest_streak': ClientProgress.objects.filter(client__gym=gym).order_by('-longest_streak').first(),
    }
    
    context = {
        'gym': gym,
        'settings': settings,
        'top_clients': top_clients,
        'stats': stats,
        'page_title': 'Tabla de Clasificación',
    }
    
    return render(request, 'gamification/leaderboard.html', context)


@login_required
def achievements_view(request, gym_id):
    """Vista de gestión de logros"""
    gym = get_object_or_404(Gym, id=gym_id)
    
    # Obtener o crear configuración de gamificación
    settings, created = GamificationSettings.objects.get_or_create(gym=gym)
    if not settings.enabled:
        messages.info(request, "💡 La gamificación no está activa. Actívala en Ajustes para que los clientes desbloqueen logros.")
    
    # Obtener todos los logros del gimnasio con contador de desbloqueados
    achievements = Achievement.objects.filter(
        gym=gym,
        is_active=True
    ).annotate(
        unlocked_count=Count('clientachievement')
    ).order_by('category', 'order', 'name')
    
    # Logros más populares (más desbloqueados)
    popular_achievements = Achievement.objects.filter(
        gym=gym,
        is_active=True
    ).annotate(
        unlocked_count=Count('clientachievement')
    ).order_by('-unlocked_count')[:10]
    
    # Logros recientes desbloqueados
    recent_unlocks = ClientAchievement.objects.filter(
        achievement__gym=gym
    ).select_related('client__user', 'achievement').order_by('-unlocked_at')[:20]
    
    context = {
        'gym': gym,
        'settings': settings,
        'achievements': achievements,
        'popular_achievements': popular_achievements,
        'recent_unlocks': recent_unlocks,
        'page_title': 'Logros y Badges',
    }
    
    return render(request, 'gamification/achievements.html', context)


@login_required
def challenges_view(request, gym_id):
    """Vista de gestión de desafíos"""
    gym = get_object_or_404(Gym, id=gym_id)
    
    # Obtener o crear configuración de gamificación
    settings, created = GamificationSettings.objects.get_or_create(gym=gym)
    if not settings.enabled:
        messages.info(request, "💡 La gamificación no está activa. Actívala en Ajustes para crear retos.")
    
    today = timezone.now().date()
    
    # Obtener desafíos activos
    active_challenges = Challenge.objects.filter(
        gym=gym,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).annotate(
        participants_count=Count('participants')
    ).order_by('end_date')
    
    # Desafíos próximos
    upcoming_challenges = Challenge.objects.filter(
        gym=gym,
        is_active=True,
        start_date__gt=today
    ).annotate(
        participants_count=Count('participants')
    ).order_by('start_date')[:5]
    
    # Desafíos pasados
    past_challenges = Challenge.objects.filter(
        gym=gym,
        end_date__lt=today
    ).annotate(
        participants_count=Count('participants')
    ).order_by('-end_date')[:10]
    
    context = {
        'gym': gym,
        'settings': settings,
        'active_challenges': active_challenges,
        'upcoming_challenges': upcoming_challenges,
        'past_challenges': past_challenges,
        'page_title': 'Desafíos',
    }
    
    return render(request, 'gamification/challenges.html', context)


@login_required
def client_progress_view(request, gym_id, client_id):
    """Vista detallada del progreso de un cliente"""
    gym = get_object_or_404(Gym, id=gym_id)
    client = get_object_or_404(Client, id=client_id, gym=gym)
    
    # Verificar que la gamificación esté activa
    try:
        settings = gym.gamification_settings
        if not settings.enabled:
            messages.warning(request, "La gamificación no está activa en este gimnasio")
            return redirect('client_detail', client_id=client_id)
    except GamificationSettings.DoesNotExist:
        messages.error(request, "La gamificación no está configurada")
        return redirect('client_detail', client_id=client_id)
    
    # Obtener o crear progreso
    progress, created = ClientProgress.objects.get_or_create(client=client)
    
    # Logros desbloqueados
    unlocked_achievements = ClientAchievement.objects.filter(
        client=client
    ).select_related('achievement').order_by('-unlocked_at')
    
    # Historial de XP (últimas 50 transacciones)
    xp_transactions = XPTransaction.objects.filter(
        client=client
    ).order_by('-created_at')[:50]
    
    # Desafíos activos del cliente
    active_participations = ChallengeParticipation.objects.filter(
        client=client,
        challenge__is_active=True,
        challenge__end_date__gte=timezone.now().date()
    ).select_related('challenge')
    
    # Ranking del cliente
    rank = ClientProgress.objects.filter(
        client__gym=gym,
        total_xp__gt=progress.total_xp
    ).count() + 1
    
    context = {
        'gym': gym,
        'client': client,
        'progress': progress,
        'unlocked_achievements': unlocked_achievements,
        'xp_transactions': xp_transactions,
        'active_participations': active_participations,
        'rank': rank,
        'page_title': f'Progreso de {client.first_name}',
    }
    
    return render(request, 'gamification/client_progress.html', context)


# API Endpoints para la app móvil

@login_required
def api_my_progress(request, gym_id):
    """API: Progreso del cliente autenticado"""
    gym = get_object_or_404(Gym, id=gym_id)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    
    try:
        progress = client.progress
    except ClientProgress.DoesNotExist:
        progress, _ = ClientProgress.objects.get_or_create(client=client)
    
    rank_badge = progress.get_rank_badge()
    
    # Ranking del cliente
    rank = ClientProgress.objects.filter(
        client__gym=gym,
        total_xp__gt=progress.total_xp
    ).count() + 1
    
    data = {
        'total_xp': progress.total_xp,
        'current_level': progress.current_level,
        'xp_to_next_level': progress.xp_to_next_level(),
        'level_progress_percentage': progress.level_progress_percentage(),
        'current_streak': progress.current_streak,
        'longest_streak': progress.longest_streak,
        'total_visits': progress.total_visits,
        'total_reviews': progress.total_reviews,
        'total_referrals': progress.total_referrals,
        'rank': rank,
        'rank_badge': rank_badge,
    }
    
    return JsonResponse(data)


@login_required
def api_my_achievements(request, gym_id):
    """API: Logros del cliente autenticado"""
    gym = get_object_or_404(Gym, id=gym_id)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    
    # Logros desbloqueados
    unlocked = ClientAchievement.objects.filter(
        client=client
    ).select_related('achievement').values(
        'achievement__code',
        'achievement__name',
        'achievement__description',
        'achievement__icon',
        'achievement__category',
        'achievement__xp_reward',
        'unlocked_at'
    )
    
    # Todos los logros disponibles
    all_achievements = Achievement.objects.filter(
        gym=gym,
        is_active=True,
        is_secret=False
    ).values(
        'code',
        'name',
        'description',
        'icon',
        'category',
        'xp_reward',
        'requirement_type',
        'requirement_value'
    )
    
    data = {
        'unlocked': list(unlocked),
        'available': list(all_achievements),
        'unlocked_count': unlocked.count(),
        'total_count': all_achievements.count(),
    }
    
    return JsonResponse(data)


@login_required
def api_leaderboard(request, gym_id):
    """API: Tabla de clasificación"""
    gym = get_object_or_404(Gym, id=gym_id)
    
    # Top 100
    top_clients = ClientProgress.objects.filter(
        client__gym=gym
    ).select_related('client__user').order_by('-total_xp')[:100].values(
        'client__user__first_name',
        'client__user__last_name',
        'total_xp',
        'current_level',
        'current_streak'
    )
    
    data = {
        'leaderboard': list(top_clients),
    }
    
    return JsonResponse(data)
