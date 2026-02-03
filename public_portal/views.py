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
from clients.models import Client, ClientMembership
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
# BÚSQUEDA DE GIMNASIOS
# ===========================

def gym_search_landing(request):
    """Página de búsqueda de gimnasios - Landing principal del portal público"""
    query = request.GET.get('q', '').strip()
    gyms = []
    
    if query and len(query) >= 2:
        # Buscar gimnasios por nombre o ciudad
        gym_settings = PublicPortalSettings.objects.filter(
            public_portal_enabled=True
        ).filter(
            Q(gym__name__icontains=query) |
            Q(gym__commercial_name__icontains=query) |
            Q(gym__city__icontains=query)
        ).select_related('gym')[:20]
        
        gyms = [
            {
                'name': ps.gym.commercial_name or ps.gym.name,
                'city': ps.gym.city or '',
                'slug': ps.public_slug,
                'logo': ps.gym.logo.url if ps.gym.logo else None,
                'brand_color': ps.gym.brand_color or '#1e293b',
            }
            for ps in gym_settings
        ]
    
    # Para AJAX requests, devolver JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'gyms': gyms})
    
    context = {
        'query': query,
        'gyms': gyms,
    }
    return render(request, 'public_portal/gym_search.html', context)


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
    
    # Obtener anuncios activos para la HOME
    from marketing.models import Advertisement
    from django.db.models import Q
    now = timezone.now()
    
    def filter_ads_by_screen(queryset, screen='HOME'):
        """Filtrar anuncios por pantalla de manera compatible con SQLite"""
        # Obtener todos y filtrar en Python para evitar problemas con JSONField en SQLite
        ads = list(queryset)
        return [
            ad for ad in ads 
            if not ad.target_screens or  # Lista vacía = todas las pantallas
               screen in ad.target_screens or 
               'ALL' in ad.target_screens
        ]
    
    # Anuncios para este gym, activos, en fecha válida
    hero_ads_base = Advertisement.objects.filter(
        Q(gym=gym) | Q(target_gyms=gym),
        is_active=True,
        start_date__lte=now,
        position='HERO_CAROUSEL'
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    ).distinct().order_by('priority', '-created_at')
    
    hero_ads = filter_ads_by_screen(hero_ads_base, 'HOME')[:5]
    
    footer_ads_base = Advertisement.objects.filter(
        Q(gym=gym) | Q(target_gyms=gym),
        is_active=True,
        start_date__lte=now,
        position='STICKY_FOOTER'
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    ).distinct().order_by('priority', '-created_at')
    
    footer_ads = filter_ads_by_screen(footer_ads_base, 'HOME')
    footer_ad = footer_ads[0] if footer_ads else None
    
    context = {
        'gym': gym,
        'settings': settings,
        'modules': {
            'schedule': settings.show_schedule,
            'pricing': settings.show_pricing,
            'services': settings.show_services,
            'shop': settings.show_shop,
        },
        'hero_ads': hero_ads,
        'footer_ad': footer_ad,
    }
    
    return render(request, 'public_portal/home.html', context)


# ===========================
# HORARIO PÚBLICO
# ===========================

def public_schedule(request, slug):
    """Calendario público de clases - vista lista estilo Mindbody"""
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
    
    # Vista: 'list' (por defecto, estilo Mindbody) o 'calendar' (grid)
    view_type = request.GET.get('view', 'list')
    
    context = {
        'gym': gym,
        'settings': settings,
        'activities': activities,
        'can_book': settings.allow_online_booking,
        'requires_login': settings.booking_requires_login,
        'view_type': view_type,
    }
    
    # Usar template según vista
    if view_type == 'calendar':
        return render(request, 'public_portal/schedule.html', context)
    return render(request, 'public_portal/schedule_list.html', context)


