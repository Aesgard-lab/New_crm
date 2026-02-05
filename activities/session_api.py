"""
Session Detail API for Class Modal
Provides endpoints for managing individual activity sessions.
"""
import json
from datetime import timedelta
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.utils import timezone

from .models import ActivitySession, WaitlistEntry, SessionCheckin
from clients.models import ClientVisit
from clients.models import Client


@login_required
@require_GET
def get_sessions_list(request):
    """
    API para obtener sesiones de un día específico en formato lista.
    Usado por la vista de listado del calendario.
    
    Query params:
        - date: YYYY-MM-DD (requerido)
        - staff: ID del instructor (opcional)
        - room: ID de la sala (opcional)
    """
    from datetime import datetime
    
    gym = request.gym
    date_str = request.GET.get('date')
    staff_id = request.GET.get('staff')
    room_id = request.GET.get('room')
    
    if not date_str:
        return JsonResponse({'error': 'Se requiere el parámetro date'}, status=400)
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}, status=400)
    
    # Base query
    sessions = ActivitySession.objects.filter(
        gym=gym,
        start_datetime__date=target_date
    ).select_related(
        'activity', 'room', 'staff', 'staff__user'
    ).prefetch_related(
        'attendees'
    ).order_by('start_datetime')
    
    # Filtros opcionales
    if staff_id:
        sessions = sessions.filter(staff_id=staff_id)
    if room_id:
        sessions = sessions.filter(room_id=room_id)
    
    # Estadísticas del día
    total_attendees = 0
    total_checked_in = 0
    
    sessions_data = []
    for session in sessions:
        # Calcular check-ins para esta sesión
        checked_in_count = SessionCheckin.objects.filter(session=session).count()
        booked_count = session.attendee_count
        capacity = session.max_capacity or session.activity.default_capacity or 20
        
        total_attendees += booked_count
        total_checked_in += checked_in_count
        
        # Determinar nombre del instructor
        instructor_name = None
        if session.staff and session.staff.user:
            user = session.staff.user
            if user.first_name or user.last_name:
                instructor_name = f"{user.first_name} {user.last_name}".strip()
            else:
                instructor_name = user.email.split('@')[0]
        
        # Calcular duration desde end_datetime - start_datetime
        if session.end_datetime:
            duration = int((session.end_datetime - session.start_datetime).total_seconds() / 60)
            end_datetime = session.end_datetime
        else:
            duration = session.activity.duration or 60
            end_datetime = session.start_datetime + timedelta(minutes=duration)
        
        sessions_data.append({
            'id': session.id,
            'activity_name': session.activity.name,
            'activity_id': session.activity.id,
            'color': session.activity.color or '#3B82F6',
            'start_time': session.start_datetime.strftime('%H:%M'),
            'end_time': end_datetime.strftime('%H:%M'),
            'duration': duration,
            'room_id': session.room.id if session.room else None,
            'room_name': session.room.name if session.room else None,
            'instructor_id': session.staff.id if session.staff else None,
            'instructor_name': instructor_name,
            'capacity': capacity,
            'booked': booked_count,
            'checked_in': checked_in_count,
            'status': session.status,
            'is_full': booked_count >= capacity,
            'utilization': round((booked_count / capacity) * 100) if capacity > 0 else 0,
        })
    
    # Calcular porcentaje de asistencia
    attendance_percentage = 0
    if total_attendees > 0:
        attendance_percentage = (total_checked_in / total_attendees) * 100
    
    return JsonResponse({
        'date': date_str,
        'sessions': sessions_data,
        'stats': {
            'total': total_attendees,
            'attended': total_checked_in,
            'percentage': attendance_percentage,
            'sessions_count': len(sessions_data),
        }
    })


def _get_cancelled_late_ids(session):
    return set(
        ClientVisit.objects.filter(
            client__in=session.attendees.all(),
            date=session.start_datetime.date(),
            status='CANCELLED',
            cancellation_type='LATE'
        ).values_list('client_id', flat=True)
    )


