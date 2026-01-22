"""
Views del Portal Público
------------------------
Vistas sin autenticación (o autenticación de cliente) para:
- Horario público de clases
- Precios y planes
- Servicios
- Tienda
- Auto-registro de clientes
- Login de clientes
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q
from datetime import datetime, timedelta

from organizations.models import Gym, PublicPortalSettings
from activities.models import Activity, ActivitySession
from memberships.models import MembershipPlan
from services.models import Service
from products.models import Product
from clients.models import Client, Membership


def get_gym_by_slug(slug):
    """Helper para obtener gym y sus settings por slug"""
    try:
        settings = PublicPortalSettings.objects.select_related('gym').get(
            public_slug=slug,
            public_portal_enabled=True
        )
        return settings.gym, settings
    except PublicPortalSettings.DoesNotExist:
        return None, None


# ===========================
# LANDING PAGE DEL GYM
# ===========================

def public_gym_home(request, slug):
    """Página principal del portal público del gimnasio"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', {
            'message': 'Gimnasio no encontrado o portal no habilitado'
        }, status=404)
    
    context = {
        'gym': gym,
        'settings': settings,
        'modules': {
            'schedule': settings.show_schedule,
            'pricing': settings.show_pricing,
            'services': settings.show_services,
            'shop': settings.show_shop,
        }
    }
    
    return render(request, 'public_portal/home.html', context)


# ===========================
# HORARIO PÚBLICO
# ===========================

def public_schedule(request, slug):
    """Calendario público de clases"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym or not settings.show_schedule:
        return render(request, 'public_portal/404.html', {
            'message': 'Horario no disponible'
        }, status=404)
    
    # Filtrar solo actividades visibles online
    activities = Activity.objects.filter(
        gym=gym,
        is_visible_online=True
    ).select_related('category')
    
    context = {
        'gym': gym,
        'settings': settings,
        'activities': activities,
        'can_book': settings.allow_online_booking,
        'requires_login': settings.booking_requires_login,
    }
    
    return render(request, 'public_portal/schedule.html', context)


def api_public_schedule_events(request, slug):
    """API para FullCalendar - solo sesiones de actividades visibles"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym or not settings.show_schedule:
        return JsonResponse({'error': 'Not allowed'}, status=403)
    
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    sessions = ActivitySession.objects.filter(
        gym=gym,
        activity__is_visible_online=True,
        start_datetime__gte=start,
        start_datetime__lte=end
    ).select_related('activity', 'staff', 'room')
    
    events = []
    for session in sessions:
        # Calcular disponibilidad
        attendee_count = session.attendees.count()
        spots_available = session.max_capacity - attendee_count
        
        events.append({
            'id': f'sess_{session.id}',
            'title': session.activity.name,
            'start': session.start_datetime.isoformat(),
            'end': session.end_datetime.isoformat(),
            'color': session.activity.color,
            'extendedProps': {
                'type': 'session',
                'activity_id': session.activity.id,
                'staff': session.staff.user.get_full_name() if session.staff else None,
                'room': session.room.name if session.room else None,
                'attendees': attendee_count,
                'max_capacity': session.max_capacity,
                'spots_available': spots_available,
                'is_full': spots_available <= 0,
            }
        })
    
    return JsonResponse(events, safe=False)


# ===========================
# PRECIOS Y PLANES
# ===========================