def api_public_schedule_events(request, slug):
    """API para FullCalendar y vista lista - solo sesiones de actividades visibles"""
    from datetime import timedelta
    
    gym, settings = get_gym_by_slug(slug)
    
    if not gym or not settings.show_schedule:
        return JsonResponse({'error': 'Not allowed'}, status=403)
    
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    # Si no se proporcionan fechas, usar rango por defecto (semana actual)
    if not start:
        start = timezone.now().date()
    if not end:
        end = timezone.now().date() + timedelta(days=14)
    
    sessions = ActivitySession.objects.filter(
        gym=gym,
        activity__is_visible_online=True,
        start_datetime__gte=start,
        start_datetime__lte=end
    ).select_related('activity', 'activity__category', 'staff', 'staff__user', 'room')
    
    # Obtener info de membresía del cliente si está autenticado
    client = None
    active_membership = None
    membership_activities = set()  # IDs de actividades permitidas por la membresía
    membership_categories = set()  # IDs de categorías permitidas
    has_unlimited_access = False
    
    if request.user.is_authenticated:
        try:
            client = Client.objects.get(user=request.user, gym=gym)
            # Obtener membresía activa
            active_membership = ClientMembership.objects.filter(
                client=client,
                status='ACTIVE'
            ).select_related('plan').first()
            
            if active_membership:
                # Obtener reglas de acceso de la membresía
                access_rules = active_membership.access_rules.all()
                
                if not access_rules.exists():
                    # Si no hay reglas específicas, tiene acceso ilimitado a todo
                    has_unlimited_access = True
                else:
                    for rule in access_rules:
                        if rule.activity_id:
                            membership_activities.add(rule.activity_id)
                        if rule.activity_category_id:
                            membership_categories.add(rule.activity_category_id)
                        if rule.service_id is None and rule.service_category_id is None and \
                           rule.activity_id is None and rule.activity_category_id is None:
                            # Regla general = acceso a todo
                            has_unlimited_access = True
                            
        except Client.DoesNotExist:
            pass
    
    events = []
    for session in sessions:
        # Calcular disponibilidad
        attendee_count = session.attendees.count()
        spots_available = session.max_capacity - attendee_count
        
        # Obtener imagen de la actividad
        activity_image = None
        if session.activity.image:
            activity_image = session.activity.image.url
        
        # Staff info
        staff_name = None
        staff_photo = None
        if session.staff:
            staff_name = session.staff.user.get_full_name()
            if hasattr(session.staff, 'photo') and session.staff.photo:
                staff_photo = session.staff.photo.url
        
        # Intensidad
        intensity_map = {'LOW': 'Baja', 'MEDIUM': 'Media', 'HIGH': 'Alta'}
        intensity = intensity_map.get(session.activity.intensity_level, 'Media')
        
        # Determinar si el cliente puede reservar esta actividad
        can_book = False
        booking_message = None
        
        if not request.user.is_authenticated:
            can_book = False
            booking_message = 'login_required'
        elif not active_membership:
            can_book = False
            booking_message = 'no_membership'
        elif has_unlimited_access:
            can_book = True
        elif session.activity.id in membership_activities:
            can_book = True
        elif session.activity.category_id and session.activity.category_id in membership_categories:
            can_book = True
        else:
            can_book = False
            booking_message = 'activity_not_included'
        
        events.append({
            'id': f'sess_{session.id}',
            'title': session.activity.name,
            'start': session.start_datetime.isoformat(),
            'end': session.end_datetime.isoformat(),
            'backgroundColor': session.activity.color,
            'borderColor': session.activity.color,
            'extendedProps': {
                'type': 'session',
                'activity_id': session.activity.id,
                'staff': staff_name,
                'staff_photo': staff_photo,
                'room': session.room.name if session.room else None,
                'attendees': attendee_count,
                'max_capacity': session.max_capacity,
                'spots_available': spots_available,
                'is_full': spots_available <= 0,
                'image': activity_image,
                'description': session.activity.description or '',
                'intensity': intensity,
                'duration': session.activity.duration,
                'category': session.activity.category.name if session.activity.category else None,
                'can_book': can_book,
                'booking_message': booking_message,
                'membership_name': active_membership.name if active_membership else None,
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
    
    # Verificar elegibilidad de ofertas para nuevos clientes
    client = None
    if request.user.is_authenticated:
        try:
            client = Client.objects.get(user=request.user, gym=gym)
        except Client.DoesNotExist:
            pass
    
    # Añadir info de elegibilidad a cada plan (filtrando los ocultos)
    plans_with_eligibility = []
    for plan in plans:
        # Usar nuevo sistema de visibilidad
        if client:
            should_show, is_eligible, reason = plan.should_show_to_client(client)
            if not should_show:
                continue  # Ocultar este plan completamente
            
            plan_data = {
                'plan': plan,
                'is_eligible': is_eligible,
                'ineligible_reason': reason,
                'show_badge': plan.has_eligibility_restriction() and plan.get_badge_text()
            }
        else:
            # Usuario no autenticado - mostrar todos los planes
            plan_data = {
                'plan': plan,
                'is_eligible': True,
                'ineligible_reason': '',
                'show_badge': plan.has_eligibility_restriction() and plan.get_badge_text()
            }
        
        plans_with_eligibility.append(plan_data)
    
    context = {
        'gym': gym,
        'settings': settings,
        'plans': plans_with_eligibility,
        'client': client,
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
    
    # Verificar elegibilidad usando el nuevo sistema
    if plan.has_eligibility_restriction():
        is_eligible, reason = plan.is_client_eligible(client)
        if not is_eligible:
            messages.error(request, reason)
            return redirect('public_pricing', slug=slug)
    
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
    
    # Historial de compras/ventas del cliente (últimas 10)
    from sales.models import Order
    orders = Order.objects.filter(
        client=client,
        gym=gym
    ).prefetch_related('items', 'refunds').order_by('-created_at')[:10]
    
    # Advance payment feature
    finance_settings = getattr(gym, 'finance_settings', None)
    allow_pay_next_fee = bool(finance_settings and getattr(finance_settings, 'allow_client_pay_next_fee', False))
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'memberships': memberships,
        'bookings': bookings,
        'gamification': gamification_data,
        'orders': orders,  # Historial de compras incluyendo devoluciones
        'allow_pay_next_fee': allow_pay_next_fee,
    }
    
    return render(request, 'public_portal/dashboard.html', context)


# ===========================
# PERFIL DEL CLIENTE
# ===========================

@login_required
def public_client_profile(request, slug):
    """Página de perfil completo del cliente estilo app"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    # Verificar que el usuario es cliente de este gym
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        messages.error(request, 'No tienes acceso a este gimnasio')
        return redirect('public_login', slug=slug)
    
    # Procesar formulario de edición
    if request.method == 'POST':
        client.first_name = request.POST.get('first_name', client.first_name)
        client.last_name = request.POST.get('last_name', client.last_name)
        client.email = request.POST.get('email', client.email)
        client.phone_number = request.POST.get('phone', client.phone_number)
        birth_date = request.POST.get('birth_date')
        if birth_date:
            from datetime import datetime as dt
            try:
                client.birth_date = dt.strptime(birth_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if 'photo' in request.FILES:
            client.photo = request.FILES['photo']
        
        client.save()
        
        # Actualizar email del usuario si cambió
        if client.user and request.POST.get('email'):
            client.user.email = request.POST.get('email')
            client.user.save(update_fields=['email'])
        
        messages.success(request, '¡Perfil actualizado correctamente!')
        return redirect('public_client_profile', slug=slug)
    
    # Membresía activa
    active_membership = Membership.objects.filter(
        client=client,
        gym=gym,
        status='ACTIVE'
    ).select_related('plan').first()
    
    # Calcular porcentaje de sesiones usadas si aplica
    if active_membership and active_membership.sessions_total:
        active_membership.sessions_percentage = int(
            (active_membership.sessions_used or 0) / active_membership.sessions_total * 100
        )
        # sessions_remaining ya es una propiedad calculada del modelo
    
    # Estadísticas del cliente
    from activities.models import ActivitySessionBooking
    from clients.models import ClientVisit
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    stats = {
        'total_visits': ClientVisit.objects.filter(client=client).count(),
        'current_streak': getattr(client, 'current_streak', 0),
        'bookings_this_month': ActivitySessionBooking.objects.filter(
            client=client,
            booked_at__gte=this_month_start,
            status='CONFIRMED'
        ).count(),
    }
    
    # Próximas reservas (conteo)
    upcoming_bookings_count = ActivitySessionBooking.objects.filter(
        client=client,
        session__start_datetime__gte=timezone.now(),
        status='CONFIRMED'
    ).count()
    
    # Gamificación
    gamification_enabled = False
    achievements_unlocked = 0
    achievements_total = 0
    rank_position = 0
    
    try:
        from gamification.models import GamificationSettings, ClientProgress, Achievement, ClientAchievement
        gamification_settings = gym.gamification_settings
        if gamification_settings.enabled and gamification_settings.show_on_portal:
            gamification_enabled = True
            progress, _ = ClientProgress.objects.get_or_create(client=client)
            
            rank_position = ClientProgress.objects.filter(
                client__gym=gym,
                total_xp__gt=progress.total_xp
            ).count() + 1
            
            achievements_unlocked = ClientAchievement.objects.filter(client=client).count()
            achievements_total = Achievement.objects.filter(gym=gym, is_active=True).count()
            
            stats['current_streak'] = progress.current_streak
    except Exception:
        pass
    
    # Tarjeta guardada
    has_saved_card = False
    last_card_digits = ''
    try:
        from finance.models import ClientRedsysToken
        saved_card = ClientRedsysToken.objects.filter(client=client, is_active=True).first()
        if saved_card:
            has_saved_card = True
            last_card_digits = saved_card.card_last_four or ''
    except Exception:
        pass
    
    # Programa de referidos
    referral_enabled = False
    try:
        from discounts.referral_service import is_referral_enabled
        referral_enabled = is_referral_enabled(gym)
    except Exception:
        pass
    
    # Monedero / Wallet
    wallet_enabled = False
    wallet_balance = 0
    try:
        from finance.wallet_service import WalletService
        from finance.models import WalletSettings
        wallet_settings = WalletService.get_wallet_settings(gym)
        if wallet_settings.wallet_enabled and wallet_settings.show_in_client_portal:
            wallet_enabled = True
            wallet_balance = WalletService.get_balance(client, gym)
    except Exception:
        pass
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'active_membership': active_membership,
        'stats': stats,
        'upcoming_bookings_count': upcoming_bookings_count,
        'gamification_enabled': gamification_enabled,
        'achievements_unlocked': achievements_unlocked,
        'achievements_total': achievements_total,
        'rank_position': rank_position,
        'has_saved_card': has_saved_card,
        'last_card_digits': last_card_digits,
        'referral_enabled': referral_enabled,
        'wallet_enabled': wallet_enabled,
        'wallet_balance': wallet_balance,
    }
    
    return render(request, 'public_portal/profile.html', context)


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
        'gamification_settings': gamification_settings,
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
    join_waitlist = data.get('join_waitlist', False)
    
    if not session_id:
        return JsonResponse({'success': False, 'error': 'Session ID required'}, status=400)
    
    # Obtener la sesión
    try:
        session = ActivitySession.objects.select_related('activity', 'activity__policy').get(
            id=session_id,
            gym=gym
        )
    except ActivitySession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)
    
    # Usar el servicio de políticas para validar
    from activities.policy_service import BookingPolicyService, WaitlistPolicyService
    
    validation = BookingPolicyService.can_book(session, client)
    
    if not validation.success:
        # Si la clase está llena pero hay waitlist disponible y el usuario quiere unirse
        if validation.data.get('waitlist_available') and join_waitlist:
            waitlist_result = WaitlistPolicyService.join_waitlist(session, client)
            return JsonResponse(waitlist_result.to_dict(), status=200 if waitlist_result.success else 400)
        
        return JsonResponse({
            'success': False, 
            'error': validation.message,
            **validation.data
        }, status=400)
    
    # Verificar que tenga membresía activa (opcional según config)
    from clients.models import ClientMembership as Membership
    active_membership = Membership.objects.filter(
        client=client,
        gym=gym,
        status='ACTIVE',
        start_date__lte=timezone.now().date()
    ).first()
    
    if not active_membership and settings.booking_requires_login:
        return JsonResponse({'success': False, 'error': 'Necesitas una membresía activa'}, status=400)
    
    # Crear la reserva
    from activities.models import ActivitySessionBooking
    booking = ActivitySessionBooking.objects.create(
        session=session,
        client=client,
        status='CONFIRMED'
    )
    
    # Disparar notificaciones y workflows de marketing
    try:
        from marketing.signals import on_client_added_to_class
        on_client_added_to_class(client, session)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error triggering booking notification: {e}")
    
    return JsonResponse({
        'success': True,
        'booking_id': booking.id,
        'message': 'Reserva confirmada',
        'spots_available': validation.data.get('spots_available')
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
        booking = ActivitySessionBooking.objects.select_related(
            'session', 'session__activity', 'session__activity__policy'
        ).get(
            id=booking_id,
            client=client
        )
    except ActivitySessionBooking.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Booking not found'}, status=404)
    
    # Usar el servicio de políticas para validar y ejecutar
    from activities.policy_service import CancellationPolicyService
    
    # Primero verificar si puede cancelar
    validation = CancellationPolicyService.can_cancel(booking)
    
    if not validation.success:
        return JsonResponse({
            'success': False,
            'error': validation.message
        }, status=400)
    
    # Si tiene penalización, verificar si el usuario confirmó
    import json
    data = json.loads(request.body) if request.body else {}
    confirmed = data.get('confirmed', False)
    
    if validation.data.get('has_penalty') and not confirmed:
        # Devolver información de penalización para que el frontend confirme
        return JsonResponse({
            'success': False,
            'requires_confirmation': True,
            'penalty_info': {
                'type': validation.data.get('penalty_type'),
                'description': validation.data.get('penalty_description'),
                'amount': validation.data.get('penalty_amount'),
                'hours_until_class': validation.data.get('hours_until_class'),
                'window_hours': validation.data.get('window_hours')
            },
            'message': validation.message
        }, status=200)
    
    # Ejecutar la cancelación
    result = CancellationPolicyService.execute_cancellation(booking, cancelled_by=request.user)
    
    # Disparar notificaciones de cancelación
    if result.success:
        try:
            from marketing.signals import on_client_removed_from_class
            cancellation_type = 'LATE' if result.data.get('penalty_applied') else 'EARLY'
            on_client_removed_from_class(client, booking.session, cancellation_type)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Error triggering cancel notification: {e}")
    
    return JsonResponse({
        'success': result.success,
        'message': result.message,
        'penalty_applied': result.data.get('penalty_applied', False),
        'penalty_type': result.data.get('penalty_type')
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


# ===========================
# PÁGINAS DEL PERFIL DEL CLIENTE
# ===========================

@login_required
def public_attendance_history(request, slug):
    """Historial de asistencia del cliente"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Historial de visitas
    from clients.models import ClientVisit
    visits = ClientVisit.objects.filter(client=client).order_by('-date', '-check_in_time')[:50]
    
    # Historial de asistencia a clases
    from activities.models import ActivitySessionBooking
    class_attendance = ActivitySessionBooking.objects.filter(
        client=client,
        attended=True
    ).select_related('session__activity').order_by('-session__start_datetime')[:50]
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'visits': visits,
        'class_attendance': class_attendance,
    }
    
    return render(request, 'public_portal/profile/attendance_history.html', context)


@login_required
def public_payment_history(request, slug):
    """Historial de pagos del cliente"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Historial de pagos
    from sales.models import Order
    orders = Order.objects.filter(
        client=client,
        gym=gym,
        status__in=['COMPLETED', 'PAID', 'PARTIALLY_REFUNDED']
    ).prefetch_related('items', 'payments').order_by('-created_at')[:50]
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'orders': orders,
    }
    
    return render(request, 'public_portal/profile/payment_history.html', context)


@login_required
def public_payment_methods(request, slug):
    """Métodos de pago guardados del cliente"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Obtener configuración de pasarelas
    finance_settings = getattr(gym, 'finance_settings', None)
    stripe_enabled = bool(finance_settings and finance_settings.has_stripe)
    redsys_enabled = bool(finance_settings and finance_settings.has_redsys)
    
    # Determinar qué pasarela mostrar según la estrategia
    gateway_strategy = finance_settings.app_gateway_strategy if finance_settings else 'STRIPE_ONLY'
    
    show_stripe = False
    show_redsys = False
    show_choice = False
    
    if gateway_strategy == 'STRIPE_ONLY':
        show_stripe = stripe_enabled
    elif gateway_strategy == 'REDSYS_ONLY':
        show_redsys = redsys_enabled
    elif gateway_strategy == 'STRIPE_PRIMARY':
        show_stripe = stripe_enabled
        show_redsys = redsys_enabled and not stripe_enabled
    elif gateway_strategy == 'REDSYS_PRIMARY':
        show_redsys = redsys_enabled
        show_stripe = stripe_enabled and not redsys_enabled
    elif gateway_strategy == 'CLIENT_CHOICE':
        show_stripe = stripe_enabled
        show_redsys = redsys_enabled
        show_choice = True
    
    # Tarjetas guardadas
    stripe_cards = []
    redsys_tokens = []
    
    if stripe_enabled:
        from finance.stripe_utils import list_payment_methods
        try:
            stripe_cards = list_payment_methods(client)
        except Exception as e:
            print(f"Error obteniendo tarjetas Stripe: {e}")
    
    if redsys_enabled:
        from finance.models import ClientRedsysToken
        redsys_tokens = list(ClientRedsysToken.objects.filter(client=client))
    
    # Client secret para añadir tarjeta con Stripe
    stripe_client_secret = None
    if show_stripe and stripe_enabled:
        try:
            from finance.stripe_utils import create_setup_intent
            stripe_client_secret = create_setup_intent(client)
        except Exception as e:
            print(f"Error creando SetupIntent: {e}")
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'stripe_cards': stripe_cards,
        'redsys_tokens': redsys_tokens,
        'stripe_public_key': finance_settings.stripe_public_key if finance_settings else '',
        'stripe_client_secret': stripe_client_secret,
        'show_stripe': show_stripe,
        'show_redsys': show_redsys,
        'show_choice': show_choice,
        'gateway_strategy': gateway_strategy,
    }
    
    return render(request, 'public_portal/profile/payment_methods.html', context)


@login_required
def public_orders_history(request, slug):
    """Historial de compras/pedidos del cliente"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Pedidos del cliente
    from sales.models import Order
    orders = Order.objects.filter(
        client=client,
        gym=gym
    ).prefetch_related('items').order_by('-created_at')[:50]
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'orders': orders,
    }
    
    return render(request, 'public_portal/profile/orders_history.html', context)


@login_required
def public_my_memberships(request, slug):
    """Membresías del cliente"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Membresías activas e históricas
    memberships = ClientMembership.objects.filter(
        client=client,
        gym=gym
    ).select_related('plan').order_by('-start_date')
    
    # Obtener configuración financiera
    finance_settings = getattr(gym, 'finance_settings', None)
    allow_pay_next_fee = bool(finance_settings and getattr(finance_settings, 'allow_client_pay_next_fee', False))
    
    # Verificar si el cliente tiene método de pago
    from clients.models import ClientPaymentMethod
    has_payment_method = ClientPaymentMethod.objects.filter(client=client).exists()
    
    # Obtener membresía activa para el botón de adelantar cobro
    active_membership = memberships.filter(status='ACTIVE', is_recurring=True).first()
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'memberships': memberships,
        'allow_pay_next_fee': allow_pay_next_fee,
        'has_payment_method': has_payment_method,
        'active_membership': active_membership,
    }
    
    return render(request, 'public_portal/profile/my_memberships.html', context)