def _get_payment_status(client, session, active_membership, booking):
    """
    Determina el estado de pago del cliente para esta sesión.
    Retorna:
        - 'PAID': Cliente tiene acceso pagado (membresía, bono, pago individual)
        - 'UNPAID': Cliente no tiene forma de pago válida
        - 'COURTESY': Apuntado por staff sin pago (cortesía/invitado)
    """
    from clients.models import ClientMembership
    from memberships.models import PlanAccessRule
    from sales.models import OrderItem
    
    # Si tiene membresía activa que incluya esta actividad, está pagado
    if active_membership:
        # Verificar si la membresía incluye esta actividad
        plan_rules = PlanAccessRule.objects.filter(
            plan=active_membership.plan
        )
        
        # Si hay reglas de acceso, verificar si incluye la actividad
        if plan_rules.exists():
            # Verificar si alguna regla incluye la actividad específica o su categoría
            for rule in plan_rules:
                if rule.activities.filter(id=session.activity.id).exists():
                    return 'PAID'
                if rule.activity_categories.filter(id=session.activity.category_id).exists():
                    return 'PAID'
        else:
            # Sin reglas específicas = acceso total
            return 'PAID'
    
    # Verificar si tiene un bono/pack activo que incluya esta actividad
    active_packs = ClientMembership.objects.filter(
        client=client,
        status='ACTIVE',
        plan__is_recurring=False,  # Bonos/packs no recurrentes
        sessions_remaining__gt=0
    )
    
    for pack in active_packs:
        pack_rules = PlanAccessRule.objects.filter(plan=pack.plan)
        
        if pack_rules.exists():
            for rule in pack_rules:
                if rule.activities.filter(id=session.activity.id).exists():
                    return 'PAID'
                if rule.activity_categories.filter(id=session.activity.category_id).exists():
                    return 'PAID'
        else:
            return 'PAID'
    
    # Verificar si existe un pago individual para esta sesión específica
    # (Buscar en OrderItem de tipo actividad que corresponda a esta sesión)
    individual_payment = OrderItem.objects.filter(
        order__client=client,
        order__status__in=['PAID', 'PARTIALLY_PAID'],
        activity_session=session
    ).exists()
    
    if individual_payment:
        return 'PAID'
    
    # Si no tiene booking o el booking es PENDING, probablemente sea cortesía
    if not booking or booking.status == 'PENDING':
        return 'COURTESY'
    
    # Por defecto, si no hay pago y tiene booking confirmado, es cortesía
    return 'UNPAID' if booking.status == 'CONFIRMED' else 'COURTESY'


def get_session_detail(request, session_id):
    """
    Returns full session details including attendees and waitlist.
    """
    from datetime import timedelta
    from django.db.models import Count, Q
    
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    
    # Get policy for cancellation rules
    policy = session.activity.policy
    
    # Build attendees list with enriched info
    attendees = []
    late_cancel_ids = _get_cancelled_late_ids(session)
    
    # Import booking model
    from .models import ActivitySessionBooking
    
    for client in session.attendees.all():
        # Get booking record for attendance tracking
        booking = ActivitySessionBooking.objects.filter(
            session=session,
            client=client
        ).first()
        
        # Get last note for this client
        last_note = client.notes.order_by('-created_at').first()
        note_info = None
        if last_note:
            note_info = {
                'content': last_note.text[:200],  # First 200 chars
                'created_at': last_note.created_at.isoformat(),
                'author': f"{last_note.author.first_name} {last_note.author.last_name}" if last_note.author else 'Sistema',
                'type': last_note.type,
            }
        
        # Calculate attendance statistics
        total_visits = client.visits.filter(status__in=['ATTENDED', 'NOSHOW']).count()
        attended_visits = client.visits.filter(status='ATTENDED').count()
        attendance_rate = round((attended_visits / total_visits * 100) if total_visits > 0 else 0)
        
        # Check for active membership
        active_membership = client.memberships.filter(status='ACTIVE').first()
        membership_info = None
        if active_membership:
            membership_info = {
                'name': active_membership.name,
                'is_recurring': active_membership.is_recurring,
                'sessions_remaining': active_membership.sessions_remaining,
                'sessions_total': active_membership.sessions_total,
            }
        
        # Determine payment status
        payment_status = _get_payment_status(client, session, active_membership, booking)
        
        # Check if this is a recurring booking
        is_recurring = False
        future_sessions_count = 0
        if session.rule:  # If session belongs to a recurring rule
            # Check if client is in future sessions of this rule
            future_sessions = ActivitySession.objects.filter(
                rule=session.rule,
                start_datetime__gt=session.start_datetime,
                status='SCHEDULED'
            ).filter(attendees=client)
            future_sessions_count = future_sessions.count()
            is_recurring = future_sessions_count > 0
        
        # Calculate cancellation window
        cancellation_info = None
        if policy:
            hours_until = (session.start_datetime - timezone.now()).total_seconds() / 3600
            can_cancel = hours_until > policy.cancellation_window_hours
            cancellation_info = {
                'can_cancel': can_cancel,
                'window_hours': policy.cancellation_window_hours,
                'deadline': (session.start_datetime - timedelta(hours=policy.cancellation_window_hours)).isoformat(),
                'is_late': not can_cancel and hours_until > 0,
            }
        
        # Check ClientVisit for this session
        visit = client.visits.filter(
            date=session.start_datetime.date(),
            concept__icontains=session.activity.name,
        ).first()
        
        visit_status = None
        if visit:
            visit_status = {
                'status': visit.status,
                'cancellation_type': visit.cancellation_type if visit.status == 'CANCELLED' else None,
            }
        
        attendees.append({
            'id': client.id,
            'booking_id': booking.id if booking else None,
            'name': f"{client.first_name} {client.last_name}",
            'avatar': client.photo.url if client.photo else None,
            'email': client.email,
            'phone': client.phone_number or '',
            'attended': True,  # Default, will need separate tracking
            'attendance_status': booking.attendance_status if booking else 'PENDING',
            'note': note_info,
            'attendance_rate': attendance_rate,
            'total_visits': total_visits,
            'membership': membership_info,
            'payment_status': payment_status,
            'is_recurring': is_recurring,
            'future_sessions_count': future_sessions_count,
            'cancellation': cancellation_info,
            'visit_status': visit_status,
            'is_late_cancel': client.id in late_cancel_ids,
        })
    
    # Build waitlist
    waitlist = []
    for entry in session.waitlist_entries.filter(status='WAITING').order_by('joined_at'):
        waitlist.append({
            'id': entry.id,
            'client_id': entry.client.id,
            'name': f"{entry.client.first_name} {entry.client.last_name}",
            'avatar': entry.client.photo.url if entry.client.photo else None,
            'email': entry.client.email,
            'phone': entry.client.phone_number or '',
            'position': waitlist.__len__() + 1,
            'joined_at': entry.joined_at.isoformat(),
        })
    
    active_attendees_count = len(attendees) - len(late_cancel_ids)

    data = {
        'id': session.id,
        'rule_id': session.rule.id if session.rule else None,
        'activity': {
            'id': session.activity.id,
            'name': session.activity.name,
            'color': session.activity.color,
            'duration': session.activity.duration,
            'description': session.activity.description,
            'allow_waitlist': bool(policy.waitlist_enabled) if policy else False,
        },
        'room': {
            'id': session.room.id,
            'name': session.room.name,
        } if session.room else None,
        'staff': {
            'id': session.staff.id,
            'name': f"{session.staff.user.first_name} {session.staff.user.last_name}",
        } if session.staff else None,
        'start_datetime': session.start_datetime.isoformat(),
        'end_datetime': session.end_datetime.isoformat(),
        'status': session.status,
        'max_capacity': session.max_capacity,
        'attendee_count': active_attendees_count,
        'utilization': round((active_attendees_count / session.max_capacity * 100) if session.max_capacity > 0 else 0),
        'notes': session.notes,
        'attendees': attendees,
        'waitlist': waitlist,
        'has_waitlist': len(waitlist) > 0,
    }
    
    return JsonResponse(data)