def public_pricing(request, slug):
    """Página de precios y planes"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym or not settings.show_pricing:
        return render(request, 'public_portal/404.html', {
            'message': 'Precios no disponibles'
        }, status=404)
    
    plans = MembershipPlan.objects.filter(
        gym=gym,
        is_active=True,
        is_visible_online=True
    ).order_by('display_order', 'base_price')
    
    context = {
        'gym': gym,
        'settings': settings,
        'plans': plans,
    }
    
    return render(request, 'public_portal/pricing.html', context)


# ===========================
# COMPRA DE PLANES
# ===========================

@login_required
def public_plan_purchase(request, slug, plan_id):
    """Página de compra de un plan"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym or not settings.show_pricing:
        return render(request, 'public_portal/404.html', {
            'message': 'Compra no disponible'
        }, status=404)
    
    # Verificar que el usuario es cliente de este gym
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        messages.error(request, 'No tienes acceso a este gimnasio')
        return redirect('public_login', slug=slug)
    
    # Obtener el plan
    plan = get_object_or_404(MembershipPlan, id=plan_id, gym=gym, is_active=True, is_visible_online=True)
    
    # Obtener métodos de pago disponibles
    from finance.models import PaymentMethod
    payment_methods = PaymentMethod.objects.filter(
        gym=gym,
        is_active=True,
        available_for_online=True
    ).order_by('display_order')
    
    if request.method == 'POST':
        from django.http import JsonResponse
        import json
        
        payment_method_id = request.POST.get('payment_method')
        payment_method = get_object_or_404(PaymentMethod, id=payment_method_id, gym=gym, is_active=True)
        
        # Crear la membresía
        membership = Membership.objects.create(
            client=client,
            gym=gym,
            plan=plan,
            name=plan.name,
            start_date=timezone.now().date(),
            price=plan.final_price,
            status='ACTIVE',
            is_recurring=plan.is_recurring,
            payment_method=payment_method,
            created_by=request.user
        )
        
        # Si requiere pago online (Stripe, Redsys)
        if payment_method.gateway in ['STRIPE', 'REDSYS']:
            # Crear sesión de pago
            # TODO: Implementar integración con pasarelas
            # from billing.services import create_payment_session
            
            try:
                # Por ahora redirigir a página de éxito
                # En producción aquí iría la integración con Stripe/Redsys
                membership.status = 'PENDING_PAYMENT'
                membership.save()
                
                # Simular URL de pago
                payment_url = f'/public/{slug}/purchase/success/{membership.id}/'
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'redirect_url': payment_url
                    })
                return redirect('public_purchase_success', slug=slug, membership_id=membership.id)
                
            except Exception as e:
                membership.delete()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': str(e)
                    }, status=400)
                messages.error(request, f'Error al procesar el pago: {str(e)}')
                return redirect('public_pricing', slug=slug)
        
        # Pagos offline (efectivo, transferencia)
        else:
            membership.status = 'PENDING_PAYMENT'
            membership.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'success_url': f'/public/{slug}/purchase/success/{membership.id}/'
                })
            return redirect('public_purchase_success', slug=slug, membership_id=membership.id)
    
    context = {
        'gym': gym,
        'settings': settings,
        'plan': plan,
        'payment_methods': payment_methods,
    }
    
    return render(request, 'public_portal/plan_purchase.html', context)


@login_required
def public_purchase_success(request, slug, membership_id):
    """Página de confirmación de compra"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    # Verificar que el usuario es cliente y propietario de esta membresía
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    membership = get_object_or_404(Membership, id=membership_id, client=client, gym=gym)
    
    context = {
        'gym': gym,
        'settings': settings,
        'membership': membership,
    }
    
    return render(request, 'public_portal/purchase_success.html', context)


# ===========================
# DASHBOARD DEL CLIENTE
# ===========================

@login_required
def public_client_dashboard(request, slug):
    """Dashboard del cliente con sus membresías y reservas"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    # Verificar que el usuario es cliente de este gym
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        messages.error(request, 'No tienes acceso a este gimnasio')
        return redirect('public_login', slug=slug)
    
    # Membresías del cliente
    memberships = Membership.objects.filter(
        client=client,
        gym=gym
    ).select_related('plan').order_by('-start_date')
    
    # Próximas reservas
    from activities.models import ActivitySessionBooking
    bookings = ActivitySessionBooking.objects.filter(
        client=client,
        session__start_datetime__gte=timezone.now(),
        status='CONFIRMED'
    ).select_related(
        'session__activity',
        'session__staff'
    ).order_by('session__start_datetime')[:10]
    
    # Gamificación
    gamification_data = None
    try:
        from gamification.models import GamificationSettings, ClientProgress, Achievement, ClientAchievement
        gamification_settings = gym.gamification_settings
        if gamification_settings.enabled and gamification_settings.show_on_portal:
            progress, _ = ClientProgress.objects.get_or_create(client=client)
            
            # Posición en ranking
            rank_position = ClientProgress.objects.filter(
                client__gym=gym,
                total_xp__gt=progress.total_xp
            ).count() + 1
            
            # Logros desbloqueados
            unlocked_count = ClientAchievement.objects.filter(client=client).count()
            total_achievements = Achievement.objects.filter(gym=gym, is_active=True).count()
            
            # Últimos logros desbloqueados
            recent_achievements = ClientAchievement.objects.filter(
                client=client
            ).select_related('achievement').order_by('-unlocked_at')[:3]
            
            gamification_data = {
                'enabled': True,
                'progress': progress,
                'rank_position': rank_position,
                'unlocked_count': unlocked_count,
                'total_achievements': total_achievements,
                'recent_achievements': recent_achievements,
                'show_leaderboard': gamification_settings.show_leaderboard,
            }
    except Exception:
        pass
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'memberships': memberships,
        'bookings': bookings,
        'gamification': gamification_data,
    }
    
    return render(request, 'public_portal/dashboard.html', context)