@login_required
def public_chat(request, slug):
    """Chat del cliente con el gimnasio"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Obtener o crear la sala de chat
    from clients.models import ChatRoom, ChatMessage
    room, created = ChatRoom.objects.get_or_create(
        client=client,
        defaults={'gym': gym}
    )
    
    # Obtener mensajes del chat
    messages_list = ChatMessage.objects.filter(
        room=room
    ).select_related('sender').order_by('created_at')
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'room': room,
        'messages': messages_list,
    }
    
    return render(request, 'public_portal/chat.html', context)


@login_required
def public_chat_send_message(request, slug):
    """Enviar mensaje en el chat (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return JsonResponse({'error': 'Gimnasio no encontrado'}, status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=403)
    
    from clients.models import ChatRoom, ChatMessage
    import json
    
    # Obtener o crear sala
    room, _ = ChatRoom.objects.get_or_create(
        client=client,
        defaults={'gym': gym}
    )
    
    # Crear mensaje
    data = json.loads(request.body)
    message_text = data.get('message', '').strip()
    
    if not message_text:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)
    
    message = ChatMessage.objects.create(
        room=room,
        sender=request.user,
        message=message_text
    )
    
    # Actualizar timestamp de la sala
    room.last_message_at = timezone.now()
    room.save()
    
    return JsonResponse({
        'success': True,
        'message': {
            'id': message.id,
            'message': message.message,
            'created_at': message.created_at.isoformat(),
            'sender_name': request.user.get_full_name() or 'Yo'
        }
    })


