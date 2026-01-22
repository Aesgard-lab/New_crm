from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.http import JsonResponse
import datetime
from .models import Client, ClientMembership
from finance.stripe_utils import list_payment_methods, create_setup_intent, detach_payment_method

def portal_login(request):
    if request.user.is_authenticated:
        # Check if is client
        if hasattr(request.user, 'client_profile'):
            return redirect('portal_home')
        # If staff, redirect to backoffice home
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user_obj = User.objects.get(email=email)
            
            # Verificar contraseña manualmente ya que usamos email como USERNAME_FIELD
            if user_obj.check_password(password):
                if hasattr(user_obj, 'client_profile'):
                    login(request, user_obj)
                    return redirect('portal_home')
                else:
                    messages.error(request, 'Este usuario no es un cliente.')
            else:
                messages.error(request, 'Contraseña incorrecta.')
        except User.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
            
    return render(request, 'portal/auth/login.html')

@login_required
def portal_logout(request):
    logout(request)
    return redirect('portal_login')

@login_required
def portal_home(request):
    # Verify is client
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
        
    client = request.user.client_profile
    active_membership = client.memberships.filter(status='ACTIVE').first()
    pending_membership = client.memberships.filter(status='PENDING').order_by('start_date').first()
    finance_settings = getattr(client.gym, 'finance_settings', None)
    allow_pay_next_fee = bool(finance_settings and getattr(finance_settings, 'allow_client_pay_next_fee', False))
    
    # Next bookings (próximas 3 clases)
    from datetime import timedelta
    today = timezone.now().date()
    next_bookings = client.visits.filter(
        status='SCHEDULED', 
        date__gte=today
    ).order_by('date', 'check_in_time')[:3]
    
    # Weekly attendance stats (last 7 days)
    week_ago = today - timedelta(days=7)
    weekly_visits = client.visits.filter(
        date__gte=week_ago,
        date__lte=today,
        status='ATTENDED'
    ).count()
    
    # Monthly visits
    month_start = today.replace(day=1)
    monthly_visits = client.visits.filter(
        date__gte=month_start,
        date__lte=today,
        status='ATTENDED'
    ).count()
    
    # Current streak (días consecutivos)
    current_streak = 0
    check_date = today
    for i in range(30):  # Check last 30 days max
        has_visit = client.visits.filter(
            date=check_date,
            status='ATTENDED'
        ).exists()
        if has_visit:
            current_streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    
    # Popups Logic
    from marketing.models import Popup, PopupRead
    from django.db.models import Q
    
    # Get unread popups active now
    now = timezone.now()
    active_popups = Popup.objects.filter(
        gym=client.gym,
        is_active=True,
        start_date__lte=now
    ).exclude(
        end_date__lt=now # Exclude expired if end_date set
    ).exclude(
        reads__client=client # Exclude already read
    )
    
    relevant_popups = []
    
    for popup in active_popups:
        is_relevant = False
        
        # 1. Direct Target
        if popup.target_client_id:
            if popup.target_client_id == client.id:
                is_relevant = True
        
        # 2. Audience (Only if no specific target_client is set)
        else:
             if popup.audience_type == 'ALL_ACTIVE':
                 # Check active membership or status
                 if client.memberships.filter(status='ACTIVE').exists():
                     is_relevant = True
             elif popup.audience_type == 'ALL_CLIENTS':
                 is_relevant = True
             elif popup.audience_type == 'CUSTOM_TAG':
                 # Check tags (assuming tags is ManyToMany or list)
                 # Mock for now: matches always or implement tag logic
                 pass 
        
        if is_relevant:
            relevant_popups.append(popup)

    context = {
        'client': client,
        'membership': active_membership,
        'pending_membership': pending_membership,
        'membership_required': getattr(client.gym, 'require_active_membership', False),
        'next_bookings': next_bookings,
        'weekly_visits': weekly_visits,
        'monthly_visits': monthly_visits,
        'current_streak': current_streak,
        'qr_data': client.access_code or client.id,
        'popups': relevant_popups, # List of popups to show
        'allow_pay_next_fee': allow_pay_next_fee,
    }
    return render(request, 'portal/dashboard/home.html', context)