# ===========================
# GAMIFICACIÓN PORTAL
# ===========================

@login_required
def public_leaderboard(request, slug):
    """Tabla de clasificación pública del gimnasio"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    # Verificar que el usuario es cliente de este gym
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        messages.error(request, 'No tienes acceso a este gimnasio')
        return redirect('public_login', slug=slug)
    
    # Verificar gamificación habilitada
    from gamification.models import GamificationSettings, ClientProgress
    try:
        gamification_settings = gym.gamification_settings
        if not gamification_settings.enabled or not gamification_settings.show_on_portal or not gamification_settings.show_leaderboard:
            messages.warning(request, 'El ranking no está disponible')
            return redirect('public_client_dashboard', slug=slug)
    except GamificationSettings.DoesNotExist:
        messages.warning(request, 'Gamificación no configurada')
        return redirect('public_client_dashboard', slug=slug)
    
    # Top 100 jugadores
    top_clients = ClientProgress.objects.filter(
        client__gym=gym
    ).select_related('client').order_by('-total_xp')[:100]
    
    # Mi progreso
    my_progress, _ = ClientProgress.objects.get_or_create(client=client)
    my_rank = ClientProgress.objects.filter(
        client__gym=gym,
        total_xp__gt=my_progress.total_xp
    ).count() + 1
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'top_clients': top_clients,
        'my_progress': my_progress,
        'my_rank': my_rank,
    }
    
    return render(request, 'public_portal/leaderboard.html', context)


@login_required
def public_achievements(request, slug):
    """Mis logros en el portal del cliente"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    # Verificar que el usuario es cliente de este gym
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        messages.error(request, 'No tienes acceso a este gimnasio')
        return redirect('public_login', slug=slug)
    
    # Verificar gamificación habilitada
    from gamification.models import GamificationSettings, ClientProgress, Achievement, ClientAchievement
    try:
        gamification_settings = gym.gamification_settings
        if not gamification_settings.enabled or not gamification_settings.show_on_portal:
            messages.warning(request, 'La gamificación no está disponible')
            return redirect('public_client_dashboard', slug=slug)
    except GamificationSettings.DoesNotExist:
        messages.warning(request, 'Gamificación no configurada')
        return redirect('public_client_dashboard', slug=slug)
    
    # Obtener todos los logros visibles
    all_achievements = Achievement.objects.filter(
        gym=gym,
        is_active=True
    ).order_by('category', 'order', 'name')
    
    # Obtener logros desbloqueados
    unlocked_ids = set(
        ClientAchievement.objects.filter(client=client)
        .values_list('achievement_id', flat=True)
    )
    unlocked_achievements = {
        ca.achievement_id: ca for ca in ClientAchievement.objects.filter(client=client).select_related('achievement')
    }
    
    # Mi progreso actual
    progress, _ = ClientProgress.objects.get_or_create(client=client)
    
    # Preparar logros con progreso
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
        elif achievement.requirement_type == 'total_xp':
            current_value = progress.total_xp
        elif achievement.requirement_type == 'current_level':
            current_value = progress.current_level
        
        progress_pct = min(100, int((current_value / achievement.requirement_value) * 100)) if achievement.requirement_value > 0 else 0
        
        achievements_list.append({
            'achievement': achievement,
            'unlocked': achievement.id in unlocked_ids,
            'unlocked_at': unlocked_achievements.get(achievement.id).unlocked_at if achievement.id in unlocked_ids else None,
            'current': current_value,
            'required': achievement.requirement_value,
            'progress_pct': progress_pct,
        })
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'achievements': achievements_list,
        'unlocked_count': len(unlocked_ids),
        'total_count': len(achievements_list),
        'progress': progress,
    }
    
    return render(request, 'public_portal/achievements.html', context)