# ============================================================
# Adelantar Cobro y Pago de Membresía Pendiente
# ============================================================

@login_required
def public_advance_payment(request, slug):
    """Vista para adelantar el cobro de la siguiente cuota"""
    from datetime import timedelta
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Verificar que la funcionalidad esté habilitada
    finance_settings = getattr(gym, 'finance_settings', None)
    if not finance_settings or not finance_settings.allow_client_pay_next_fee:
        messages.error(request, 'Esta funcionalidad no está disponible.')
        return redirect('public_my_memberships', slug=slug)
    
    # Obtener membresía activa recurrente
    active_membership = ClientMembership.objects.filter(
        client=client,
        gym=gym,
        status='ACTIVE',
        is_recurring=True
    ).first()
    
    if not active_membership:
        messages.error(request, 'No tienes una membresía activa recurrente.')
        return redirect('public_my_memberships', slug=slug)
    
    # Verificar método de pago
    from clients.models import ClientPaymentMethod
    payment_method = ClientPaymentMethod.objects.filter(client=client).first()
    has_payment_method = payment_method is not None
    
    # Calcular datos del próximo cobro
    next_billing_date = active_membership.next_billing_date or (active_membership.end_date + timedelta(days=1))
    amount = active_membership.price
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'membership': active_membership,
        'next_billing_date': next_billing_date,
        'amount': amount,
        'has_payment_method': has_payment_method,
    }
    
    return render(request, 'public_portal/profile/advance_payment.html', context)


