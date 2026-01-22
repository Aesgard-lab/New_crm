from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from accounts.decorators import require_gym_permission
from .models import GymGoal, Gym
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


@login_required
@require_gym_permission('organizations.view_gymgoal')
def gym_goals_list(request):
    """Lista todos los objetivos del gimnasio actual"""
    gym = request.gym
    goals = GymGoal.objects.filter(gym=gym, is_active=True)
    
    context = {
        'gym': gym,
        'goals': goals,
    }
    return render(request, 'organizations/goals/list.html', context)


@login_required
@require_gym_permission('organizations.add_gymgoal')
def gym_goal_create(request):
    """Crear un nuevo objetivo (solo owners/franchise)"""
    gym = request.gym
    
    # Verificar que el usuario es owner de la franquicia
    if not request.user.franchises_owned.exists() and not request.user.is_superuser:
        messages.error(request, 'Solo los propietarios de franquicia pueden crear objetivos.')
        return redirect('gym_goals_list')
    
    if request.method == 'POST':
        try:
            period = request.POST.get('period', 'monthly')
            target_members = request.POST.get('target_members')
            target_revenue = request.POST.get('target_revenue')
            start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
            notes = request.POST.get('notes', '')
            
            # Calcular end_date según el período
            if period == 'monthly':
                end_date = start_date + relativedelta(months=1) - timedelta(days=1)
            elif period == 'quarterly':
                end_date = start_date + relativedelta(months=3) - timedelta(days=1)
            elif period == 'yearly':
                end_date = start_date + relativedelta(years=1) - timedelta(days=1)
            else:
                end_date = start_date + relativedelta(months=1) - timedelta(days=1)
            
            goal = GymGoal.objects.create(
                gym=gym,
                target_members=int(target_members) if target_members else None,
                target_revenue=float(target_revenue) if target_revenue else None,
                period=period,
                start_date=start_date,
                end_date=end_date,
                notes=notes,
                created_by=request.user
            )
            
            messages.success(request, f'Objetivo creado correctamente para {gym.name}')
            return redirect('gym_goals_list')
            
        except Exception as e:
            messages.error(request, f'Error al crear el objetivo: {str(e)}')
    
    context = {
        'gym': gym,
    }
    return render(request, 'organizations/goals/form.html', context)


@login_required
@require_gym_permission('organizations.change_gymgoal')
def gym_goal_edit(request, goal_id):
    """Editar un objetivo existente"""
    gym = request.gym
    goal = get_object_or_404(GymGoal, id=goal_id, gym=gym)
    
    # Verificar que el usuario es owner de la franquicia
    if not request.user.franchises_owned.exists() and not request.user.is_superuser:
        messages.error(request, 'Solo los propietarios de franquicia pueden editar objetivos.')
        return redirect('gym_goals_list')
    
    if request.method == 'POST':
        try:
            goal.period = request.POST.get('period', 'monthly')
            
            target_members = request.POST.get('target_members')
            goal.target_members = int(target_members) if target_members else None
            
            target_revenue = request.POST.get('target_revenue')
            goal.target_revenue = float(target_revenue) if target_revenue else None
            
            goal.start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
            goal.notes = request.POST.get('notes', '')
            
            # Recalcular end_date
            if goal.period == 'monthly':
                goal.end_date = goal.start_date + relativedelta(months=1) - timedelta(days=1)
            elif goal.period == 'quarterly':
                goal.end_date = goal.start_date + relativedelta(months=3) - timedelta(days=1)
            elif goal.period == 'yearly':
                goal.end_date = goal.start_date + relativedelta(years=1) - timedelta(days=1)
            
            goal.save()
            
            messages.success(request, 'Objetivo actualizado correctamente')
            return redirect('gym_goals_list')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el objetivo: {str(e)}')
    
    context = {
        'gym': gym,
        'goal': goal,
    }
    return render(request, 'organizations/goals/form.html', context)


@login_required
@require_gym_permission('organizations.delete_gymgoal')
def gym_goal_delete(request, goal_id):
    """Eliminar (desactivar) un objetivo"""
    gym = request.gym
    goal = get_object_or_404(GymGoal, id=goal_id, gym=gym)
    
    # Verificar que el usuario es owner de la franquicia
    if not request.user.franchises_owned.exists() and not request.user.is_superuser:
        messages.error(request, 'Solo los propietarios de franquicia pueden eliminar objetivos.')
        return redirect('gym_goals_list')
    
    if request.method == 'POST':
        goal.is_active = False
        goal.save()
        messages.success(request, 'Objetivo eliminado correctamente')
        return redirect('gym_goals_list')
    
    context = {
        'gym': gym,
        'goal': goal,
    }
    return render(request, 'organizations/goals/delete.html', context)


@login_required
@require_gym_permission('organizations.view_gymgoal')
def gym_goal_progress_api(request, goal_id):
    """API para obtener el progreso actual de un objetivo"""
    gym = request.gym
    goal = get_object_or_404(GymGoal, id=goal_id, gym=gym)
    
    # Calcular métricas actuales
    from backoffice.dashboard_service import DashboardService
    dashboard = DashboardService(gym)
    stats = dashboard.get_kpi_stats()
    
    current_members = stats.get('active_members', 0)
    current_revenue = stats.get('revenue_current', 0)
    
    progress_members = goal.get_progress_members(current_members) if goal.target_members else None
    progress_revenue = goal.get_progress_revenue(current_revenue) if goal.target_revenue else None
    
    return JsonResponse({
        'goal_id': goal.id,
        'current_members': current_members,
        'target_members': goal.target_members,
        'progress_members': progress_members,
        'current_revenue': float(current_revenue),
        'target_revenue': float(goal.target_revenue) if goal.target_revenue else None,
        'progress_revenue': progress_revenue,
        'period': goal.get_period_display(),
        'start_date': goal.start_date.strftime('%Y-%m-%d'),
        'end_date': goal.end_date.strftime('%Y-%m-%d'),
    })
