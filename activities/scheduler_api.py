from datetime import datetime, timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from .models import ActivitySession, ScheduleSettings
from services.models import ServiceAppointment
from clients.models import ClientVisit

def _active_attendee_count(sess):
    late_ids = set(
        ClientVisit.objects.filter(
            client__in=sess.attendees.all(),
            date=sess.start_datetime.date(),
            status='CANCELLED',
            cancellation_type='LATE'
        ).values_list('client_id', flat=True)
    )
    return max(sess.attendees.count() - len(late_ids), 0)

@login_required
@require_GET
def get_calendar_events(request):
    """
    Returns events for FullCalendar (start, end, title, etc.)
    Query params: start, end (ISO dates)
    """
    gym = request.gym
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    
    events = []
    
    try:
        if not start_str or not end_str:
            return JsonResponse([], safe=False)
            
        # 1. Activity Sessions
        sessions = ActivitySession.objects.filter(
            gym=gym, 
            start_datetime__gte=start_str,
            start_datetime__lte=end_str
        ).select_related('activity', 'room', 'staff')
        
        for sess in sessions:
            # Use Activity Color
            color = sess.activity.color
            active_attendees = _active_attendee_count(sess)
                
            events.append({
                'id': f'sess_{sess.id}',
                'resourceId': sess.room.id if sess.room else None,
                'title': f"{sess.activity.name} ({active_attendees}/{sess.max_capacity})",
                'start': sess.start_datetime.isoformat(),
                'end': sess.end_datetime.isoformat(),
                'backgroundColor': color,
                'borderColor': color,
                'extendedProps': {
                    'type': 'session',
                    'staff': f"{sess.staff.user.first_name} {sess.staff.user.last_name}".strip() if sess.staff else 'Sin Asignar',
                    'room': sess.room.name if sess.room else 'Sin Sala',
                    'attendees': active_attendees,
                    'max_capacity': sess.max_capacity,
                    'db_id': sess.id
                }
            })
            
        # 2. Service Appointments
        appointments = ServiceAppointment.objects.filter(
            gym=gym,
            start_datetime__gte=start_str,
            start_datetime__lte=end_str
        ).select_related('service', 'client', 'staff', 'room')
        
        for apt in appointments:
            color = apt.service.color
            
            events.append({
                'id': f'apt_{apt.id}',
                'resourceId': apt.room.id if apt.room else None,
                'title': f"{apt.service.name} ({apt.client.first_name})",
                'start': apt.start_datetime.isoformat(),
                'end': apt.end_datetime.isoformat(),
                'backgroundColor': color,
                'borderColor': color,
                'extendedProps': {
                    'type': 'appointment',
                    'client': f"{apt.client.first_name} {apt.client.last_name}",
                    'staff': f"{apt.staff.user.first_name} {apt.staff.user.last_name}".strip() if apt.staff else 'Sin Asignar',
                    'status': apt.status,
                    'db_id': apt.id
                }
            })

        return JsonResponse(events, safe=False)
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def create_session_api(request):
    """
    Creates a single ActivitySession or a ScheduleRule + Sessions.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    gym = request.gym
    data = request.POST
    
    activity_id = data.get('activity')
    room_id = data.get('room')
    staff_id = data.get('staff')
    start_str = data.get('start_datetime') # For single
    type = data.get('type') # 'single' or 'recurring'
    
    # Common Validations
    if not activity_id:
        return JsonResponse({'error': 'Falta actividad'}, status=400)
    
    from django.shortcuts import get_object_or_404
    from .models import Activity, Room, ActivitySession, ScheduleRule
    from staff.models import StaffProfile
    
    activity = get_object_or_404(Activity, pk=activity_id, gym=gym)
    room = Room.objects.filter(pk=room_id, gym=gym).first() if room_id else None
    staff = StaffProfile.objects.filter(pk=staff_id, gym=gym).first() if staff_id else None
    
    if type == 'single':
        # Create one session
        if not start_str:
            return JsonResponse({'error': 'Falta fecha de inicio'}, status=400)
            
        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00')) # Simple parsing
        end_dt = start_dt + timedelta(minutes=activity.duration)
        
        # Get schedule settings for validations
        settings = ScheduleSettings.get_for_gym(gym)
        
        # Check room overlaps if not allowed
        if room and not settings.allow_room_overlaps:
            overlapping_sessions = ActivitySession.objects.filter(
                gym=gym,
                room=room,
                start_datetime__lt=end_dt,
                end_datetime__gt=start_dt
            ).exclude(pk=getattr(session, 'pk', None) if 'session' in locals() else None)
            
            if overlapping_sessions.exists():
                return JsonResponse({
                    'error': f'⚠️ Conflicto: La sala {room.name} ya tiene una clase programada en este horario'
                }, status=400)
        
        # Check staff overlaps if not allowed
        if staff and not settings.allow_staff_overlaps:
            overlapping_staff = ActivitySession.objects.filter(
                gym=gym,
                staff=staff,
                start_datetime__lt=end_dt,
                end_datetime__gt=start_dt
            ).exclude(pk=getattr(session, 'pk', None) if 'session' in locals() else None)
            
            if overlapping_staff.exists():
                staff_name = f"{staff.user.first_name} {staff.user.last_name}".strip()
                return JsonResponse({
                    'error': f'⚠️ Conflicto: {staff_name} ya tiene una clase asignada en este horario'
                }, status=400)
        
        # Check minimum break between classes for same staff
        if staff and settings.min_break_between_classes > 0:
            break_minutes = settings.min_break_between_classes
            break_start = start_dt - timedelta(minutes=break_minutes)
            break_end = end_dt + timedelta(minutes=break_minutes)
            
            nearby_classes = ActivitySession.objects.filter(
                gym=gym,
                staff=staff,
                start_datetime__gte=break_start,
                end_datetime__lte=break_end
            ).exclude(pk=getattr(session, 'pk', None) if 'session' in locals() else None)
            
            if nearby_classes.exists():
                staff_name = f"{staff.user.first_name} {staff.user.last_name}".strip()
                return JsonResponse({
                    'error': f'⚠️ Conflicto: {staff_name} necesita al menos {break_minutes} minutos de descanso entre clases'
                }, status=400)
        
        session = ActivitySession.objects.create(
            gym=gym,
            activity=activity,
            room=room,
            staff=staff,
            start_datetime=start_dt,
            end_datetime=end_dt,
            max_capacity=room.capacity if room else activity.base_capacity
        )
        return JsonResponse({'status': 'ok', 'id': session.id})
        
    elif type == 'recurring':
        days = data.getlist('days') # List of strings '0', '1'...
        end_date_str = data.get('end_date')
        
        if not days or not end_date_str:
             return JsonResponse({'error': 'Faltan días o fecha fin para recurrencia'}, status=400)
             
        if not start_str:
             return JsonResponse({'error': 'Falta hora de inicio'}, status=400)
             
        ref_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        start_time = ref_dt.time()
        end_time = (ref_dt + timedelta(minutes=activity.duration)).time()
        
        # Create Rule(s) - One per day selected
        created_count = 0
        
        for day in days:
            rule = ScheduleRule.objects.create(
                gym=gym,
                activity=activity,
                room=room,
                staff=staff,
                day_of_week=int(day),
                start_time=start_time,
                end_time=end_time,
                start_date=timezone.now().date(),
                end_date=end_date_str
            )
            
            # Generate Sessions
            current_date = rule.start_date
            try:
                end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                 return JsonResponse({'error': 'Fecha fin inválida'}, status=400)

            while current_date <= end_date_obj:
                if current_date.weekday() == rule.day_of_week:
                    s_dt = datetime.combine(current_date, rule.start_time)
                    e_dt = datetime.combine(current_date, rule.end_time)
                    
                    ActivitySession.objects.create(
                        gym=gym,
                        activity=activity,
                        rule=rule,
                        room=room,
                        staff=staff,
                        start_datetime=s_dt,
                        end_datetime=e_dt,
                        max_capacity=room.capacity if room else activity.base_capacity
                    )
                    created_count += 1
                    
                current_date += timedelta(days=1)
                
        return JsonResponse({'status': 'ok', 'created': created_count})

    return JsonResponse({'error': 'Tipo inválido'}, status=400)


@login_required
def update_session_api(request):
    """
    Handles Drag & Drop updates (Time changes).
    Supports 'single' (this instance) vs 'future' (this + future recurring).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        import json
        data = json.loads(request.body)
        
        event_id = data.get('id')
        new_start = data.get('start')
        new_end = data.get('end')
        mode = data.get('mode', 'single')
        
        if not event_id or not new_start:
             return JsonResponse({'error': 'Datos incompletos'}, status=400)

        # Parse Event ID
        if event_id.startswith('sess_'):
            pk = event_id.split('_')[1]
            
            from django.shortcuts import get_object_or_404
            from .models import ActivitySession
            session = get_object_or_404(ActivitySession, pk=pk, gym=request.gym)
            
            # Parse Dates
            try:
                start_dt = datetime.fromisoformat(new_start.replace('Z', '+00:00'))
                if new_end:
                    end_dt = datetime.fromisoformat(new_end.replace('Z', '+00:00'))
                else:
                    # Default duration if not provided
                    end_dt = start_dt + timedelta(minutes=session.activity.duration)
            except ValueError as e:
                return JsonResponse({'error': f'Error de formato de fecha: {str(e)}'}, status=400)
                
            if mode == 'single' or not session.rule:
                # Just update this session
                session.start_datetime = start_dt
                session.end_datetime = end_dt
                session.save()
                return JsonResponse({'status': 'ok', 'msg': 'Sesión actualizada'})
                
            elif mode == 'future' and session.rule:
                # Update Rule + Future Sessions
                rule = session.rule
                
                # 1. Update Rule Times
                rule.start_time = start_dt.time()
                rule.end_time = end_dt.time()
                rule.day_of_week = start_dt.weekday()
                rule.save()
                
                # 2. Update Future Sessions
                target_sessions = ActivitySession.objects.filter(
                    rule=rule,
                    start_datetime__gte=session.start_datetime
                )
                
                count = 0
                for s in target_sessions:
                    s.start_datetime = datetime.combine(s.start_datetime.date(), start_dt.time())
                    s.end_datetime = datetime.combine(s.end_datetime.date(), end_dt.time())
                    s.save()
                    count += 1
                    
                return JsonResponse({'status': 'ok', 'msg': f'Actualizadas {count} sesiones futuras'})

        return JsonResponse({'error': f'Evento no soportado: {event_id}'}, status=400)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)