@login_required
def public_process_advance_payment(request, slug):
    """Procesar el adelanto de cobro"""
    from datetime import timedelta
    from django.db import transaction
    from finance.stripe_utils import charge_client
    from finance.models import ClientPayment
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return JsonResponse({'error': 'Gimnasio no encontrado'}, status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    
    # Verificar configuración
    finance_settings = getattr(gym, 'finance_settings', None)
    if not finance_settings or not finance_settings.allow_client_pay_next_fee:
        return JsonResponse({'error': 'Funcionalidad no habilitada'}, status=403)
    
    # Obtener membresía
    active_membership = ClientMembership.objects.filter(
        client=client,
        gym=gym,
        status='ACTIVE',
        is_recurring=True
    ).first()
    
    if not active_membership:
        return JsonResponse({'error': 'No tienes una membresía activa recurrente'}, status=400)
    
    # Verificar método de pago
    from clients.models import ClientPaymentMethod
    payment_method = ClientPaymentMethod.objects.filter(client=client).first()
    if not payment_method:
        return JsonResponse({'error': 'No tienes un método de pago vinculado'}, status=400)
    
    amount = active_membership.price
    concept = f"Adelanto cuota: {active_membership.name}"
    
    try:
        with transaction.atomic():
            # Realizar el cobro
            payment_method_id = payment_method.stripe_payment_method_id
            result = charge_client(client, float(amount), payment_method_id, concept)
            
            if not result or not result.get('success'):
                error_msg = result.get('error', 'Error al procesar el pago') if result else 'Error al procesar el pago'
                return JsonResponse({'error': error_msg}, status=400)
            
            # Registrar el pago
            ClientPayment.objects.create(
                client=client,
                gym=gym,
                membership=active_membership,
                amount=amount,
                payment_method='STRIPE',
                status='COMPLETED',
                description=concept,
                stripe_payment_intent_id=result.get('payment_intent_id', '')
            )
            
            # Extender la membresía
            active_membership.end_date = active_membership.end_date + timedelta(days=30)
            if active_membership.next_billing_date:
                active_membership.next_billing_date = active_membership.next_billing_date + timedelta(days=30)
            active_membership.save()
            
            return JsonResponse({
                'success': True,
                'message': '¡Pago realizado correctamente!',
                'new_end_date': active_membership.end_date.strftime('%d/%m/%Y'),
                'new_billing_date': active_membership.next_billing_date.strftime('%d/%m/%Y') if active_membership.next_billing_date else None
            })
            
    except Exception as e:
        return JsonResponse({'error': f'Error al procesar el pago: {str(e)}'}, status=500)


@login_required
def public_checkout_membership(request, slug, membership_id):
    """Checkout para pagar una membresía pendiente"""
    from finance.stripe_utils import charge_client
    from finance.models import ClientPayment
    from django.db import transaction
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Obtener la membresía
    membership = get_object_or_404(ClientMembership, id=membership_id, client=client, gym=gym)
    
    # Verificar que esté pendiente de pago
    if membership.status not in ['PENDING', 'PENDING_PAYMENT']:
        messages.error(request, 'Esta membresía no está pendiente de pago.')
        return redirect('public_my_memberships', slug=slug)
    
    # Verificar método de pago
    from clients.models import ClientPaymentMethod
    payment_method = ClientPaymentMethod.objects.filter(client=client).first()
    has_payment_method = payment_method is not None
    
    if request.method == 'POST' and has_payment_method:
        amount = membership.price
        concept = f"Pago membresía: {membership.name}"
        
        try:
            with transaction.atomic():
                payment_method_id = payment_method.stripe_payment_method_id
                result = charge_client(client, float(amount), payment_method_id, concept)
                
                if not result or not result.get('success'):
                    error_msg = result.get('error', 'Error al procesar el pago') if result else 'Error al procesar el pago'
                    messages.error(request, error_msg)
                    return redirect('public_checkout_membership', slug=slug, membership_id=membership_id)
                
                # Registrar el pago
                ClientPayment.objects.create(
                    client=client,
                    gym=gym,
                    membership=membership,
                    amount=amount,
                    payment_method='STRIPE',
                    status='COMPLETED',
                    description=concept,
                    stripe_payment_intent_id=result.get('payment_intent_id', '')
                )
                
                # Activar la membresía
                membership.status = 'ACTIVE'
                membership.save()
                
                messages.success(request, '¡Pago realizado! Tu membresía ya está activa.')
                return redirect('public_my_memberships', slug=slug)
                
        except Exception as e:
            messages.error(request, f'Error al procesar el pago: {str(e)}')
            return redirect('public_checkout_membership', slug=slug, membership_id=membership_id)
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'membership': membership,
        'has_payment_method': has_payment_method,
    }
    
    return render(request, 'public_portal/profile/checkout_membership.html', context)


# ===========================
# RUTINAS
# ===========================

@login_required
def public_routines(request, slug):
    """Lista de rutinas asignadas al cliente"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Obtener rutinas asignadas
    from routines.models import ClientRoutine
    assignments = ClientRoutine.objects.filter(
        client=client,
        is_active=True
    ).select_related('routine').order_by('-start_date')
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'assignments': assignments,
    }
    return render(request, 'public_portal/routines/list.html', context)


@login_required
def public_routine_detail(request, slug, routine_id):
    """Detalle de una rutina con sus días y ejercicios"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Verificar que la rutina está asignada al cliente
    from routines.models import ClientRoutine
    assignment = get_object_or_404(
        ClientRoutine,
        routine_id=routine_id,
        client=client,
        is_active=True
    )
    routine = assignment.routine
    
    # Obtener días con ejercicios
    days = routine.days.all().prefetch_related('exercises__exercise').order_by('order')
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'routine': routine,
        'assignment': assignment,
        'days': days,
    }
    return render(request, 'public_portal/routines/detail.html', context)


# ===========================
# QR CHECK-IN
# ===========================

