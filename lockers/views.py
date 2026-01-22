"""
Vistas del módulo de Taquillas
==============================
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q

from .models import LockerZone, Locker, LockerAssignment


@login_required
def locker_dashboard(request):
    """Dashboard principal de taquillas."""
    gym = request.gym
    
    zones = LockerZone.objects.filter(gym=gym, is_active=True).annotate(
        total=Count('lockers'),
        available=Count('lockers', filter=Q(lockers__status='AVAILABLE')),
        assigned=Count('lockers', filter=Q(lockers__status='ASSIGNED')),
        maintenance=Count('lockers', filter=Q(lockers__status='MAINTENANCE')),
    )
    
    # Estadísticas generales
    total_lockers = Locker.objects.filter(zone__gym=gym).count()
    available_lockers = Locker.objects.filter(zone__gym=gym, status='AVAILABLE').count()
    assigned_lockers = Locker.objects.filter(zone__gym=gym, status='ASSIGNED').count()
    
    # Asignaciones que vencen pronto (próximos 7 días)
    today = timezone.now().date()
    from datetime import timedelta
    expiring_soon = LockerAssignment.objects.filter(
        locker__zone__gym=gym,
        status='ACTIVE',
        end_date__lte=today + timedelta(days=7),
        end_date__gte=today
    ).select_related('locker', 'client')[:10]
    
    context = {
        'zones': zones,
        'total_lockers': total_lockers,
        'available_lockers': available_lockers,
        'assigned_lockers': assigned_lockers,
        'expiring_soon': expiring_soon,
    }
    
    return render(request, 'backoffice/lockers/dashboard.html', context)


@login_required
def zone_list(request):
    """Listado de zonas de taquillas."""
    gym = request.gym
    zones = LockerZone.objects.filter(gym=gym).annotate(
        total=Count('lockers'),
        available=Count('lockers', filter=Q(lockers__status='AVAILABLE')),
        assigned=Count('lockers', filter=Q(lockers__status='ASSIGNED')),
    )
    
    return render(request, 'backoffice/lockers/zone_list.html', {'zones': zones})


@login_required
def zone_detail(request, zone_id):
    """Detalle de una zona con mapa de taquillas."""
    gym = request.gym
    zone = get_object_or_404(LockerZone, id=zone_id, gym=gym)
    lockers = zone.lockers.select_related().prefetch_related('assignments__client')
    
    # Estadísticas
    available_count = lockers.filter(status='AVAILABLE').count()
    assigned_count = lockers.filter(status='ASSIGNED').count()
    maintenance_count = lockers.filter(status='MAINTENANCE').count()
    
    # Asignaciones activas
    active_assignments = LockerAssignment.objects.filter(
        locker__zone=zone,
        status='ACTIVE'
    ).select_related('locker', 'client')
    
    return render(request, 'backoffice/lockers/zone_detail.html', {
        'zone': zone,
        'lockers': lockers,
        'available_count': available_count,
        'assigned_count': assigned_count,
        'maintenance_count': maintenance_count,
        'active_assignments': active_assignments,
    })


@login_required
def zone_create(request):
    """Crear nueva zona de taquillas."""
    gym = request.gym
    
    if request.method == 'POST':
        zone = LockerZone(
            gym=gym,
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            color=request.POST.get('color', '#6366F1'),
            rows=int(request.POST.get('rows', 4)),
            columns=int(request.POST.get('columns', 10)),
        )
        zone.save()
        
        # Auto-crear taquillas
        auto_create = request.POST.get('auto_create_lockers')
        if auto_create:
            default_price = request.POST.get('default_price', '0')
            for row in range(1, zone.rows + 1):
                for col in range(1, zone.columns + 1):
                    number = f"{row}{col:02d}"  # Ej: 101, 102, 201, etc.
                    Locker.objects.create(
                        zone=zone,
                        number=number,
                        row=row,
                        column=col,
                        monthly_price=default_price,
                    )
        
        messages.success(request, f'Zona "{zone.name}" creada correctamente.')
        return redirect('lockers:zone_detail', zone_id=zone.id)
    
    return render(request, 'backoffice/lockers/zone_form.html', {'zone': None})


@login_required
def zone_edit(request, zone_id):
    """Editar zona de taquillas."""
    gym = request.gym
    zone = get_object_or_404(LockerZone, id=zone_id, gym=gym)
    
    if request.method == 'POST':
        zone.name = request.POST.get('name')
        zone.description = request.POST.get('description', '')
        zone.color = request.POST.get('color', '#6366F1')
        zone.save()
        
        messages.success(request, f'Zona "{zone.name}" actualizada.')
        return redirect('lockers:zone_detail', zone_id=zone.id)
    
    return render(request, 'backoffice/lockers/zone_form.html', {'zone': zone})


@login_required
def locker_create(request, zone_id):
    """Crear taquilla individual."""
    gym = request.gym
    zone = get_object_or_404(LockerZone, id=zone_id, gym=gym)
    
    if request.method == 'POST':
        locker = Locker(
            zone=zone,
            number=request.POST.get('number'),
            row=request.POST.get('row') or None,
            column=request.POST.get('column') or None,
            size=request.POST.get('size', 'M'),
            monthly_price=request.POST.get('monthly_price', '0'),
            notes=request.POST.get('notes', ''),
        )
        locker.save()
        
        messages.success(request, f'Taquilla {locker.number} creada.')
        return redirect('lockers:zone_detail', zone_id=zone.id)
    
    return render(request, 'backoffice/lockers/locker_form.html', {'zone': zone, 'locker': None})


@login_required
def assignment_list(request):
    """Listado de todas las asignaciones."""
    gym = request.gym
    
    status_filter = request.GET.get('status', 'ACTIVE')
    assignments = LockerAssignment.objects.filter(
        locker__zone__gym=gym
    ).select_related('locker', 'locker__zone', 'client')
    
    if status_filter:
        assignments = assignments.filter(status=status_filter)
    
    return render(request, 'backoffice/lockers/assignment_list.html', {
        'assignments': assignments,
        'status_filter': status_filter,
    })


@login_required
def assign_locker(request, locker_id):
    """Asignar taquilla a un cliente."""
    gym = request.gym
    locker = get_object_or_404(Locker, id=locker_id, zone__gym=gym)
    
    if request.method == 'POST':
        from clients.models import Client
        
        client_id = request.POST.get('client')
        client = get_object_or_404(Client, id=client_id, gym=gym)
        
        assignment = LockerAssignment(
            locker=locker,
            client=client,
            start_date=request.POST.get('start_date') or timezone.now().date(),
            end_date=request.POST.get('end_date') or None,
            price=request.POST.get('monthly_price') or locker.monthly_price,
            is_included_in_membership='is_included' in request.POST,
            deposit_amount=request.POST.get('deposit') or 0,
            key_delivered='key_delivered' in request.POST,
            notes=request.POST.get('notes', ''),
            assigned_by=request.user,
        )
        assignment.save()
        
        messages.success(request, f'Taquilla {locker.number} asignada a {client.first_name} {client.last_name}.')
        return redirect('lockers:zone_detail', zone_id=locker.zone.id)
    
    return render(request, 'backoffice/lockers/assign_form.html', {
        'locker': locker,
    })


@login_required
def release_locker(request, assignment_id):
    """Liberar taquilla (cancelar asignación)."""
    gym = request.gym
    assignment = get_object_or_404(LockerAssignment, id=assignment_id, locker__zone__gym=gym)
    
    if request.method == 'POST':
        assignment.status = 'CANCELLED'
        assignment.key_returned = True
        assignment.key_returned_date = timezone.now().date()
        assignment.save()
        
        messages.success(request, f'Taquilla {assignment.locker.number} liberada.')
        return redirect('lockers:zone_detail', zone_id=assignment.locker.zone.id)
    
    return render(request, 'backoffice/lockers/release_confirm.html', {'assignment': assignment})


@login_required
@require_http_methods(['POST'])
def api_locker_status(request, locker_id):
    """API para cambiar estado de taquilla."""
    gym = request.gym
    locker = get_object_or_404(Locker, id=locker_id, zone__gym=gym)
    
    import json
    data = json.loads(request.body)
    new_status = data.get('status')
    
    if new_status in dict(Locker.STATUS_CHOICES):
        locker.status = new_status
        locker.save()
        return JsonResponse({'success': True, 'status': locker.status})
    
    return JsonResponse({'error': 'Invalid status'}, status=400)


@login_required
def zone_delete(request, zone_id):
    """Eliminar zona de taquillas."""
    gym = request.gym
    zone = get_object_or_404(LockerZone, id=zone_id, gym=gym)
    
    if request.method == 'POST':
        zone_name = zone.name
        zone.delete()
        messages.success(request, f'Zona "{zone_name}" eliminada correctamente.')
        return redirect('lockers:zone_list')
    
    return render(request, 'backoffice/lockers/zone_delete_confirm.html', {'zone': zone})


@login_required
def locker_edit(request, locker_id):
    """Editar taquilla."""
    gym = request.gym
    locker = get_object_or_404(Locker, id=locker_id, zone__gym=gym)
    zone = locker.zone
    
    if request.method == 'POST':
        locker.number = request.POST.get('number')
        locker.size = request.POST.get('size', 'M')
        locker.monthly_price = request.POST.get('monthly_price') or 0
        locker.status = request.POST.get('status', locker.status)
        locker.notes = request.POST.get('notes', '')
        locker.save()
        
        messages.success(request, f'Taquilla {locker.number} actualizada.')
        return redirect('lockers:zone_detail', zone_id=zone.id)
    
    return render(request, 'backoffice/lockers/locker_form.html', {'zone': zone, 'locker': locker})


@login_required
def locker_delete(request, locker_id):
    """Eliminar taquilla."""
    gym = request.gym
    locker = get_object_or_404(Locker, id=locker_id, zone__gym=gym)
    zone = locker.zone
    
    if request.method == 'POST':
        locker_number = locker.number
        locker.delete()
        messages.success(request, f'Taquilla {locker_number} eliminada.')
        return redirect('lockers:zone_detail', zone_id=zone.id)
    
    return render(request, 'backoffice/lockers/locker_delete_confirm.html', {'locker': locker})


@login_required
def api_search_clients(request):
    """API para buscar clientes (para asignar taquillas)."""
    gym = request.gym
    from clients.models import Client
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'clients': []})
    
    clients = Client.objects.filter(
        gym=gym,
        status='ACTIVE'
    ).filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(phone__icontains=query)
    )[:10]
    
    data = [{
        'id': c.id,
        'first_name': c.first_name,
        'last_name': c.last_name,
        'email': c.email or '',
        'phone': c.phone or '',
    } for c in clients]
    
    return JsonResponse({'clients': data})


@login_required
def assign_locker_to_client(request, client_id):
    """Asignar taquilla a un cliente específico (desde ficha del cliente)."""
    gym = request.gym
    from clients.models import Client
    
    client = get_object_or_404(Client, id=client_id, gym=gym)
    
    # Obtener zonas con taquillas disponibles
    zones = LockerZone.objects.filter(gym=gym, is_active=True).prefetch_related('lockers')
    
    if request.method == 'POST':
        locker_id = request.POST.get('locker')
        locker = get_object_or_404(Locker, id=locker_id, zone__gym=gym, status='AVAILABLE')
        
        assignment = LockerAssignment(
            locker=locker,
            client=client,
            start_date=request.POST.get('start_date') or timezone.now().date(),
            end_date=request.POST.get('end_date') or None,
            price=request.POST.get('monthly_price') or locker.monthly_price,
            deposit_amount=request.POST.get('deposit') or 0,
            key_delivered='key_delivered' in request.POST,
            notes=request.POST.get('notes', ''),
            assigned_by=request.user,
        )
        assignment.save()
        
        messages.success(request, f'Taquilla {locker.number} asignada a {client.first_name} {client.last_name}.')
        return redirect('client_detail', client_id=client.id)
    
    return render(request, 'backoffice/lockers/assign_to_client.html', {
        'client': client,
        'zones': zones,
    })


@login_required
def api_available_lockers(request):
    """API para obtener taquillas disponibles de una zona."""
    gym = request.gym
    zone_id = request.GET.get('zone_id')
    
    if not zone_id:
        return JsonResponse({'lockers': []})
    
    lockers = Locker.objects.filter(
        zone_id=zone_id,
        zone__gym=gym,
        status='AVAILABLE'
    ).order_by('number')
    
    data = [{
        'id': l.id,
        'number': l.number,
        'size': l.get_size_display(),
        'price': float(l.monthly_price) if l.monthly_price else 0,
    } for l in lockers]
    
    return JsonResponse({'lockers': data})