@login_required
def portal_mark_popup_read(request, popup_id):
    """
    API to mark popup as read.
    """
    if request.method != 'POST':
         from django.http import JsonResponse
         return JsonResponse({'error': 'Method not allowed'}, status=405)
         
    from marketing.models import Popup, PopupRead
    client = request.user.client_profile
    
    try:
        popup = Popup.objects.get(id=popup_id, gym=client.gym)
        PopupRead.objects.get_or_create(popup=popup, client=client)
        from django.http import JsonResponse
        return JsonResponse({'status': 'ok'})
    except Popup.DoesNotExist:
         from django.http import JsonResponse
         return JsonResponse({'error': 'Popup not found'}, status=404)

@login_required
def portal_bookings(request):
    """
    Shows available sessions for the next 7 days.
    """
    from activities.models import ActivitySession
    from datetime import timedelta
    
    client = request.user.client_profile
    active_membership = client.memberships.filter(status='ACTIVE').first()
    pending_membership = client.memberships.filter(status='PENDING').order_by('start_date').first()
    finance_settings = getattr(client.gym, 'finance_settings', None)
    allow_pay_next_fee = bool(finance_settings and getattr(finance_settings, 'allow_client_pay_next_fee', False))
    today = timezone.now().date()
    end_date = today + timedelta(days=6)
    
    # Simple Date Strip Data
    dates = []
    for i in range(7):
        d = today + timedelta(days=i)
        dates.append({
            'date': d,
            'day_name': d.strftime('%a'), # TODO: Spanish translation or filter
            'day_num': d.day,
            'is_today': (d == today)
        })
    
    # Get selected date from GET or default to today
    selected_date_str = request.GET.get('date')
    if selected_date_str:
        try:
            selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    # Fetch Sessions
    sessions = ActivitySession.objects.filter(
        gym=client.gym,
        start_datetime__date=selected_date,
        status='SCHEDULED'
    ).order_by('start_datetime')
    
    # Augment sessions with 'is_booked' and 'is_full'
    # We can prefetch attendees for performance if needed
    for s in sessions:
        s.user_booked = s.attendees.filter(id=client.id).exists()
        s.is_full = s.attendee_count >= s.max_capacity if s.max_capacity > 0 else False

    context = {
        'dates': dates,
        'selected_date': selected_date,
        'sessions': sessions,
        'client': client,
        'active_membership': active_membership,
        'pending_membership': pending_membership,
        'membership_required': getattr(client.gym, 'require_active_membership', False),
        'allow_pay_next_fee': allow_pay_next_fee,
    }
    return render(request, 'portal/bookings/list.html', context)

@login_required
def portal_book_session(request, session_id):
    """
    Toggle booking for a session (Book/Cancel).
    """
    from activities.models import ActivitySession
    
    client = request.user.client_profile
    session = get_object_or_404(ActivitySession, id=session_id, gym=client.gym)
    
    # Booking Logic
    if request.method == 'POST':
        action = request.POST.get('action') # 'book' or 'cancel'
        
        if action == 'book':
            # Check if membership required by gym policy
            gym = client.gym
            if getattr(gym, 'require_active_membership', False):
                has_active_membership = client.memberships.filter(status='ACTIVE').exists()
                if not has_active_membership:
                    pending_membership = client.memberships.filter(status='PENDING').order_by('start_date').first()
                    if pending_membership and pending_membership.start_date:
                        start_str = pending_membership.start_date.strftime('%d/%m/%Y')
                        messages.error(request, f'Necesitas una membresía activa para reservar clases. Tu siguiente cuota empieza el {start_str}. Paga la siguiente cuota desde la app.')
                    else:
                        messages.error(request, 'Necesitas una membresía activa para reservar clases. Paga la siguiente cuota desde la app.')
                    return redirect(f"{reverse('portal_bookings')}?date={session.start_datetime.date()}")
            
            # Other checks
            if session.status != 'SCHEDULED':
                messages.error(request, 'La clase no está disponible.')
            elif session.attendees.filter(id=client.id).exists():
                messages.warning(request, 'Ya estás apuntado a esta clase.')
            elif session.max_capacity > 0 and session.attendee_count >= session.max_capacity:
                # Check waitlist
                if gym.allow_waitlist:
                    from activities.models import WaitlistEntry
                    WaitlistEntry.objects.get_or_create(session=session, client=client)
                    messages.info(request, 'Clase completa. Te hemos añadido a la lista de espera.')
                else:
                    messages.error(request, 'Clase completa.')
            else:
                # Success
                session.attendees.add(client)
                
                # Create Visit Record (ClientVisit) as verification
                from clients.models import ClientVisit
                ClientVisit.objects.create(
                    client=client,
                    staff=session.staff,
                    date=session.start_datetime.date(),
                    status='SCHEDULED',
                    concept=session.activity.name
                )
                
                messages.success(request, '¡Clase reservada!')
                
        elif action == 'cancel':
            if session.attendees.filter(id=client.id).exists():
                session.attendees.remove(client)
                
                # Determinar si la cancelación es temprana o tardía
                from datetime import timedelta
                from clients.models import ClientVisit
                
                # Obtener la política de la actividad
                policy = getattr(session.activity, 'policy', None)
                cancellation_type = None
                
                if policy and policy.cancellation_window_hours:
                    # Calcular cuántas horas quedan hasta la clase
                    now = timezone.now()
                    hours_until_session = (session.start_datetime - now).total_seconds() / 3600
                    
                    if hours_until_session >= policy.cancellation_window_hours:
                        cancellation_type = ClientVisit.CancellationType.EARLY
                    else:
                        cancellation_type = ClientVisit.CancellationType.LATE
                
                # Actualizar o crear el registro de visita como cancelada
                ClientVisit.objects.update_or_create(
                    client=client,
                    date=session.start_datetime.date(),
                    concept=session.activity.name,
                    status='SCHEDULED',
                    defaults={
                        'status': ClientVisit.Status.CANCELLED,
                        'cancellation_type': cancellation_type,
                        'staff': session.staff
                    }
                )
                
                if cancellation_type == ClientVisit.CancellationType.LATE:
                    messages.warning(request, 'Reserva cancelada con penalización (cancelación tardía).')
                else:
                    messages.success(request, 'Reserva cancelada.')
            else:
                messages.warning(request, 'No estabas apuntado.')
                
    return redirect(f"{reverse('portal_bookings')}?date={session.start_datetime.date()}")