@login_required
def public_checkin(request, slug):
    """Página principal de check-in con escáner QR"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
    }
    return render(request, 'public_portal/checkin/scanner.html', context)


@login_required
def public_my_qr(request, slug):
    """Genera el código QR personal del cliente"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return JsonResponse({'error': 'Gimnasio no encontrado'}, status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    
    import hashlib
    import time
    from django.conf import settings as django_settings
    
    # Generar token dinámico que cambia cada 30 segundos
    timestamp = int(time.time() // 30)
    raw = f"{client.id}-{timestamp}-{django_settings.SECRET_KEY}"
    token = hashlib.sha256(raw.encode()).hexdigest()[:16]
    
    qr_data = {
        'type': 'client_checkin',
        'client_id': client.id,
        'gym_id': gym.id,
        'token': token,
        'ts': timestamp,
    }
    
    import json
    qr_content = json.dumps(qr_data)
    
    return JsonResponse({
        'qr_content': qr_content,
        'client_name': client.full_name,
        'valid_until': (timestamp + 1) * 30,
    })


@login_required
@csrf_exempt
def public_checkin_process(request, slug):
    """Procesa el check-in escaneando QR de sesión"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return JsonResponse({'error': 'Gimnasio no encontrado'}, status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    
    import json
    try:
        data = json.loads(request.body)
        qr_token = data.get('token', '')
    except:
        return JsonResponse({'error': 'Datos inválidos'}, status=400)
    
    # Verificar el token QR de la sesión
    from activities.checkin_views import verify_qr_token
    
    try:
        session, client_verified = verify_qr_token(qr_token, client)
        
        if session and client_verified:
            # Crear registro de check-in
            from activities.models import SessionCheckin
            checkin, created = SessionCheckin.objects.get_or_create(
                session=session,
                client=client,
                defaults={'ip_address': request.META.get('REMOTE_ADDR', '')}
            )
            
            if created:
                return JsonResponse({
                    'success': True,
                    'message': f'¡Check-in exitoso para {session.activity.name}!',
                    'session': session.activity.name,
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'Ya tenías check-in para esta sesión',
                    'already_checked_in': True,
                })
        else:
            return JsonResponse({'error': 'Token QR inválido o expirado'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ===========================
# DOCUMENTOS
# ===========================

@login_required
def public_documents(request, slug):
    """Lista de documentos del cliente"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Obtener documentos del cliente
    from clients.models import ClientDocument
    documents = ClientDocument.objects.filter(
        client=client
    ).select_related('template').order_by('-created_at')
    
    # Contar pendientes
    pending_count = documents.filter(signed_at__isnull=True).count()
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'documents': documents,
        'pending_count': pending_count,
    }
    return render(request, 'public_portal/documents/list.html', context)


@login_required
def public_document_detail(request, slug, document_id):
    """Ver detalle de un documento"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    from clients.models import ClientDocument
    document = get_object_or_404(ClientDocument, id=document_id, client=client)
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'document': document,
    }
    return render(request, 'public_portal/documents/detail.html', context)


@login_required
@csrf_exempt
def public_document_sign(request, slug, document_id):
    """Firmar un documento digitalmente"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return JsonResponse({'error': 'Gimnasio no encontrado'}, status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    
    from clients.models import ClientDocument
    document = get_object_or_404(ClientDocument, id=document_id, client=client)
    
    if document.signed_at:
        return JsonResponse({'error': 'Documento ya firmado'}, status=400)
    
    import json
    try:
        data = json.loads(request.body)
        signature_data = data.get('signature', '')
    except:
        return JsonResponse({'error': 'Datos inválidos'}, status=400)
    
    if not signature_data:
        return JsonResponse({'error': 'Firma requerida'}, status=400)
    
    # Guardar firma
    document.signature = signature_data
    document.signed_at = timezone.now()
    document.signed_ip = request.META.get('REMOTE_ADDR', '')
    document.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Documento firmado correctamente',
    })


# ===========================
# RECUPERAR CONTRASEÑA
# ===========================