# ===========================
# RESERVA DE CLASES
# ===========================

@login_required
def api_book_session(request, slug):
    """API para reservar plaza en una sesión"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return JsonResponse({'success': False, 'error': 'Gym not found'}, status=404)
    
    # Verificar que el usuario es cliente
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not a client'}, status=403)
    
    import json
    data = json.loads(request.body)
    session_id = data.get('session_id')
    
    if not session_id:
        return JsonResponse({'success': False, 'error': 'Session ID required'}, status=400)
    
    # Obtener la sesión
    try:
        session = ActivitySession.objects.select_related('activity').get(
            id=session_id,
            gym=gym
        )
    except ActivitySession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)
    
    # Verificar que la sesión está en el futuro
    if session.start_datetime < timezone.now():
        return JsonResponse({'success': False, 'error': 'No se pueden reservar clases pasadas'}, status=400)
    
    # Verificar disponibilidad
    from activities.models import ActivitySessionBooking
    current_bookings = ActivitySessionBooking.objects.filter(
        session=session,
        status='CONFIRMED'
    ).count()
    
    if session.capacity and current_bookings >= session.capacity:
        return JsonResponse({'success': False, 'error': 'Clase completa'}, status=400)
    
    # Verificar que no tenga ya una reserva
    existing_booking = ActivitySessionBooking.objects.filter(
        session=session,
        client=client,
        status='CONFIRMED'
    ).exists()
    
    if existing_booking:
        return JsonResponse({'success': False, 'error': 'Ya tienes una reserva para esta clase'}, status=400)
    
    # Verificar que tenga membresía activa con acceso a esta actividad
    active_membership = Membership.objects.filter(
        client=client,
        gym=gym,
        status='ACTIVE',
        start_date__lte=timezone.now().date()
    ).first()
    
    if not active_membership and settings.booking_requires_login:
        return JsonResponse({'success': False, 'error': 'Necesitas una membresía activa'}, status=400)
    
    # Crear la reserva
    booking = ActivitySessionBooking.objects.create(
        session=session,
        client=client,
        gym=gym,
        status='CONFIRMED',
        membership=active_membership,
        created_by=request.user
    )
    
    return JsonResponse({
        'success': True,
        'booking_id': booking.id,
        'message': 'Reserva confirmada'
    })


@login_required
def api_cancel_booking(request, slug, booking_id):
    """API para cancelar una reserva"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return JsonResponse({'success': False, 'error': 'Gym not found'}, status=404)
    
    # Verificar que el usuario es cliente
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not a client'}, status=403)
    
    # Obtener la reserva
    from activities.models import ActivitySessionBooking
    try:
        booking = ActivitySessionBooking.objects.select_related('session').get(
            id=booking_id,
            client=client,
            gym=gym
        )
    except ActivitySessionBooking.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Booking not found'}, status=404)
    
    # Verificar que la sesión no haya pasado
    if booking.session.start_datetime < timezone.now():
        return JsonResponse({'success': False, 'error': 'No se pueden cancelar clases pasadas'}, status=400)
    
    # Cancelar la reserva
    booking.status = 'CANCELLED'
    booking.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Reserva cancelada'
    })


# ===========================
# SERVICIOS
# ===========================