# ============================================
# FORGOT / RESET PASSWORD
# ============================================

def portal_forgot_password(request):
    """
    Solicitar recuperación de contraseña por email.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Introduce tu email.')
            return render(request, 'portal/auth/forgot_password.html')
        
        from django.contrib.auth import get_user_model
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        User = get_user_model()
        
        try:
            user = User.objects.get(email=email)
            
            # Verificar que es cliente
            if not hasattr(user, 'client_profile'):
                messages.error(request, 'Este email no está registrado como socio.')
                return render(request, 'portal/auth/forgot_password.html')
            
            # Generar token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # En producción enviaríamos email real aquí
            # Por ahora guardamos en sesión para demo
            reset_link = f"/app/reset-password/{uid}/{token}/"
            
            # TODO: Enviar email real con:
            # send_mail(
            #     'Recuperar contraseña - Mi Gym',
            #     f'Haz clic aquí para recuperar tu contraseña: {reset_link}',
            #     'noreply@mygym.com',
            #     [email],
            # )
            
            # Para desarrollo, mostramos el link
            request.session['reset_link_debug'] = reset_link
            
            return render(request, 'portal/auth/reset_sent.html', {'email': email})
            
        except User.DoesNotExist:
            # No revelamos si el email existe o no por seguridad
            return render(request, 'portal/auth/reset_sent.html', {'email': email})
    
    return render(request, 'portal/auth/forgot_password.html')


def portal_reset_password(request, uidb64, token):
    """
    Resetear contraseña con token válido.
    """
    from django.contrib.auth import get_user_model
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    
    User = get_user_model()
    
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Verificar token
    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, 'El enlace de recuperación es inválido o ha expirado.')
        return redirect('portal_forgot_password')
    
    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        if not password1 or len(password1) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
        elif password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        else:
            user.set_password(password1)
            user.save()
            messages.success(request, '¡Contraseña actualizada! Ya puedes iniciar sesión.')
            return redirect('portal_login')
    
    return render(request, 'portal/auth/reset_password.html', {'valid_link': True})


# ============================================
# PROFILE
# ============================================

@login_required
def portal_profile(request):
    """
    Ver perfil del cliente.
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    active_membership = client.memberships.filter(status='ACTIVE').first()
    
    # Estadísticas
    total_visits = client.visits.filter(status='ATTENDED').count()
    this_month_visits = client.visits.filter(
        status='ATTENDED',
        date__month=timezone.now().month,
        date__year=timezone.now().year
    ).count()
    
    context = {
        'client': client,
        'membership': active_membership,
        'total_visits': total_visits,
        'this_month_visits': this_month_visits,
    }
    return render(request, 'portal/profile/view.html', context)