@login_required
@require_POST
def add_attendee(request, session_id):
    """
    Add a client to the session attendees.
    """
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    
    try:
        data = json.loads(request.body)
        client_id = data.get('client_id')
    except json.JSONDecodeError:
        client_id = request.POST.get('client_id')
    
    if not client_id:
        return JsonResponse({'error': 'client_id requerido'}, status=400)
    
    client = get_object_or_404(Client, pk=client_id, gym=gym)
    
    # Check capacity using active attendees (excluding late cancellations)
    late_ids = _get_cancelled_late_ids(session)
    active_count = session.attendees.count() - len(late_ids)
    if session.max_capacity > 0 and active_count >= session.max_capacity:
        return JsonResponse({'error': 'Clase llena'}, status=400)
    
    # Check if already in
    if session.attendees.filter(pk=client.pk).exists():
        return JsonResponse({'error': 'Cliente ya está en la clase'}, status=400)
    
    session.attendees.add(client)
    
    # Create booking record for attendance tracking
    from .models import ActivitySessionBooking
    ActivitySessionBooking.objects.get_or_create(
        session=session,
        client=client,
        defaults={
            'status': 'CONFIRMED',
            'attendance_status': 'PENDING'
        }
    )
    
    # Remove from waitlist if present
    WaitlistEntry.objects.filter(session=session, client=client).update(
        status='PROMOTED', promoted_at=timezone.now()
    )
    
    # Send notification
    try:
        from marketing.signals import on_client_added_to_class
        on_client_added_to_class(client, session)
    except Exception as e:
        print("Error sending notification:", str(e))
    
    return JsonResponse({
        'status': 'ok',
        'attendee_count': session.attendees.count() - len(_get_cancelled_late_ids(session))
    })


@login_required
@require_POST
def add_to_waitlist(request, session_id):
    """Add a client to the waitlist for a session."""
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)

    policy = session.activity.policy
    if not (policy and policy.waitlist_enabled):
        return JsonResponse({'error': 'Esta actividad no permite lista de espera'}, status=400)

    try:
        data = json.loads(request.body)
        client_id = data.get('client_id')
    except Exception:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    client = get_object_or_404(Client, pk=client_id, gym=gym)

    # Already in attendees
    if session.attendees.filter(pk=client.pk).exists():
        return JsonResponse({'error': 'Cliente ya está en la clase'}, status=400)

    # Already in waitlist
    if session.waitlist_entries.filter(client=client, status__in=['WAITING', 'NOTIFIED']).exists():
        return JsonResponse({'error': 'Cliente ya está en lista de espera'}, status=400)

    # Verificar si es VIP
    client_is_vip = is_client_vip(client, policy)
    
    entry = WaitlistEntry.objects.create(
        session=session,
        client=client,
        gym=gym,
        status='WAITING',
        joined_at=timezone.now(),
        is_vip=client_is_vip
    )
    
    # Calcular posición en la lista
    position = session.waitlist_entries.filter(
        status__in=['WAITING', 'NOTIFIED']
    ).filter(
        Q(is_vip=True, joined_at__lt=entry.joined_at) |  # VIPs que llegaron antes
        Q(is_vip=False, joined_at__lt=entry.joined_at) if not client_is_vip else Q()  # No-VIPs si no soy VIP
    ).count() + 1
    
    if client_is_vip:
        # Si es VIP, la posición es solo entre VIPs
        position = session.waitlist_entries.filter(
            status__in=['WAITING', 'NOTIFIED'],
            is_vip=True,
            joined_at__lt=entry.joined_at
        ).count() + 1

    return JsonResponse({
        'status': 'ok',
        'entry_id': entry.id,
        'is_vip': client_is_vip,
        'position': position,
        'waitlist_count': session.waitlist_entries.filter(status__in=['WAITING', 'NOTIFIED']).count()
    })


