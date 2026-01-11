from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_gym_permission
from django.contrib import messages
from .models import Room, Activity, ActivityCategory, CancellationPolicy
from .models import Room, Activity, ActivityCategory, CancellationPolicy
from staff.models import StaffProfile
from .forms import RoomForm, ActivityForm, ActivityCategoryForm

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
    activities = Activity.objects.filter(gym=gym).select_related('category', 'cancellation_policy')
    return render(request, 'backoffice/activities/classes/list.html', {'activities': activities})

@login_required
@require_gym_permission('activities.add_activity')
def activity_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES, gym=gym)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.gym = gym
            activity.save()
            form.save_m2m()
            messages.success(request, 'Actividad creada correctamente.')
            return redirect('activity_list')
    else:
        form = ActivityForm(gym=gym)
    
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
        form = ActivityForm(request.POST, request.FILES, instance=activity, gym=gym)
        if form.is_valid():
            form.save()
            messages.success(request, 'Actividad actualizada.')
            return redirect('activity_list')
    else:
        form = ActivityForm(instance=activity, gym=gym)
    
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

    return render(request, 'backoffice/scheduler/calendar.html', {
        'rooms': rooms,
        'activities': activities,
        'staff_list': staff_list,
        'title': 'Calendario de Actividades'
    })