def public_forgot_password(request, slug):
    """Solicitar recuperación de contraseña"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, 'Por favor, introduce tu email.')
            return redirect('public_forgot_password', slug=slug)
        
        # Buscar cliente
        try:
            client = Client.objects.get(email__iexact=email, gym=gym)
            user = client.user
            
            if user:
                # Generar token
                import secrets
                from django.core.cache import cache
                
                token = secrets.token_urlsafe(32)
                cache_key = f"password_reset_{token}"
                cache.set(cache_key, user.id, timeout=3600)  # 1 hora
                
                # Enviar email
                reset_url = request.build_absolute_uri(
                    f"/public/gym/{slug}/reset-password/{token}/"
                )
                
                # TODO: Enviar email real
                try:
                    from django.core.mail import send_mail
                    send_mail(
                        subject=f'Recuperar contraseña - {gym.name}',
                        message=f'Haz clic en el siguiente enlace para restablecer tu contraseña:\n\n{reset_url}\n\nEste enlace expirará en 1 hora.',
                        from_email=None,
                        recipient_list=[email],
                        fail_silently=True,
                    )
                except:
                    pass
                
                messages.success(request, 'Si el email existe, recibirás instrucciones para recuperar tu contraseña.')
            else:
                messages.success(request, 'Si el email existe, recibirás instrucciones para recuperar tu contraseña.')
        except Client.DoesNotExist:
            # No revelar si el email existe o no
            messages.success(request, 'Si el email existe, recibirás instrucciones para recuperar tu contraseña.')
        
        return redirect('public_login', slug=slug)
    
    context = {
        'gym': gym,
        'settings': settings,
    }
    return render(request, 'public_portal/auth/forgot_password.html', context)


def public_reset_password(request, slug, token):
    """Restablecer contraseña con token"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    from django.core.cache import cache
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    cache_key = f"password_reset_{token}"
    user_id = cache.get(cache_key)
    
    if not user_id:
        messages.error(request, 'El enlace ha expirado o es inválido.')
        return redirect('public_forgot_password', slug=slug)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('public_forgot_password', slug=slug)
    
    if request.method == 'POST':
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        if not password or len(password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            return redirect('public_reset_password', slug=slug, token=token)
        
        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('public_reset_password', slug=slug, token=token)
        
        user.set_password(password)
        user.save()
        
        # Invalidar token
        cache.delete(cache_key)
        
        messages.success(request, '¡Contraseña actualizada! Ya puedes iniciar sesión.')
        return redirect('public_login', slug=slug)
    
    context = {
        'gym': gym,
        'settings': settings,
        'token': token,
    }
    return render(request, 'public_portal/auth/reset_password.html', context)


# ===========================
# PWA - MANIFEST DINÁMICO
# ===========================

def gym_manifest(request, slug):
    """
    Genera un manifest.json dinámico para cada gimnasio.
    Esto permite que cada gym tenga su propia PWA con nombre, colores e iconos personalizados.
    """
    import json
    from django.urls import reverse
    from django.conf import settings as django_settings
    
    gym = get_object_or_404(Gym, slug=slug)
    
    # Nombre para mostrar
    gym_name = gym.commercial_name or gym.name
    short_name = gym_name[:12] if len(gym_name) > 12 else gym_name
    
    # Color de la marca
    theme_color = gym.brand_color or "#0f172a"
    
    # URL base del gym - usar reverse para obtener la URL correcta
    base_url = reverse('public_gym_home', kwargs={'slug': slug})
    
    # Construir iconos - si el gym tiene logo, usamos versiones escaladas del logo
    # Si no, usamos iconos genéricos
    if gym.logo:
        # El gym tiene logo - usamos endpoint dinámico para iconos
        icon_base = reverse('gym_pwa_icon', kwargs={'slug': slug, 'size': 72}).rsplit('/72/', 1)[0]
        icons = [
            {
                "src": f"{icon_base}/72/",
                "sizes": "72x72",
                "type": "image/png"
            },
            {
                "src": f"{icon_base}/96/",
                "sizes": "96x96",
                "type": "image/png"
            },
            {
                "src": f"{icon_base}/128/",
                "sizes": "128x128",
                "type": "image/png"
            },
            {
                "src": f"{icon_base}/144/",
                "sizes": "144x144",
                "type": "image/png"
            },
            {
                "src": f"{icon_base}/152/",
                "sizes": "152x152",
                "type": "image/png"
            },
            {
                "src": f"{icon_base}/192/",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": f"{icon_base}/384/",
                "sizes": "384x384",
                "type": "image/png"
            },
            {
                "src": f"{icon_base}/512/",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    else:
        # Sin logo - usar iconos genéricos
        icons = [
            {"src": "/static/icons/icon-72x72.png", "sizes": "72x72", "type": "image/png"},
            {"src": "/static/icons/icon-96x96.png", "sizes": "96x96", "type": "image/png"},
            {"src": "/static/icons/icon-128x128.png", "sizes": "128x128", "type": "image/png"},
            {"src": "/static/icons/icon-144x144.png", "sizes": "144x144", "type": "image/png"},
            {"src": "/static/icons/icon-152x152.png", "sizes": "152x152", "type": "image/png"},
            {"src": "/static/icons/icon-192x192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static/icons/icon-384x384.png", "sizes": "384x384", "type": "image/png"},
            {"src": "/static/icons/icon-512x512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
        ]
    
    manifest = {
        "name": f"{gym_name} - Portal Cliente",
        "short_name": short_name,
        "description": f"Accede a {gym_name} desde tu móvil",
        "start_url": base_url,
        "display": "standalone",
        "background_color": "#f8fafc",
        "theme_color": theme_color,
        "orientation": "portrait-primary",
        "scope": base_url,
        "icons": icons,
        "shortcuts": [
            {
                "name": "Horario",
                "short_name": "Horario",
                "description": "Ver horario de clases",
                "url": f"{base_url}schedule/",
                "icons": [{"src": "/static/icons/icon-96x96.png", "sizes": "96x96"}]
            },
            {
                "name": "Mi Perfil",
                "short_name": "Perfil",
                "description": "Ver mi perfil",
                "url": f"{base_url}profile/",
                "icons": [{"src": "/static/icons/icon-96x96.png", "sizes": "96x96"}]
            }
        ]
    }
    
    return HttpResponse(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        content_type='application/manifest+json'
    )


def gym_pwa_icon(request, slug, size):
    """
    Genera iconos PWA dinámicos basados en el logo del gimnasio.
    Redimensiona el logo al tamaño solicitado.
    """
    from PIL import Image
    from io import BytesIO
    import os
    
    gym = get_object_or_404(Gym, slug=slug)
    
    # Validar tamaño - incluir tamaños pequeños para favicons
    valid_sizes = [16, 32, 72, 96, 128, 144, 152, 192, 384, 512]
    if size not in valid_sizes:
        size = 192  # Default
    
    # Si el gym tiene logo, redimensionarlo
    if gym.logo:
        try:
            # Abrir imagen del logo
            img = Image.open(gym.logo.path)
            
            # Convertir a RGBA si es necesario
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Crear imagen cuadrada con fondo del color de marca
            brand_color = gym.brand_color or "#0f172a"
            # Convertir hex a RGB
            brand_rgb = tuple(int(brand_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            # Crear fondo cuadrado
            background = Image.new('RGBA', (size, size), (*brand_rgb, 255))
            
            # Redimensionar logo manteniendo proporción
            img.thumbnail((int(size * 0.7), int(size * 0.7)), Image.Resampling.LANCZOS)
            
            # Centrar logo sobre fondo
            offset_x = (size - img.width) // 2
            offset_y = (size - img.height) // 2
            background.paste(img, (offset_x, offset_y), img if img.mode == 'RGBA' else None)
            
            # Guardar en buffer
            buffer = BytesIO()
            background.save(buffer, format='PNG')
            buffer.seek(0)
            
            return HttpResponse(buffer.getvalue(), content_type='image/png')
            
        except Exception as e:
            # Si hay error, devolver icono genérico
            pass
    
    # Fallback: redirigir a icono genérico
    from django.shortcuts import redirect
    return redirect(f'/static/icons/icon-{size}x{size}.png')


def gym_service_worker(request, slug):
    """
    Genera un Service Worker básico para cada gimnasio.
    Esto permite funcionalidad offline y mejor experiencia PWA.
    """
    gym = get_object_or_404(Gym, slug=slug)
    gym_name = gym.commercial_name or gym.name
    
    sw_content = f'''
// Service Worker para {gym_name}
const CACHE_NAME = 'gym-{slug}-v1';
const urlsToCache = [
    '/gym/{slug}/',
    '/gym/{slug}/schedule/',
    '/gym/{slug}/profile/',
    '/static/icons/icon-192x192.png',
];

// Instalación
self.addEventListener('install', function(event) {{
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {{
                return cache.addAll(urlsToCache);
            }})
    );
}});

// Fetch con estrategia Network First
self.addEventListener('fetch', function(event) {{
    event.respondWith(
        fetch(event.request)
            .then(function(response) {{
                // Si es exitoso, cachear y devolver
                if (response && response.status === 200) {{
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then(function(cache) {{
                        cache.put(event.request, responseClone);
                    }});
                }}
                return response;
            }})
            .catch(function() {{
                // Si falla, buscar en cache
                return caches.match(event.request);
            }})
    );
}});

// Activación - limpiar caches antiguas
self.addEventListener('activate', function(event) {{
    event.waitUntil(
        caches.keys().then(function(cacheNames) {{
            return Promise.all(
                cacheNames.filter(function(cacheName) {{
                    return cacheName.startsWith('gym-{slug}-') && cacheName !== CACHE_NAME;
                }}).map(function(cacheName) {{
                    return caches.delete(cacheName);
                }})
            );
        }})
    );
}});
'''
    
    return HttpResponse(sw_content, content_type='application/javascript')


# ===========================
# NOTIFICACIONES Y ANUNCIOS
# ===========================

def public_notifications(request, slug):
    """Vista de notificaciones: chat, anuncios y alertas"""
    gym, settings = get_gym_by_slug(slug)
    
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    # Verificar autenticación - redirigir al login del portal público
    if not request.user.is_authenticated:
        from django.urls import reverse
        login_url = reverse('public_login', kwargs={'slug': slug})
        return redirect(f'{login_url}?next={request.path}')
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Obtener anuncios activos para este gym
    from marketing.models import Advertisement
    from django.db.models import Q
    now = timezone.now()
    
    # Anuncios donde:
    # 1. gym = este gym (el que lo creó), O
    # 2. este gym está en target_gyms
    # Y además: is_active=True, start_date <= now, end_date is null o > now
    advertisements = Advertisement.objects.filter(
        Q(gym=gym) | Q(target_gyms=gym),
        is_active=True,
        start_date__lte=now
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    ).distinct().order_by('priority', '-created_at')
    
    # Obtener mensajes del chat
    from clients.models import ChatRoom, ChatMessage
    chat_room = ChatRoom.objects.filter(client=client).first()
    unread_messages = 0
    if chat_room:
        unread_messages = ChatMessage.objects.filter(
            room=chat_room,
            is_from_client=False,
            is_read=False
        ).count()
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'advertisements': advertisements,
        'unread_messages': unread_messages,
    }
    
    return render(request, 'public_portal/notifications.html', context)


def get_advertisements_for_screen(gym, screen_name='HOME'):
    """Helper para obtener anuncios filtrados por pantalla"""
    from marketing.models import Advertisement
    now = timezone.now()
    
    ads = Advertisement.objects.filter(
        gym=gym,
        is_active=True,
        start_date__lte=now
    ).exclude(
        end_date__lt=now
    ).order_by('priority', '-created_at')
    
    # Filtrar por pantalla
    filtered_ads = []
    for ad in ads:
        target_screens = ad.target_screens or []
        # Si no tiene pantallas específicas o incluye la pantalla actual o incluye 'ALL'
        if not target_screens or screen_name in target_screens or 'ALL' in target_screens:
            filtered_ads.append(ad)
    
    return filtered_ads

# ===========================
# CALENDAR SYNC (iCal)
# ===========================

@login_required
def public_calendar_sync(request, slug):
    """Página de sincronización de calendario en el portal público"""
    from clients import calendar_service
    from activities.models import ActivitySessionBooking
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        messages.error(request, 'No tienes acceso a este gimnasio')
        return redirect('public_gym_home', slug=slug)
    
    token = calendar_service.get_or_create_calendar_token(client)
    feed_url = calendar_service.get_calendar_feed_url(client, request)
    
    # Obtener próximas reservas
    upcoming_bookings = ActivitySessionBooking.objects.filter(
        client=client,
        status='CONFIRMED',
        session__start_datetime__gte=timezone.now()
    ).select_related(
        'session',
        'session__activity',
        'session__room'
    ).order_by('session__start_datetime')[:10]
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'feed_url': feed_url,
        'upcoming_bookings': upcoming_bookings,
    }
    
    return render(request, 'public_portal/calendar_sync.html', context)


@login_required
def public_calendar_settings(request, slug):
    """API para obtener configuración de calendario"""
    from clients import calendar_service
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return JsonResponse({'error': 'Gym not found'}, status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Not a client'}, status=403)
    
    token = calendar_service.get_or_create_calendar_token(client)
    feed_url = calendar_service.get_calendar_feed_url(client, request)
    
    return JsonResponse({
        'feed_url': feed_url,
        'has_token': bool(token),
    })


@login_required
def public_calendar_regenerate(request, slug):
    """API para regenerar token de calendario"""
    from clients import calendar_service
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return JsonResponse({'error': 'Gym not found'}, status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Not a client'}, status=403)
    
    new_token = calendar_service.regenerate_calendar_token(client)
    new_url = calendar_service.get_calendar_feed_url(client, request)
    
    return JsonResponse({
        'success': True,
        'feed_url': new_url,
        'message': 'Token regenerado correctamente'
    })


@login_required
def public_download_booking_ics(request, slug, booking_id):
    """Descarga archivo .ics para una reserva específica"""
    from clients import calendar_service
    from activities.models import ActivitySessionBooking
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Not a client'}, status=403)
    
    booking = get_object_or_404(
        ActivitySessionBooking,
        id=booking_id,
        client=client,
        status='CONFIRMED'
    )
    
    # Generar el archivo .ics
    ics_content = calendar_service.generate_booking_ics(booking)
    
    # Nombre del archivo
    activity_name = booking.session.activity.name.replace(' ', '_')
    date_str = booking.session.start_datetime.strftime('%Y%m%d')
    filename = f"reserva_{activity_name}_{date_str}.ics"
    
    response = HttpResponse(ics_content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


# ===========================
# PROGRAMA DE REFERIDOS
# ===========================

@login_required
def public_referrals(request, slug):
    """Página del programa de referidos para el cliente"""
    from discounts.referral_service import (
        is_referral_enabled,
        get_active_referral_program,
        get_share_data,
        get_referral_stats,
        get_referral_history
    )
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Verificar si está habilitado
    if not is_referral_enabled(gym):
        messages.info(request, 'El programa de referidos no está disponible actualmente')
        return redirect('public_client_dashboard', slug=slug)
    
    # Obtener datos
    program = get_active_referral_program(gym)
    share_data = get_share_data(client, request)
    stats = get_referral_stats(client)
    history = get_referral_history(client, limit=20)
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'program': program,
        'share_data': share_data,
        'stats': stats,
        'history': history,
    }
    
    return render(request, 'public_portal/referrals.html', context)


@login_required
def api_referral_share_data(request, slug):
    """API para obtener datos de compartir referido (AJAX)"""
    from discounts.referral_service import is_referral_enabled, get_share_data
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return JsonResponse({'error': 'Gym not found'}, status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Not a client'}, status=403)
    
    if not is_referral_enabled(gym):
        return JsonResponse({'error': 'Referral program not enabled'}, status=400)
    
    share_data = get_share_data(client, request)
    
    return JsonResponse(share_data)


# ===========================
# MONEDERO / WALLET
# ===========================

@login_required
def public_wallet(request, slug):
    """Página del monedero del cliente"""
    from finance.wallet_service import WalletService
    from finance.models import ClientWallet, WalletTransaction, WalletSettings
    
    gym, settings = get_gym_by_slug(slug)
    if not gym:
        return render(request, 'public_portal/404.html', status=404)
    
    try:
        client = Client.objects.get(user=request.user, gym=gym)
    except Client.DoesNotExist:
        return redirect('public_login', slug=slug)
    
    # Verificar si está habilitado
    wallet_settings = WalletService.get_wallet_settings(gym)
    if not wallet_settings.wallet_enabled or not wallet_settings.show_in_client_portal:
        messages.info(request, 'El monedero no está disponible actualmente')
        return redirect('public_client_dashboard', slug=slug)
    
    # Obtener o crear monedero
    wallet, _ = WalletService.get_or_create_wallet(client, gym)
    
    # Historial de transacciones
    transactions = wallet.transactions.order_by('-created_at')[:30]
    
    # Resumen
    summary = WalletService.get_summary(wallet)
    
    context = {
        'gym': gym,
        'settings': settings,
        'client': client,
        'wallet': wallet,
        'wallet_settings': wallet_settings,
        'transactions': transactions,
        'summary': summary,
    }
    
    return render(request, 'public_portal/wallet.html', context)