@login_required
@require_POST
def remove_attendee(request, session_id, client_id):
    """
    Remove a client from the session attendees.
    Supports 'mode': 'single' (default) or 'future' to remove from this and all future sessions in the series.
    Also accepts 'cancellation_type': 'EARLY', 'LATE', or 'WAITLIST' to register the cancellation in ClientVisit
    or move to waitlist.
    """
    from clients.models import ClientVisit
    
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    client = get_object_or_404(Client, pk=client_id, gym=gym)
    
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    
    mode = data.get('mode', 'single')
    cancellation_type = data.get('cancellation_type', 'EARLY')
    
    # Determine which sessions to remove from
    sessions_to_update = [session]
    if mode == 'future' and session.rule:
        # Get all future sessions in the same series where client is attendee
        future_sessions = ActivitySession.objects.filter(
            rule=session.rule,
            start_datetime__gte=session.start_datetime,
            status='SCHEDULED',
            gym=gym,
            attendees=client
        )
        sessions_to_update = list(future_sessions)
    
    # Check if moving to waitlist instead of cancelling
    if cancellation_type == 'WAITLIST':
        # Move client to waitlist instead of removing
        moved_count = 0
        for sess in sessions_to_update:
            # Check if waitlist is enabled for this activity
            sess_policy = sess.activity.policy
            if not sess_policy or not sess_policy.waitlist_enabled:
                continue
            
            # Remove from attendees
            sess.attendees.remove(client)
            
            # Add to waitlist if not already there
            waitlist_entry, created = WaitlistEntry.objects.get_or_create(
                session=sess,
                client=client,
                defaults={'status': 'WAITING'}
            )
            if not created:
                # If entry exists but was promoted/expired, reactivate it
                waitlist_entry.status = 'WAITING'
                waitlist_entry.save()
            
            moved_count += 1
            
            # Auto-promote from waitlist if there's someone else waiting
            late_ids = _get_cancelled_late_ids(sess)
            active_count = sess.attendees.count() - len(late_ids)
            if active_count < sess.max_capacity:
                # Get first person in line (excluding the one we just added) - VIPs primero
                first_in_line = sess.waitlist_entries.filter(status='WAITING').exclude(client=client).order_by('-is_vip', 'joined_at').first()
                if first_in_line:
                    sess.attendees.add(first_in_line.client)
                    first_in_line.status = 'PROMOTED'
                    first_in_line.promoted_at = timezone.now()
                    first_in_line.save()
        
        return JsonResponse({
            'status': 'ok',
            'moved_to_waitlist': moved_count,
            'message': f"✅ Cliente movido a lista de espera en {moved_count} clase(s)"
        })
    
    # Standard cancellation flow (EARLY or LATE)
    removed_count = 0
    promoted_count = 0
    notified_info = None
    
    for sess in sessions_to_update:
        # Create or update the ClientVisit as cancelled
        visit, created = ClientVisit.objects.get_or_create(
            client=client,
            date=sess.start_datetime.date(),
            defaults={
                'status': 'CANCELLED',
                'cancellation_type': cancellation_type,
                'concept': f"{sess.activity.name}",
                'staff': sess.staff
            }
        )
        if not created:
            # Update existing visit
            visit.status = 'CANCELLED'
            visit.cancellation_type = cancellation_type
            visit.save()

        # Late cancellation: keep in attendees list (for visibility) but mark as cancelled; free capacity via active count
        if cancellation_type != 'LATE':
            sess.attendees.remove(client)
            removed_count += 1
        else:
            # Count as removed for messaging but keep visible
            removed_count += 1

        # Procesar lista de espera según el modo configurado
        late_ids = _get_cancelled_late_ids(sess)
        active_count = sess.attendees.count() - len(late_ids)
        sess_policy = sess.activity.policy
        
        if sess_policy and sess_policy.waitlist_enabled and active_count < sess.max_capacity:
            waitlist_mode = sess_policy.waitlist_mode
            
            if waitlist_mode == 'AUTO_PROMOTE':
                # Modo tradicional: promoción automática al primero (VIPs primero)
                first_in_line = sess.waitlist_entries.filter(status='WAITING').order_by('-is_vip', 'joined_at').first()
                if first_in_line:
                    sess.attendees.add(first_in_line.client)
                    first_in_line.status = 'PROMOTED'
                    first_in_line.promoted_at = timezone.now()
                    first_in_line.save()
                    promoted_count += 1
                    
                    # Crear booking
                    from .models import ActivitySessionBooking
                    ActivitySessionBooking.objects.get_or_create(
                        session=sess,
                        client=first_in_line.client,
                        defaults={'status': 'BOOKED', 'attendance_status': 'PENDING'}
                    )
                    
                    # Notificar
                    try:
                        from marketing.signals import send_class_notification
                        send_class_notification(
                            client=first_in_line.client,
                            event_type='WAITLIST_PROMOTED',
                            session=sess
                        )
                    except Exception as e:
                        print(f"Error sending promotion notification: {e}")
            
            elif waitlist_mode in ['BROADCAST', 'FIRST_CLAIM']:
                # Nuevos modos: notificar para que reclamen (VIPs se auto-promocionan)
                notified_info = notify_waitlist_for_claim(sess, exclude_client_id=client.id)
                if notified_info and notified_info.get('promoted'):
                    promoted_count += 1

    active_attendee_count = session.attendees.count() - len(_get_cancelled_late_ids(session))
    response_data = {
        'status': 'ok',
        'removed': removed_count,
        'attendee_count': active_attendee_count
    }

    if promoted_count > 0:
        response_data['promoted'] = promoted_count
        response_data['message'] = f"✅ {promoted_count} cliente(s) promovido(s) desde lista de espera"

    return JsonResponse(response_data)