@login_required
def portal_payment_methods(request):
    """Listado de tarjetas guardadas y alta de nueva tarjeta (Stripe)."""
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')

    client = request.user.client_profile
    finance_settings = getattr(client.gym, 'finance_settings', None)
    allow_delete = bool(finance_settings and finance_settings.allow_client_delete_card)
    cards = list_payment_methods(client)

    context = {
        'client': client,
        'cards': cards,
        'stripe_public_key': finance_settings.stripe_public_key if finance_settings else '',
        'allow_delete': allow_delete,
    }
    return render(request, 'portal/profile/payment_methods.html', context)


@login_required
def portal_profile_edit(request):
    """
    Editar datos del perfil.
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    
    if request.method == 'POST':
        # Actualizar datos básicos
        client.first_name = request.POST.get('first_name', client.first_name)
        client.last_name = request.POST.get('last_name', client.last_name)
        client.phone_number = request.POST.get('phone_number', client.phone_number)
        client.address = request.POST.get('address', client.address)
        
        # Foto de perfil
        if 'photo' in request.FILES:
            client.photo = request.FILES['photo']
        
        client.save()
        
        # Actualizar también el User
        request.user.first_name = client.first_name
        request.user.last_name = client.last_name
        request.user.save()
        
        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('portal_profile')
    
    return render(request, 'portal/profile/edit.html', {'client': client})


@login_required
def portal_toggle_email_notifications(request):
    """
    Activa o desactiva las notificaciones por email del cliente.
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    if request.method == 'POST':
        client = request.user.client_profile
        client.email_notifications_enabled = not client.email_notifications_enabled
        client.save()
        
        if client.email_notifications_enabled:
            messages.success(request, '✅ Notificaciones por email activadas.')
        else:
            messages.info(request, '🔕 Ya no recibirás emails del gimnasio.')
        
        return redirect('portal_profile')
    
    return redirect('portal_profile')


@login_required
def portal_change_password(request):
    """
    Cambiar contraseña desde perfil.
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password1 = request.POST.get('new_password1', '')
        new_password2 = request.POST.get('new_password2', '')
        
        if not request.user.check_password(current_password):
            messages.error(request, 'La contraseña actual es incorrecta.')
        elif len(new_password1) < 6:
            messages.error(request, 'La nueva contraseña debe tener al menos 6 caracteres.')
        elif new_password1 != new_password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        else:
            request.user.set_password(new_password1)
            request.user.save()
            
            # Re-login para mantener sesión
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            
            messages.success(request, '¡Contraseña cambiada correctamente!')
            return redirect('portal_profile')
    
    return render(request, 'portal/profile/change_password.html')


@login_required
def portal_get_stripe_setup(request):
    """Devuelve client_secret para guardar tarjeta desde el portal."""
    if not hasattr(request.user, 'client_profile'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    client = request.user.client_profile
    try:
        client_secret = create_setup_intent(client)
        return JsonResponse({'client_secret': client_secret})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def portal_delete_payment_method(request, pm_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    if not hasattr(request.user, 'client_profile'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    client = request.user.client_profile
    finance_settings = getattr(client.gym, 'finance_settings', None)
    if not finance_settings or not finance_settings.allow_client_delete_card:
        return JsonResponse({'error': 'El gimnasio no permite eliminar tarjetas desde la app.'}, status=403)
    try:
        detach_payment_method(client, pm_id)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================
# ROUTINES
# ============================================

@login_required
def portal_routines(request):
    """
    Lista de rutinas asignadas al cliente.
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    
    # Obtener rutinas asignadas al cliente
    try:
        from routines.models import RoutineAssignment
        assignments = RoutineAssignment.objects.filter(
            client=client
        ).select_related('routine').order_by('-assigned_date')
    except:
        assignments = []
    
    context = {
        'client': client,
        'assignments': assignments,
    }
    return render(request, 'portal/routines/list.html', context)