def public_services(request, slug):
    """Página de servicios"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym or not settings.show_services:
        return render(request, 'public_portal/404.html', {
            'message': 'Servicios no disponibles'
        }, status=404)
    
    services = Service.objects.filter(
        gym=gym,
        is_active=True,
        is_visible_online=True
    ).select_related('category')
    
    context = {
        'gym': gym,
        'settings': settings,
        'services': services,
    }
    
    return render(request, 'public_portal/services.html', context)


# ===========================
# TIENDA
# ===========================

def public_shop(request, slug):
    """Tienda de productos"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym or not settings.show_shop:
        return render(request, 'public_portal/404.html', {
            'message': 'Tienda no disponible'
        }, status=404)
    
    products = Product.objects.filter(
        gym=gym,
        is_active=True,
        is_visible_online=True
    ).select_related('category')
    
    context = {
        'gym': gym,
        'settings': settings,
        'products': products,
    }
    
    return render(request, 'public_portal/shop.html', context)


# ===========================
# AUTO-REGISTRO DE CLIENTES
# ===========================

def public_register(request, slug):
    """Auto-registro de clientes (si está habilitado)"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym or not settings.allow_self_registration:
        return render(request, 'public_portal/404.html', {
            'message': 'Registro no disponible. Contacta con el gimnasio.'
        }, status=404)
    
    # Obtener gimnasios de la franquicia (si aplica)
    franchise_gyms = []
    if gym.franchise:
        franchise_gyms = gym.franchise.gyms.filter(is_active=True).order_by('name')
    
    # Obtener campos custom configurados para registro
    from clients.models import ClientField
    custom_fields = ClientField.objects.filter(
        gym=gym,
        is_active=True,
        show_in_registration=True
    ).prefetch_related('options').order_by('display_order', 'name')
    
    if request.method == 'POST':
        # Validar datos mínimos
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        # Gimnasio seleccionado (si hay franquicia)
        selected_gym_id = request.POST.get('gym_id')
        target_gym = gym  # Por defecto el gym actual
        
        if gym.franchise and selected_gym_id:
            try:
                target_gym = gym.franchise.gyms.get(id=selected_gym_id, is_active=True)
            except Gym.DoesNotExist:
                messages.error(request, 'Gimnasio seleccionado no válido')
                return render(request, 'public_portal/register.html', {
                    'gym': gym,
                    'settings': settings,
                    'franchise_gyms': franchise_gyms,
                    'custom_fields': custom_fields,
                })
        
        # Validaciones básicas
        if not all([email, first_name, last_name, password]):
            messages.error(request, 'Todos los campos obligatorios deben estar completos')
            return render(request, 'public_portal/register.html', {
                'gym': gym,
                'settings': settings,
                'franchise_gyms': franchise_gyms,
                'custom_fields': custom_fields,
            })
        
        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden')
            return render(request, 'public_portal/register.html', {
                'gym': gym,
                'settings': settings,
                'franchise_gyms': franchise_gyms,
                'custom_fields': custom_fields,
            })
        
        # Validar campos custom obligatorios
        extra_data = {}
        for field in custom_fields:
            field_key = f'cf_{field.slug}'
            field_value = request.POST.get(field_key, '').strip()
            
            if field.is_required and not field_value:
                messages.error(request, f'El campo "{field.name}" es obligatorio')
                return render(request, 'public_portal/register.html', {
                    'gym': gym,
                    'settings': settings,
                    'franchise_gyms': franchise_gyms,
                    'custom_fields': custom_fields,
                })
            
            if field_value:
                extra_data[field.slug] = field_value
        
        # Verificar si ya existe
        if Client.objects.filter(gym=target_gym, email=email).exists():
            messages.error(request, 'Ya existe una cuenta con este email en este gimnasio')
            return render(request, 'public_portal/register.html', {
                'gym': gym,
                'settings': settings,
                'franchise_gyms': franchise_gyms,
                'custom_fields': custom_fields,
            })
        
        # Crear usuario y cliente
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            # Crear usuario
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=False,
                is_active=not settings.require_staff_approval  # Si requiere aprobación, inactivo
            )
            
            # Crear cliente
            client = Client.objects.create(
                gym=target_gym,
                user=user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone,
                status='LEAD' if settings.require_staff_approval else 'ACTIVE',
                extra_data=extra_data,
            )
            
            # Si requiere aprobación manual
            if settings.require_staff_approval:
                messages.info(request, '✅ Registro exitoso. Tu cuenta será revisada por nuestro equipo.')
                return redirect('public_gym_home', slug=slug)
            
            # Login automático
            user_authenticated = authenticate(request, username=email, password=password)
            if user_authenticated:
                auth_login(request, user_authenticated)
                messages.success(request, f'¡Bienvenido {first_name}! Tu cuenta ha sido creada.')
                return redirect('public_schedule', slug=slug)
            
        except Exception as e:
            messages.error(request, f'Error al crear la cuenta: {str(e)}')
    
    context = {
        'gym': gym,
        'settings': settings,
        'franchise_gyms': franchise_gyms,
        'custom_fields': custom_fields,
        'show_gym_selector': gym.franchise and franchise_gyms.count() > 1,
    }
    
    return render(request, 'public_portal/register.html', context)


# ===========================
# LOGIN DE CLIENTES
# ===========================

def public_login(request, slug):
    """Login para clientes"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', {
            'message': 'Gimnasio no encontrado'
        }, status=404)
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # Verificar que el usuario es un cliente de este gym
            try:
                client = Client.objects.get(user=user, gym=gym)
                auth_login(request, user)
                
                # Redirigir a donde venía o al horario
                next_url = request.GET.get('next', 'public_schedule')
                if next_url.startswith('/'):
                    return redirect(next_url)
                return redirect(next_url, slug=slug)
                
            except Client.DoesNotExist:
                messages.error(request, 'No tienes acceso a este gimnasio')
        else:
            messages.error(request, 'Email o contraseña incorrectos')
    
    context = {
        'gym': gym,
        'settings': settings,
        'can_register': settings.allow_self_registration,
    }
    
    return render(request, 'public_portal/login.html', context)


