from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_gym_permission
from django.contrib import messages
from .models import Room, Activity, ActivityCategory, ActivityPolicy, ScheduleSettings
from staff.models import StaffProfile
from .forms import RoomForm, ActivityForm, ActivityCategoryForm, ActivityPolicyForm
from .schedule_forms import ScheduleSettingsForm
from services.franchise_service import FranchisePropagationService

@login_required
@require_gym_permission('activities.view_room')
def room_list(request):
    gym = request.gym
    rooms = Room.objects.filter(gym=gym).order_by('name')
    return render(request, 'backoffice/activities/rooms/list.html', {'rooms': rooms})

@login_required
@require_gym_permission('activities.add_room')
def room_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.gym = gym
            room.save()
            messages.success(request, 'Sala creada correctamente.')
            return redirect('room_list')
    else:
        form = RoomForm()
    
    return render(request, 'backoffice/activities/rooms/form.html', {
        'form': form,
        'title': 'Nueva Sala'
    })

@login_required
@require_gym_permission('activities.change_room')
def room_edit(request, pk):
    gym = request.gym
    room = get_object_or_404(Room, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sala actualizada correctamente.')
            return redirect('room_list')
    else:
        form = RoomForm(instance=room)
    
    return render(request, 'backoffice/activities/rooms/form.html', {
        'form': form,
        'title': f'Editar {room.name}',
        'room': room
    })

# --- Activities ---

@login_required
@require_gym_permission('activities.view_activity')
def activity_list(request):
    gym = request.gym
    activities = Activity.objects.filter(gym=gym).select_related('category', 'policy')
    return render(request, 'backoffice/activities/classes/list.html', {'activities': activities})

@login_required
@require_gym_permission('activities.add_activity')
def activity_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES, gym=gym, user=request.user)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.gym = gym
            activity.save()
            form.save_m2m()
            
            # Handle Propagation
            if 'propagate_to_gyms' in form.fields and form.cleaned_data.get('propagate_to_gyms'):
                target_gyms = form.cleaned_data['propagate_to_gyms']
                results = FranchisePropagationService.propagate_activity(activity, target_gyms)
                
                msg = f'Actividad creada. Propagación: {results["created"]} creadas, {results["updated"]} actualizadas.'
                if results['errors']:
                    msg += f' Warning: Hubo {len(results["errors"])} errores.'
                messages.success(request, msg)
            else:
                messages.success(request, 'Actividad creada correctamente.')
                
            return redirect('activity_list')
    else:
        form = ActivityForm(gym=gym, user=request.user)
    
    return render(request, 'backoffice/activities/classes/form.html', {
        'form': form,
        'title': 'Nueva Actividad'
    })

@login_required
@require_gym_permission('activities.change_activity')
def activity_edit(request, pk):
    gym = request.gym
    activity = get_object_or_404(Activity, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES, instance=activity, gym=gym, user=request.user)
        if form.is_valid():
            activity = form.save()
            
            # Handle Propagation
            if 'propagate_to_gyms' in form.fields and form.cleaned_data.get('propagate_to_gyms'):
                target_gyms = form.cleaned_data['propagate_to_gyms']
                results = FranchisePropagationService.propagate_activity(activity, target_gyms)
                
                msg = f'Actividad actualizada. Propagación: {results["created"]} creadas, {results["updated"]} actualizadas.'
                messages.success(request, msg)
            else:
                messages.success(request, 'Actividad actualizada.')
                
            return redirect('activity_list')
    else:
        form = ActivityForm(instance=activity, gym=gym, user=request.user)
    
    return render(request, 'backoffice/activities/classes/form.html', {
        'form': form,
        'title': f'Editar {activity.name}'
    })

    return render(request, 'backoffice/activities/classes/form.html', {
        'form': form,
        'title': f'Editar {activity.name}'
    })


# --- Categories ---

@login_required
@require_gym_permission('activities.view_activitycategory')
def category_list(request):
    gym = request.gym
    categories = ActivityCategory.objects.filter(gym=gym).select_related('parent')
    return render(request, 'backoffice/activities/categories/list.html', {'categories': categories})