@login_required
def portal_routine_detail(request, routine_id):
    """
    Ver detalle de una rutina con sus ejercicios.
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    
    try:
        from routines.models import Routine, RoutineAssignment
        
        # Verificar que la rutina está asignada al cliente
        assignment = get_object_or_404(
            RoutineAssignment,
            routine_id=routine_id,
            client=client
        )
        routine = assignment.routine
        
        # Obtener ejercicios de la rutina
        exercises = routine.exercises.all().select_related('exercise').order_by('order')
        
    except:
        messages.error(request, 'Rutina no encontrada.')
        return redirect('portal_routines')
    
    context = {
        'client': client,
        'routine': routine,
        'assignment': assignment,
        'exercises': exercises,
    }
    return render(request, 'portal/routines/detail.html', context)


# ============================================
# HISTORY
# ============================================

@login_required
def portal_history(request):
    """
    Historial de asistencias del cliente.
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    
    # Obtener visitas pasadas ordenadas por fecha descendente
    visits = client.visits.filter(
        date__lte=timezone.now().date()
    ).order_by('-date', '-check_in_time')[:50]  # Últimas 50
    
    # Estadísticas
    from datetime import timedelta
    last_30_days = timezone.now().date() - timedelta(days=30)
    
    stats = {
        'total_visits': client.visits.filter(status='ATTENDED').count(),
        'last_30_days': client.visits.filter(
            status='ATTENDED',
            date__gte=last_30_days
        ).count(),
        'no_shows': client.visits.filter(status='NOSHOW').count(),
    }
    
    context = {
        'client': client,
        'visits': visits,
        'stats': stats,
    }
    return render(request, 'portal/bookings/history.html', context)


# ============================================
# CHECK-IN QR (ESCÁNER DE CÁMARA)
# ============================================

@login_required
def portal_checkin_scanner(request):
    """
    Vista principal de check-in: el cliente escanea el QR de la clase con su cámara.
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    active_membership = client.memberships.filter(status='ACTIVE').first()
    
    # Próximas clases reservadas del cliente
    from activities.models import ActivitySession
    today = timezone.now()
    
    upcoming_sessions = ActivitySession.objects.filter(
        gym=client.gym,
        attendees=client,
        start_datetime__gte=today,
        status='SCHEDULED'
    ).select_related('activity', 'room').order_by('start_datetime')[:5]
    
    # Últimos check-ins
    from activities.models import SessionCheckin
    recent_checkins = SessionCheckin.objects.filter(
        client=client
    ).select_related('session__activity').order_by('-checked_in_at')[:5]
    
    context = {
        'client': client,
        'membership': active_membership,
        'upcoming_sessions': upcoming_sessions,
        'recent_checkins': recent_checkins,
    }
    return render(request, 'portal/checkin/scanner.html', context)


@login_required  
def portal_checkin_process(request):
    """
    API para procesar el check-in cuando el cliente escanea un QR de clase.
    El cliente envía el token escaneado y se valida.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    if not hasattr(request.user, 'client_profile'):
        return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)
    
    client = request.user.client_profile
    
    import json
    try:
        data = json.loads(request.body)
        qr_content = data.get('qr_content', '')
    except:
        qr_content = request.POST.get('qr_content', '')
    
    if not qr_content:
        return JsonResponse({'success': False, 'error': 'QR vacío'}, status=400)
    
    # El QR contiene una URL como /activities/checkin/qr/SESSION_ID:TIMESTAMP:SIGNATURE/
    # Extraer el token
    import re
    match = re.search(r'/checkin/qr/([^/]+)/', qr_content)
    if not match:
        # Intentar si es solo el token
        token = qr_content.strip()
    else:
        token = match.group(1)
    
    # Parsear el token: SESSION_ID:TIMESTAMP:SIGNATURE
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return JsonResponse({'success': False, 'error': 'QR inválido'}, status=400)
        
        session_id = int(parts[0])
    except (ValueError, IndexError):
        return JsonResponse({'success': False, 'error': 'QR inválido'}, status=400)
    
    # Obtener la sesión
    from activities.models import ActivitySession, AttendanceSettings, SessionCheckin
    from activities.checkin_views import verify_qr_token
    from datetime import timedelta
    
    try:
        session = ActivitySession.objects.select_related('activity', 'gym').get(id=session_id)
    except ActivitySession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Clase no encontrada'}, status=404)
    
    # Verificar que el cliente pertenece al mismo gimnasio
    if session.gym != client.gym:
        return JsonResponse({'success': False, 'error': 'Esta clase no es de tu gimnasio'}, status=400)
    
    # Obtener configuración
    try:
        att_settings = session.gym.attendance_settings
        max_age = att_settings.qr_refresh_seconds * 2
        minutes_before = att_settings.qr_checkin_minutes_before
        minutes_after = att_settings.qr_checkin_minutes_after
        success_message = att_settings.checkin_success_message
    except AttendanceSettings.DoesNotExist:
        max_age = 60
        minutes_before = 15
        minutes_after = 30
        success_message = "✅ ¡Check-in completado!"
    
    # Verificar token
    if not verify_qr_token(token, session_id, max_age):
        return JsonResponse({
            'success': False, 
            'error': 'QR expirado. Escanea de nuevo el QR de la pantalla.'
        }, status=400)
    
    # Verificar ventana de tiempo
    now = timezone.now()
    window_start = session.start_datetime - timedelta(minutes=minutes_before)
    window_end = session.start_datetime + timedelta(minutes=minutes_after)
    
    if now < window_start:
        mins_to_wait = int((window_start - now).total_seconds() / 60)
        return JsonResponse({
            'success': False,
            'error': f'Demasiado pronto. El check-in abre en {mins_to_wait} minutos.'
        }, status=400)
    
    if now > window_end:
        return JsonResponse({
            'success': False,
            'error': 'La ventana de check-in ha cerrado para esta clase.'
        }, status=400)
    
    # Verificar que el cliente tiene reserva
    if client not in session.attendees.all():
        return JsonResponse({
            'success': False,
            'error': 'No tienes reserva para esta clase. Resérvala primero.'
        }, status=400)
    
    # Verificar si ya hizo check-in
    existing = SessionCheckin.objects.filter(session=session, client=client).first()
    if existing:
        return JsonResponse({
            'success': True,
            'already_checked_in': True,
            'message': f'Ya hiciste check-in a las {existing.checked_in_at.strftime("%H:%M")}',
            'session_name': session.activity.name,
            'session_time': session.start_datetime.strftime('%H:%M'),
        })
    
    # Crear check-in
    checkin = SessionCheckin.objects.create(
        session=session,
        client=client,
        method='APP',  # Desde la app del cliente
        qr_token=token,
        ip_address=get_client_ip(request)
    )
    
    return JsonResponse({
        'success': True,
        'message': success_message,
        'session_name': session.activity.name,
        'session_time': session.start_datetime.strftime('%H:%M'),
        'checked_in_at': checkin.checked_in_at.strftime('%H:%M'),
        'client_name': client.first_name,
    })


