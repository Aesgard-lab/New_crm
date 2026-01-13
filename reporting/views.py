from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_gym_permission
from organizations.models import Gym
from clients.models import Client, ClientTag, ClientGroup
from django.db.models import Q, Sum, Count
from datetime import timedelta, date

@login_required
@require_gym_permission("clients.view")
def client_explorer(request):
    gym_id = request.session.get("current_gym_id")
    if not gym_id:
        return render(request, "backoffice/error.html", {"message": "No hay gimnasio seleccionado"})
    
    gym = Gym.objects.get(id=gym_id)
    
    # Base Query
    clients = Client.objects.filter(gym=gym).prefetch_related('tags', 'memberships', 'visits')

    # --- Filters ---
    
    # 1. Text Search
    q = request.GET.get('q')
    if q:
        clients = clients.filter(
            Q(first_name__icontains=q) | 
            Q(last_name__icontains=q) | 
            Q(email__icontains=q) |
            Q(phone_number__icontains=q)
        )

    # 2. Status
    status = request.GET.get('status')
    if status and status != 'all':
        clients = clients.filter(status=status)

    # 3. Tags (Multiple)
    selected_tags = request.GET.getlist('tags')
    if selected_tags:
        clients = clients.filter(tags__id__in=selected_tags).distinct()

    # 4. Dates (registered)
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')
    if date_start:
        clients = clients.filter(created_at__date__gte=date_start)
    if date_end:
        clients = clients.filter(created_at__date__lte=date_end)

    # 5. Financial (Advanced) - Mocked for now or simple computation
    # Filtering by aggregation is heavier, usually handled by annotations
    # For MVP, we'll do basic filtering.

    # --- Aggregates ---
    total_count = clients.count()
    active_count = clients.filter(status='ACTIVE').count()
    
    # Context Data
    tags = ClientTag.objects.filter(gym=gym)
    
    context = {
        'clients': clients[:100], # Cap for performance in UI
        'total_count': total_count,
        'active_count': active_count,
        'tags': tags,
        'filters': {
            'q': q or '',
            'status': status or 'all',
            'date_start': date_start or '',
            'date_end': date_end or '',
            'selected_tags': [int(t) for t in selected_tags]
        }
    }
    return render(request, "reporting/explorer.html", context)