@login_required
@require_gym_permission('activities.add_activitycategory')
def category_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = ActivityCategoryForm(request.POST, request.FILES, gym=gym)
        if form.is_valid():
            category = form.save(commit=False)
            category.gym = gym
            category.save()
            messages.success(request, 'Categoría creada correctamente.')
            return redirect('category_list')
    else:
        form = ActivityCategoryForm(gym=gym)
    
    return render(request, 'backoffice/activities/categories/form.html', {
        'form': form,
        'title': 'Nueva Categoría'
    })

@login_required
@require_gym_permission('activities.change_activitycategory')
def category_edit(request, pk):
    gym = request.gym
    category = get_object_or_404(ActivityCategory, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = ActivityCategoryForm(request.POST, request.FILES, instance=category, gym=gym)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada.')
            return redirect('category_list')
    else:
        form = ActivityCategoryForm(instance=category, gym=gym)
    
    return render(request, 'backoffice/activities/categories/form.html', {
        'form': form,
        'title': f'Editar {category.name}'
    })
    return render(request, 'backoffice/activities/categories/form.html', {
        'form': form,
        'title': f'Editar {category.name}'
    })

@login_required
@require_gym_permission('activities.view_activity') 
def calendar_view(request):
    gym = request.gym
    
    # We pass data for the "Create/Edit" modals to populate dropdowns
    rooms = Room.objects.filter(gym=gym).values('id', 'name', 'capacity')
    activities = Activity.objects.filter(gym=gym).select_related('category').values('id', 'name', 'duration')
    staff_members = StaffProfile.objects.filter(gym=gym, is_active=True).select_related('user')
    
    # We need to construct a cleaner staff list with full names
    staff_list = []
    for s in staff_members:
        # User model (custom) might not have get_full_name
        first = s.user.first_name
        last = s.user.last_name
        if first or last:
            name = f"{first} {last}".strip()
        else:
            name = s.user.email
            
        staff_list.append({'id': s.id, 'name': name})
    
    # Convert staff_list to JSON for JavaScript
    import json
    staff_list_json = json.dumps(staff_list)

    return render(request, 'backoffice/scheduler/calendar.html', {
        'rooms': rooms,
        'activities': activities,
        'staff_list': staff_list,  # For Django template loop
        'staff_list_json': staff_list_json,  # For JavaScript
        'title': 'Calendario de Actividades'
    })

# --- Policies ---

@login_required
@require_gym_permission('activities.view_activitypolicy')
def policy_list(request):
    gym = request.gym
    policies = ActivityPolicy.objects.filter(gym=gym).order_by('name')
    return render(request, 'backoffice/activities/policies/list.html', {'policies': policies})

@login_required
@require_gym_permission('activities.add_activitypolicy')
def policy_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = ActivityPolicyForm(request.POST)
        if form.is_valid():
            policy = form.save(commit=False)
            policy.gym = gym
            policy.save()
            messages.success(request, 'Política creada correctamente.')
            return redirect('policy_list')
    else:
        form = ActivityPolicyForm()
    
    return render(request, 'backoffice/activities/policies/form.html', {
        'form': form,
        'title': 'Nueva Política'
    })

@login_required
@require_gym_permission('activities.change_activitypolicy')
def policy_edit(request, pk):
    gym = request.gym
    policy = get_object_or_404(ActivityPolicy, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = ActivityPolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, 'Política actualizada.')
            return redirect('policy_list')
    else:
        form = ActivityPolicyForm(instance=policy)
    
    return render(request, 'backoffice/activities/policies/form.html', {
        'form': form,
        'title': f'Editar {policy.name}',
        'policy': policy
    })


@login_required
@require_gym_permission('activities.view_activity')
def schedule_settings(request):
    """
    Vista para gestionar la configuración del sistema de horarios.
    """
    gym = request.gym
    settings = ScheduleSettings.get_for_gym(gym)
    
    if request.method == 'POST':
        form = ScheduleSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Configuración de horarios guardada correctamente.')
            return redirect('schedule_settings')
    else:
        form = ScheduleSettingsForm(instance=settings)
    
    return render(request, 'backoffice/settings/schedule_settings.html', {
        'form': form,
        'settings': settings,
        'title': 'Configuración de Horarios'
    })