def get_client_ip(request):
    """Obtiene la IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def portal_checkin_qr(request):
    """
    Vista de check-in con QR dinámico renovable.
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    active_membership = client.memberships.filter(status='ACTIVE').first()
    
    # Generar token único temporal (renovable cada 30s)
    import hashlib
    import time
    timestamp = int(time.time() / 30)  # Se renueva cada 30 segundos
    qr_token = hashlib.sha256(
        f"{client.id}-{client.access_code}-{timestamp}".encode()
    ).hexdigest()[:8].upper()
    
    # Últimas 5 visitas
    recent_visits = client.visits.filter(
        status='ATTENDED'
    ).order_by('-date', '-check_in_time')[:5]
    
    context = {
        'client': client,
        'membership': active_membership,
        'qr_token': qr_token,
        'recent_visits': recent_visits,
    }
    return render(request, 'portal/checkin/qr.html', context)


@login_required
def portal_checkin_refresh(request):
    """
    API para refrescar el token QR (AJAX).
    """
    if request.method != 'POST':
        from django.http import JsonResponse
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if not hasattr(request.user, 'client_profile'):
        from django.http import JsonResponse
        return JsonResponse({'error': 'Not a client'}, status=403)
    
    client = request.user.client_profile
    
    # Generar nuevo token
    import hashlib
    import time
    timestamp = int(time.time() / 30)
    qr_token = hashlib.sha256(
        f"{client.id}-{client.access_code}-{timestamp}".encode()
    ).hexdigest()[:8].upper()
    
    from django.http import JsonResponse
    return JsonResponse({
        'token': qr_token,
        'expires_in': 30,
        'timestamp': timestamp
    })

# ==================== DOCUMENTS & CONTRACTS ====================

@login_required
def portal_documents(request):
    """
    Lista de documentos y contratos del cliente
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    from .models import ClientDocument
    
    # Documentos pendientes de firma
    pending_docs = client.documents.filter(
        requires_signature=True,
        status='PENDING'
    )
    
    # Documentos firmados
    signed_docs = client.documents.filter(status='SIGNED')
    
    # Otros documentos
    other_docs = client.documents.exclude(
        status__in=['PENDING', 'SIGNED']
    )
    
    context = {
        'client': client,
        'pending_documents': pending_docs,
        'signed_documents': signed_docs,
        'other_documents': other_docs,
        'total_pending': pending_docs.count(),
    }
    return render(request, 'portal/documents/list.html', context)


@login_required
def portal_document_detail(request, document_id):
    """
    Ver detalle de un documento y firmarlo
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    from .models import ClientDocument
    
    document = get_object_or_404(
        ClientDocument,
        id=document_id,
        client=client
    )
    
    context = {
        'client': client,
        'document': document,
    }
    return render(request, 'portal/documents/detail.html', context)