@login_required
@require_POST
def mark_attendance(request, session_id):
    """
    Bulk mark attendance for the session.
    Expects: { "attendance": { "client_id": true/false, ... } }
    """
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    
    try:
        data = json.loads(request.body)
        attendance_data = data.get('attendance', {})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    # For now, we'll store attendance in session notes or create a separate model later
    # This is a simplified version - in production you'd want an AttendanceRecord model
    session.notes = f"Attendance marked at {timezone.now().isoformat()}"
    session.save()
    
    return JsonResponse({'status': 'ok', 'marked': len(attendance_data)})


@login_required
@require_POST
def cancel_session(request, session_id):
    """
    Cancel a session (single or future).
    Expects: { "mode": "single" | "future" }
    """
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    
    try:
        data = json.loads(request.body)
        mode = data.get('mode', 'single')
    except json.JSONDecodeError:
        mode = 'single'
    
    if mode == 'single':
        session.status = 'CANCELLED'
        session.save()
        count = 1
    elif mode == 'future' and session.rule:
        count = ActivitySession.objects.filter(
            rule=session.rule,
            start_datetime__gte=session.start_datetime
        ).update(status='CANCELLED')
    else:
        session.status = 'CANCELLED'
        session.save()
        count = 1
    
    return JsonResponse({'status': 'ok', 'cancelled': count})


@login_required
@require_POST
def update_session(request, session_id):
    """
    Update session details (staff, room, capacity, notes, date, time).
    Supports 'mode': 'single' (default) or 'future' to update this and all future sessions in the series.
    """
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    mode = data.get('mode', 'single')
    
    # Determine which sessions to update
    sessions_to_update = [session]
    if mode == 'future' and session.rule:
        # Get all future sessions in the same series
        future_sessions = ActivitySession.objects.filter(
            rule=session.rule,
            start_datetime__gte=session.start_datetime,
            status='SCHEDULED',
            gym=gym
        )
        sessions_to_update = list(future_sessions)
    
    # Update all selected sessions
    for sess in sessions_to_update:
        # Update fields if provided
        if 'staff_id' in data:
            from staff.models import StaffProfile
            if data['staff_id']:
                sess.staff = get_object_or_404(StaffProfile, pk=data['staff_id'], gym=gym)
            else:
                sess.staff = None
        
        if 'room_id' in data:
            from .models import Room
            if data['room_id']:
                sess.room = get_object_or_404(Room, pk=data['room_id'], gym=gym)
            else:
                sess.room = None
        
        if 'max_capacity' in data:
            sess.max_capacity = int(data['max_capacity'])
        
        if 'notes' in data:
            sess.notes = data['notes']
        
        # Update date and time if provided
        if 'date' in data and 'start_time' in data and 'end_time' in data:
            from datetime import datetime
            import pytz
            
            # Get timezone from gym settings or default to Europe/Madrid
            tz = pytz.timezone('Europe/Madrid')
            
            # Parse date and times
            date_str = data['date']  # YYYY-MM-DD
            start_time_str = data['start_time']  # HH:MM
            end_time_str = data['end_time']  # HH:MM
            
            # Create datetime objects
            start_datetime_naive = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
            end_datetime_naive = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")
            
            # Make timezone aware
            sess.start_datetime = tz.localize(start_datetime_naive)
            sess.end_datetime = tz.localize(end_datetime_naive)
        
        sess.save()
    
    return JsonResponse({
        'status': 'ok',
        'updated': len(sessions_to_update)
    })


@login_required
@require_POST
def promote_waitlist(request, session_id, entry_id):
    """
    Promote a waitlist entry to attendee.
    """
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    entry = get_object_or_404(WaitlistEntry, pk=entry_id, session=session)
    
    # Check capacity
    if session.max_capacity > 0 and session.attendees.count() >= session.max_capacity:
        return JsonResponse({'error': 'Clase llena, no se puede promocionar'}, status=400)
    
    # Add to attendees
    session.attendees.add(entry.client)
    
    # Update waitlist entry
    entry.status = 'PROMOTED'
    entry.promoted_at = timezone.now()
    entry.save()
    
    return JsonResponse({
        'status': 'ok',
        'client_name': f"{entry.client.first_name} {entry.client.last_name}",
        'attendee_count': session.attendees.count()
    })