def public_logout(request, slug):
    """Logout de clientes"""
    auth_logout(request)
    messages.success(request, 'Has cerrado sesión correctamente')
    return redirect('public_gym_home', slug=slug)


# ===========================
# WIDGETS EMBEBIBLES (IFRAME)
# ===========================

def embed_schedule(request, slug):
    """Widget embebible del horario (vista de lista con botones de reserva)"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym or not settings.allow_embedding or not settings.show_schedule:
        return HttpResponse('Embedding not allowed', status=403)
    
    # Verificar dominio permitido (si está configurado)
    referer = request.META.get('HTTP_REFERER', '')
    if settings.embed_domains:
        allowed_domains = [d.strip() for d in settings.embed_domains.split('\n') if d.strip()]
        domain_allowed = any(domain in referer for domain in allowed_domains)
        if allowed_domains and not domain_allowed:
            return HttpResponse('Domain not allowed', status=403)
    
    activities = Activity.objects.filter(
        gym=gym,
        is_visible_online=True
    )
    
    # Tema (light/dark)
    theme = request.GET.get('theme', 'light')
    
    # Verificar si el usuario está autenticado
    is_authenticated = request.user.is_authenticated
    
    context = {
        'gym': gym,
        'settings': settings,
        'activities': activities,
        'theme': theme,
        'is_embed': True,
        'is_authenticated': is_authenticated,
    }
    
    return render(request, 'public_portal/embed/schedule_list.html', context)


def embed_schedule_calendar(request, slug):
    """Widget embebible del horario (vista de calendario FullCalendar)"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym or not settings.allow_embedding or not settings.show_schedule:
        return HttpResponse('Embedding not allowed', status=403)
    
    # Verificar dominio permitido (si está configurado)
    referer = request.META.get('HTTP_REFERER', '')
    if settings.embed_domains:
        allowed_domains = [d.strip() for d in settings.embed_domains.split('\n') if d.strip()]
        domain_allowed = any(domain in referer for domain in allowed_domains)
        if allowed_domains and not domain_allowed:
            return HttpResponse('Domain not allowed', status=403)
    
    activities = Activity.objects.filter(
        gym=gym,
        is_visible_online=True
    )
    
    # Tema (light/dark)
    theme = request.GET.get('theme', 'light')
    
    context = {
        'gym': gym,
        'settings': settings,
        'activities': activities,
        'theme': theme,
        'is_embed': True,
    }
    
    return render(request, 'public_portal/embed/schedule.html', context)