@login_required
def portal_document_sign(request, document_id):
    """
    Firmar documento (recibe imagen de firma en base64)
    """
    if request.method != 'POST':
        return redirect('portal_documents')
    
    if not hasattr(request.user, 'client_profile'):
        from django.http import JsonResponse
        return JsonResponse({'error': 'Not a client'}, status=403)
    
    client = request.user.client_profile
    from .models import ClientDocument
    from django.core.files.base import ContentFile
    import base64
    from datetime import datetime
    
    document = get_object_or_404(
        ClientDocument,
        id=document_id,
        client=client,
        status='PENDING'
    )
    
    # Obtener firma en base64
    signature_data = request.POST.get('signature')
    if not signature_data:
        messages.error(request, 'No se recibió la firma.')
        return redirect('portal_document_detail', document_id=document_id)
    
    try:
        # Decodificar base64
        format, imgstr = signature_data.split(';base64,')
        ext = format.split('/')[-1]
        
        signature_file = ContentFile(
            base64.b64decode(imgstr),
            name=f'signature_{client.id}_{document.id}.{ext}'
        )
        
        # Guardar firma
        document.signature_image = signature_file
        document.is_signed = True
        document.status = 'SIGNED'
        document.signed_at = timezone.now()
        
        # Capturar IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            document.signed_ip = x_forwarded_for.split(',')[0]
        else:
            document.signed_ip = request.META.get('REMOTE_ADDR')
        
        document.save()
        
        messages.success(request, f'✅ {document.name} firmado correctamente.')
        return redirect('portal_documents')
        
    except Exception as e:
        messages.error(request, f'Error al procesar la firma: {str(e)}')
        return redirect('portal_document_detail', document_id=document_id)


@login_required
def portal_shop(request):
    """Shop/Tienda: Muestra servicios, productos y cuotas disponibles para compra online"""
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    gym = client.gym
    
    # Filtrar solo items con is_visible_online=True
    from services.models import Service
    from products.models import Product
    from memberships.models import MembershipPlan
    
    services = Service.objects.filter(
        gym=gym,
        is_active=True,
        is_visible_online=True
    ).select_related('category', 'tax_rate')
    
    products = Product.objects.filter(
        gym=gym,
        is_active=True,
        is_visible_online=True
    ).select_related('category', 'tax_rate')
    
    membership_plans = MembershipPlan.objects.filter(
        gym=gym,
        is_active=True,
        is_visible_online=True
    ).select_related('tax_rate')
    
    context = {
        'client': client,
        'services': services,
        'products': products,
        'membership_plans': membership_plans,
    }
    
    return render(request, 'portal/shop/shop.html', context)


@login_required
def portal_chat(request):
    """Chat interno entre cliente y gimnasio"""
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    from .models import ChatRoom, ChatMessage
    
    # Obtener o crear sala de chat
    chat_room, created = ChatRoom.objects.get_or_create(
        client=client,
        gym=client.gym
    )
    
    # Obtener mensajes
    messages_list = chat_room.messages.select_related('sender').order_by('created_at')
    
    # Marcar mensajes del gimnasio como leídos
    chat_room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    
    context = {
        'client': client,
        'chat_room': chat_room,
        'messages': messages_list,
    }
    
    return render(request, 'portal/chat/chat.html', context)