@login_required
@require_POST
def remove_from_waitlist(request, session_id, entry_id):
    """
    Remove a client from the waitlist.
    """
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    entry = get_object_or_404(WaitlistEntry, pk=entry_id, session=session)
    
    entry.status = 'CANCELLED'
    entry.save()
    
    return JsonResponse({'status': 'ok'})


@login_required
@require_GET
def search_clients_for_session(request, session_id):
    """
    Search clients to add to a session.
    Returns clients not already in the session.
    """
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'clients': []})
    
    # Exclude clients already in class
    existing_ids = session.attendees.values_list('id', flat=True)
    
    clients = Client.objects.filter(
        gym=gym, status='ACTIVE'
    ).exclude(
        id__in=existing_ids
    ).filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    )[:10]
    
    results = [{
        'id': c.id,
        'name': f"{c.first_name} {c.last_name}",
        'email': c.email,
        'avatar': c.photo.url if c.photo else None,
    } for c in clients]
    
    return JsonResponse({'clients': results})


@login_required
@require_POST
def mark_attendance(request, session_id):
    """
    Mark attendance status for a single client or all clients in a session.
    """
    from .models import ActivitySessionBooking
    from staff.models import StaffProfile
    
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    
    try:
        data = json.loads(request.body)
        client_id = data.get('client_id')
        status = data.get('status')  # ATTENDED, NO_SHOW, LATE_CANCEL
        mark_all = data.get('mark_all', False)
        
        if not status or status not in ['ATTENDED', 'NO_SHOW', 'LATE_CANCEL']:
            return JsonResponse({'error': 'Estado inválido'}, status=400)
        
        # Get staff profile if exists
        staff = None
        if hasattr(request.user, 'staff_profile'):
            staff = request.user.staff_profile
        
        if mark_all and status == 'ATTENDED':
            # Mark all confirmed bookings as attended
            bookings = ActivitySessionBooking.objects.filter(
                session=session,
                status='CONFIRMED'
            )
            count = 0
            for booking in bookings:
                booking.mark_attendance(status, staff)
                count += 1
            
            return JsonResponse({
                'success': True,
                'message': f'{count} asistencias marcadas',
                'marked_count': count
            })
        
        elif client_id:
            # Mark single client
            client = get_object_or_404(Client, pk=client_id, gym=gym)
            
            # Get or create booking
            booking, created = ActivitySessionBooking.objects.get_or_create(
                session=session,
                client=client,
                defaults={'status': 'CONFIRMED'}
            )
            
            booking.mark_attendance(status, staff)
            
            return JsonResponse({
                'success': True,
                'message': 'Asistencia actualizada',
                'client_id': client_id,
                'status': status
            })
        
        else:
            return JsonResponse({'error': 'client_id requerido o mark_all=true'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def is_client_vip(client, policy):
    """
    Verifica si un cliente es VIP según la política.
    Un cliente es VIP si:
    - Pertenece a un grupo VIP configurado en la política
    - Tiene una membresía activa de un plan VIP configurado en la política
    """
    if not policy:
        return False
    
    # Verificar grupos VIP
    vip_group_ids = list(policy.vip_groups.values_list('id', flat=True))
    if vip_group_ids and client.groups.filter(id__in=vip_group_ids).exists():
        return True
    
    # Verificar planes VIP
    vip_plan_ids = list(policy.vip_membership_plans.values_list('id', flat=True))
    if vip_plan_ids:
        active_membership = client.memberships.filter(
            status='ACTIVE',
            plan_id__in=vip_plan_ids
        ).exists()
        if active_membership:
            return True
    
    return False


@login_required
@require_POST
def claim_waitlist_spot(request, session_id):
    """
    Endpoint para que un cliente reclame una plaza disponible desde la lista de espera.
    Usado en modos BROADCAST y FIRST_CLAIM.
    
    El cliente debe estar en estado NOTIFIED (ya fue notificado de que hay plaza).
    """
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    
    try:
        data = json.loads(request.body)
        client_id = data.get('client_id')
    except Exception:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    if not client_id:
        return JsonResponse({'error': 'client_id requerido'}, status=400)
    
    client = get_object_or_404(Client, pk=client_id, gym=gym)
    policy = session.activity.policy
    
    # Buscar la entrada en lista de espera
    entry = WaitlistEntry.objects.filter(
        session=session,
        client=client,
        status__in=['WAITING', 'NOTIFIED']
    ).first()
    
    if not entry:
        return JsonResponse({'error': 'No estás en la lista de espera de esta clase'}, status=400)
    
    # Verificar si hay plaza disponible
    late_ids = _get_cancelled_late_ids(session)
    active_count = session.attendees.count() - len(late_ids)
    
    if active_count >= session.max_capacity:
        return JsonResponse({
            'error': 'Lo sentimos, la plaza ya fue reclamada por otro cliente',
            'code': 'SPOT_TAKEN'
        }, status=409)
    
    # Verificar timeout si aplica
    if entry.claim_expires_at and timezone.now() > entry.claim_expires_at:
        entry.status = 'EXPIRED'
        entry.save()
        return JsonResponse({
            'error': 'El tiempo para reclamar la plaza ha expirado',
            'code': 'CLAIM_EXPIRED'
        }, status=400)
    
    # Añadir a la clase
    session.attendees.add(client)
    
    # Actualizar entrada de lista de espera
    entry.status = 'PROMOTED'
    entry.promoted_at = timezone.now()
    entry.claimed_at = timezone.now()
    entry.save()
    
    # Crear booking record
    from .models import ActivitySessionBooking
    ActivitySessionBooking.objects.get_or_create(
        session=session,
        client=client,
        defaults={'status': 'BOOKED', 'attendance_status': 'PENDING'}
    )
    
    # Notificar al cliente
    try:
        from marketing.signals import send_class_notification
        send_class_notification(
            client=client,
            event_type='WAITLIST_PROMOTED',
            session=session
        )
    except Exception as e:
        print(f"Error sending claim notification: {e}")
    
    return JsonResponse({
        'status': 'ok',
        'message': '¡Plaza reclamada con éxito! Ya estás en la clase.',
        'attendee_count': session.attendees.count() - len(_get_cancelled_late_ids(session))
    })


def notify_waitlist_for_claim(session, exclude_client_id=None):
    """
    Notifica a la lista de espera que hay una plaza disponible para reclamar.
    Usado en modos BROADCAST y FIRST_CLAIM.
    
    - VIPs: Se promocionan automáticamente (siempre ganan)
    - No-VIPs: Se les notifica y compiten por reclamar
    """
    from marketing.signals import send_class_notification
    from datetime import timedelta
    
    policy = session.activity.policy
    if not policy or not policy.waitlist_enabled:
        return None
    
    # Obtener lista de espera ordenada (VIPs primero, luego por orden de llegada)
    waitlist = WaitlistEntry.objects.filter(
        session=session,
        status='WAITING'
    ).order_by('-is_vip', 'joined_at')
    
    if exclude_client_id:
        waitlist = waitlist.exclude(client_id=exclude_client_id)
    
    if not waitlist.exists():
        return None
    
    # El primero de la lista
    first_entry = waitlist.first()
    
    # Si es VIP, promoción automática
    if first_entry.is_vip:
        session.attendees.add(first_entry.client)
        first_entry.status = 'PROMOTED'
        first_entry.promoted_at = timezone.now()
        first_entry.save()
        
        # Crear booking
        from .models import ActivitySessionBooking
        ActivitySessionBooking.objects.get_or_create(
            session=session,
            client=first_entry.client,
            defaults={'status': 'BOOKED', 'attendance_status': 'PENDING'}
        )
        
        # Notificar promoción VIP
        send_class_notification(
            client=first_entry.client,
            event_type='WAITLIST_PROMOTED',
            session=session
        )
        
        return {'promoted': first_entry.client.id, 'is_vip': True}
    
    # Si no es VIP, depende del modo
    timeout_minutes = policy.waitlist_claim_timeout_minutes or 30
    claim_expires = timezone.now() + timedelta(minutes=timeout_minutes)
    
    if policy.waitlist_mode == 'FIRST_CLAIM':
        # Notificar a TODOS en la lista
        entries_to_notify = waitlist
    else:
        # BROADCAST: Notificar solo a los primeros X
        from marketing.models import ClassNotificationSettings
        settings, _ = ClassNotificationSettings.objects.get_or_create(gym=session.gym)
        entries_to_notify = waitlist[:settings.waitlist_broadcast_count]
    
    notified_ids = []
    for entry in entries_to_notify:
        entry.status = 'NOTIFIED'
        entry.notified_at = timezone.now()
        entry.claim_expires_at = claim_expires
        entry.save()
        notified_ids.append(entry.client.id)
        
        # Enviar notificación
        send_class_notification(
            client=entry.client,
            event_type='WAITLIST_SPOT_AVAILABLE',
            session=session,
            timeout_minutes=timeout_minutes
        )
    
    return {'notified': notified_ids, 'expires_at': claim_expires.isoformat()}


@login_required
@require_GET
def get_attendance_status(request, session_id):
    """
    Get attendance status for all clients in a session.
    """
    from .models import ActivitySessionBooking
    
    gym = request.gym
    session = get_object_or_404(ActivitySession, pk=session_id, gym=gym)
    
    bookings = ActivitySessionBooking.objects.filter(
        session=session
    ).select_related('client', 'marked_by')
    
    attendance_list = []
    for booking in bookings:
        attendance_list.append({
            'client_id': booking.client.id,
            'client_name': f"{booking.client.first_name} {booking.client.last_name}",
            'status': booking.status,
            'attendance_status': booking.attendance_status,
            'marked_at': booking.marked_at.isoformat() if booking.marked_at else None,
            'marked_by': f"{booking.marked_by.user.first_name} {booking.marked_by.user.last_name}" if booking.marked_by else None,
        })
    
    return JsonResponse({
        'session_id': session_id,
        'attendance': attendance_list
    })


@require_GET
def get_session_spots(request, session_id):
    """
    API para obtener el layout de la sala y los puestos disponibles/ocupados de una sesión.
    Usado para el selector visual de puestos.
    
    Returns:
        - layout: Configuración del layout de la sala
        - spots: Lista de puestos con su estado (available/occupied)
        - allow_spot_booking: Si la actividad permite reserva de puesto
    """
    from .models import ActivitySessionBooking
    
    session = get_object_or_404(ActivitySession, pk=session_id)
    activity = session.activity
    room = session.room
    
    # Verificar si la actividad permite spot booking
    if not activity.allow_spot_booking:
        return JsonResponse({
            'allow_spot_booking': False,
            'message': 'Esta actividad no permite selección de puesto'
        })
    
    # Verificar si la sala tiene layout configurado
    if not room or not room.layout_configuration:
        return JsonResponse({
            'allow_spot_booking': True,
            'has_layout': False,
            'message': 'La sala no tiene un layout configurado'
        })
    
    # Obtener el layout
    try:
        layout_items = room.layout_configuration if isinstance(room.layout_configuration, list) else json.loads(room.layout_configuration)
    except (json.JSONDecodeError, TypeError):
        layout_items = []
    
    # Obtener los puestos ocupados
    occupied_spots = set(
        ActivitySessionBooking.objects.filter(
            session=session,
            status__in=['CONFIRMED', 'PENDING'],
            spot_number__isnull=False
        ).values_list('spot_number', flat=True)
    )
    
    # Construir lista de puestos con estado
    spots = []
    for item in layout_items:
        if item.get('type') == 'spot':
            spot_number = item.get('number')
            spots.append({
                'number': spot_number,
                'x': item.get('x'),
                'y': item.get('y'),
                'status': 'occupied' if spot_number in occupied_spots else 'available'
            })
    
    # Obtener obstáculos también (para renderizar el layout completo)
    obstacles = [
        {'x': item.get('x'), 'y': item.get('y')}
        for item in layout_items if item.get('type') == 'obstacle'
    ]
    
    return JsonResponse({
        'allow_spot_booking': True,
        'has_layout': True,
        'session_id': session_id,
        'room_name': room.name,
        'activity_name': activity.name,
        'spots': spots,
        'obstacles': obstacles,
        'total_spots': len(spots),
        'available_spots': len([s for s in spots if s['status'] == 'available']),
        'occupied_spots': len(occupied_spots)
    })


@require_POST
def reserve_spot(request, session_id):
    """
    API para reservar un puesto específico en una sesión.
    Si el cliente ya tiene una reserva sin puesto, actualiza el puesto.
    Si no tiene reserva, crea una nueva con el puesto.
    
    Body:
        - client_id: ID del cliente
        - spot_number: Número de puesto a reservar
    """
    from .models import ActivitySessionBooking
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    
    client_id = data.get('client_id')
    spot_number = data.get('spot_number')
    
    if not client_id or not spot_number:
        return JsonResponse({'success': False, 'error': 'Faltan parámetros'}, status=400)
    
    session = get_object_or_404(ActivitySession, pk=session_id)
    client = get_object_or_404(Client, pk=client_id)
    
    # Verificar que la actividad permite spot booking
    if not session.activity.allow_spot_booking:
        return JsonResponse({
            'success': False, 
            'error': 'Esta actividad no permite selección de puesto'
        }, status=400)
    
    # Verificar que el puesto no esté ocupado
    existing_booking = ActivitySessionBooking.objects.filter(
        session=session,
        spot_number=spot_number,
        status__in=['CONFIRMED', 'PENDING']
    ).exclude(client=client).first()
    
    if existing_booking:
        return JsonResponse({
            'success': False,
            'error': f'El puesto #{spot_number} ya está ocupado',
            'code': 'SPOT_TAKEN'
        }, status=409)
    
    # Verificar si el cliente ya tiene una reserva
    booking = ActivitySessionBooking.objects.filter(
        session=session,
        client=client,
        status__in=['CONFIRMED', 'PENDING']
    ).first()
    
    if booking:
        # Actualizar el puesto de la reserva existente
        old_spot = booking.spot_number
        booking.spot_number = spot_number
        booking.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Puesto actualizado de #{old_spot or "ninguno"} a #{spot_number}',
            'booking_id': booking.id,
            'spot_number': spot_number
        })
    else:
        # Crear nueva reserva con el puesto
        # Primero verificar que haya capacidad
        current_count = session.attendee_count
        max_capacity = session.max_capacity or session.activity.base_capacity
        
        if current_count >= max_capacity:
            return JsonResponse({
                'success': False,
                'error': 'La sesión está llena',
                'code': 'SESSION_FULL'
            }, status=409)
        
        # Crear la reserva
        booking = ActivitySessionBooking.objects.create(
            session=session,
            client=client,
            spot_number=spot_number,
            status='CONFIRMED'
        )
        
        # Añadir al M2M de attendees
        session.attendees.add(client)
        
        return JsonResponse({
            'success': True,
            'message': f'Reserva creada con puesto #{spot_number}',
            'booking_id': booking.id,
            'spot_number': spot_number
        })