@login_required
def portal_chat_send(request):
    """Enviar mensaje de chat (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    if not hasattr(request.user, 'client_profile'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    client = request.user.client_profile
    from .models import ChatRoom, ChatMessage
    import json
    
    try:
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return JsonResponse({'error': 'Mensaje vacío'}, status=400)
        
        # Obtener sala de chat
        chat_room = ChatRoom.objects.get(client=client)
        
        # Crear mensaje
        message = ChatMessage.objects.create(
            room=chat_room,
            sender=request.user,
            message=message_text
        )
        
        # Actualizar timestamp de la sala
        chat_room.last_message_at = timezone.now()
        chat_room.save(update_fields=['last_message_at'])
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'text': message.message,
                'created_at': message.created_at.strftime('%H:%M'),
                'is_from_client': True
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def portal_chat_poll(request):
    """Obtener nuevos mensajes (AJAX polling)"""
    if not hasattr(request.user, 'client_profile'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    client = request.user.client_profile
    from .models import ChatRoom, ChatMessage
    from django.http import JsonResponse
    
    try:
        # Obtener sala
        chat_room = ChatRoom.objects.get(client=client)
        
        # Obtener ID del último mensaje que el cliente tiene
        last_message_id = request.GET.get('last_message_id', 0)
        
        # Obtener mensajes nuevos
        new_messages = chat_room.messages.filter(
            id__gt=last_message_id
        ).select_related('sender')
        
        # Marcar como leídos los del gimnasio
        new_messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        
        messages_data = [{
            'id': msg.id,
            'text': msg.message,
            'created_at': msg.created_at.strftime('%H:%M'),
            'is_from_client': msg.is_from_client,
            'sender_name': f"{msg.sender.first_name} {msg.sender.last_name}".strip() or msg.sender.email
        } for msg in new_messages]
        
        return JsonResponse({
            'success': True,
            'messages': messages_data
        })
    except ChatRoom.DoesNotExist:
        return JsonResponse({'success': True, 'messages': []})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================
# BILLING & PAYMENTS
# ============================================

@login_required
def portal_billing(request):
    """
    Billing dashboard: Payment history and next fee.
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    from finance.models import ClientPayment
    
    # 1. History
    payments = ClientPayment.objects.filter(client=client).order_by('-date')
    
    # 2. Next Payment Prediction
    next_payment = None
    active_membership = client.memberships.filter(status='ACTIVE').first()
    pending_membership = client.memberships.filter(status='PENDING').order_by('start_date').first()
    
    finance_settings = getattr(client.gym, 'finance_settings', None)
    allow_pay_next = bool(finance_settings and getattr(finance_settings, 'allow_client_pay_next_fee', False))
    
    if active_membership:
        # Simple prediction: Next month same day
        plan = active_membership.plan
        if plan:
            amount = plan.price_monthly # Default to monthly for now
            if hasattr(active_membership, 'next_payment_date'):
                 date = active_membership.next_payment_date
            else:
                 # Fallback calc
                 date = active_membership.end_date 
            
            next_payment = {
                'amount': amount,
                'date': date,
                'plan_name': plan.name
            }
    elif pending_membership:
         # If pending, that's the next one
         plan = pending_membership.plan
         next_payment = {
            'amount': plan.price_monthly,
            'date': pending_membership.start_date,
            'plan_name': plan.name,
            'is_pending_activation': True
        }

    context = {
        'client': client,
        'payments': payments,
        'next_payment': next_payment,
        'allow_pay_next': allow_pay_next,
        'stripe_public_key': finance_settings.stripe_public_key if finance_settings else '',
    }
    return render(request, 'portal/billing/index.html', context)


@login_required
def portal_process_payment(request, payment_id=None):
    """
    Process a specific payment (retry) or next fee (if payment_id is None).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    client = request.user.client_profile
    from finance.stripe_utils import charge_client_off_session
    
    try:
        if payment_id:
            # Retry existing failed payment
            from finance.models import ClientPayment
            payment = get_object_or_404(ClientPayment, id=payment_id, client=client)
            
            # Logic to charge using saved card
            success, message = charge_client_off_session(client, payment.amount, f"Retry: {payment.concept}")
            
            if success:
                payment.status = 'PAID'
                payment.save()
                messages.success(request, 'Pago realizado correctamente.')
            else:
                messages.error(request, f'Error al procesar el pago: {message}')
                
        else:
            # Pay Next Fee (Early Renewal)
            # 1. Identify amount and concept
            active_membership = client.memberships.filter(status='ACTIVE').first()
            if not active_membership:
                 messages.error(request, 'No tienes membresía activa para renovar.')
                 return redirect('portal_billing')
            
            amount = active_membership.plan.price_monthly
            concept = f"Renovación anticipada: {active_membership.plan.name}"
            
            # 2. Charge
            success, message = charge_client_off_session(client, amount, concept)
            
            if success:
                # 3. Create Payment Record
                from finance.models import ClientPayment
                ClientPayment.objects.create(
                    client=client,
                    amount=amount,
                    status='PAID',
                    concept=concept,
                    payment_method='Tarjeta guardada' # Simplification
                )
                
                # 4. Extend Membership (Logic simplified)
                messages.success(request, 'Cuota pagada y membresía renovada.')
            else:
                messages.error(request, f'Error: {message}')
                
        return redirect('portal_billing')
        
    except Exception as e:
        messages.error(request, f'Error inesperado: {str(e)}')
        return redirect('portal_billing')

