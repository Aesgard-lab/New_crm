from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from organizations.models import Gym
from accounts.services import user_gym_ids
from accounts.decorators import require_staff
from core.mixins import require_gym


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def login_view(request):
    """
    Vista de login con rate limiting (5 intentos por minuto por IP)
    """
    print(f"[DEBUG BACKOFFICE LOGIN] Request method: {request.method}")
    print(f"[DEBUG BACKOFFICE LOGIN] Request path: {request.path}")
    
    if request.user.is_authenticated:
        # Redirigir según el tipo de usuario
        if hasattr(request.user, 'client_profile'):
            return redirect('portal_home')
        return redirect("home")

    error = None
    
    # Verificar si está bloqueado por rate limit
    was_limited = getattr(request, 'limited', False)
    if was_limited:
        error = "Demasiados intentos de inicio de sesión. Por favor, espera un minuto."
    
    if request.method == "POST" and not was_limited:
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        # DEBUG: Log de intento de login
        print(f"[DEBUG BACKOFFICE LOGIN] Email recibido: '{email}'")
        print(f"[DEBUG BACKOFFICE LOGIN] Password length: {len(password)}")
        print(f"[DEBUG BACKOFFICE LOGIN] Llamando authenticate()...")
        
        user = authenticate(request, username=email, password=password)
        print(f"[DEBUG BACKOFFICE LOGIN] Resultado authenticate(): {user}")
        
        if user is not None:
            login(request, user)
            # Log exitoso en auditoría
            try:
                from staff.models import AuditLog
                from core.ratelimit import get_client_ip
                gym_id = request.session.get("current_gym_id")
                gym = Gym.objects.get(pk=gym_id) if gym_id else None
                if gym:
                    AuditLog.objects.create(
                        gym=gym,
                        user=user,
                        action='LOGIN',
                        module='Auth',
                        target=email,
                        ip_address=get_client_ip(request),
                    )
            except Exception:
                pass
            
            # Redirigir según el tipo de usuario
            if hasattr(user, 'client_profile'):
                # Es un cliente, redirigir al portal
                return redirect('portal_home')
            elif user.is_staff or user.is_superuser:
                # Es staff o admin, redirigir al backoffice
                return redirect("home")
            else:
                # Usuario sin permisos específicos
                logout(request)
                error = "No tienes permisos para acceder al sistema"
                
        else:
            error = "Credenciales incorrectas"

    return render(request, "auth/login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


@require_staff
def home(request):
    # Redirect Franchise Owners to their dashboard if no gym is selected or explicitly preferred
    if not request.session.get("current_gym_id") and request.user.franchises_owned.exists():
        return redirect('franchise-dashboard')

    gym_id = request.session.get("current_gym_id")
    gym = Gym.objects.filter(id=gym_id).first()
    
    # Dashboard Stats
    from .dashboard_service import DashboardService
    from organizations.models import GymGoal
    from datetime import date
    
    dashboard = DashboardService(gym)
    stats = dashboard.get_kpi_stats()
    risk_clients = dashboard.get_risk_clients()
    risk_clients_enhanced = dashboard.get_risk_clients_enhanced()
    top_clients = dashboard.get_top_clients()
    chart_data = dashboard.get_revenue_chart_data(days=30)
    membership_stats = dashboard.get_membership_stats()
    revenue_forecast = dashboard.get_revenue_forecast(months_ahead=3)
    
    # Staff online count
    from staff.models import WorkShift
    staff_online_count = WorkShift.objects.filter(
        staff__gym=gym,
        end_time__isnull=True
    ).count() if gym else 0
    
    # Obtener objetivos activos del gimnasio
    today = date.today()
    current_goals = GymGoal.objects.filter(
        gym=gym,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    )
    
    # Calcular progreso de objetivos
    goals_with_progress = []
    for goal in current_goals:
        goal_data = {
            'goal': goal,
            'progress_members': None,
            'progress_revenue': None,
        }
        
        if goal.target_members:
            goal_data['progress_members'] = goal.get_progress_members(stats.get('active_members', 0))
        
        if goal.target_revenue:
            goal_data['progress_revenue'] = goal.get_progress_revenue(stats.get('revenue_current', 0))
        
        goals_with_progress.append(goal_data)
    
    # Análisis de break-even
    breakeven_data = dashboard.get_breakeven_analysis()
    
    context = {
        "gym": gym,
        "stats": stats,
        "risk_clients": risk_clients,
        "risk_clients_enhanced": risk_clients_enhanced,
        "top_clients": top_clients,
        "chart_data": chart_data,
        "membership_stats": membership_stats,
        "forecast": revenue_forecast,
        "goals": goals_with_progress,
        "staff_online_count": staff_online_count,
        "breakeven": breakeven_data,
    }
    return render(request, "backoffice/dashboard.html", context)


@login_required
def whoami(request):
    gym_id = request.session.get("current_gym_id")
    gym = Gym.objects.filter(id=gym_id).first()
    return JsonResponse({
        "user": request.user.email,
        "current_gym_id": gym_id,
        "current_gym_name": gym.name if gym else None,
    })


@login_required
@require_POST
def select_gym(request):
    gym_id = request.POST.get("gym_id")
    try:
        gym_id_int = int(gym_id)
    except (TypeError, ValueError):
        return redirect("home")

    allowed_ids = set(user_gym_ids(request.user))
    if gym_id_int in allowed_ids:
        request.session["current_gym_id"] = gym_id_int

    return redirect("home")


from accounts.decorators import require_gym_permission

# clients_list movido a clients/views.py


@login_required
@require_gym_permission("staff.view")
def staff_page(request):
    return render(request, "backoffice/staff/list.html")


@login_required
@require_gym_permission("marketing.view")
def marketing_page(request):
    return render(request, "backoffice/marketing/list.html")


@login_required
@require_gym
def settings_dashboard(request):
    """
    Centralized Settings Hub.
    """
    gym = request.gym
    
    context = {
        "title": "Configuración",
        "gym": gym,
    }
    return render(request, "backoffice/settings/dashboard.html", context)


@login_required
@require_gym
def system_settings_dashboard(request):
    """
    System Settings - Logs, Hardware, Integrations.
    """
    return render(request, "backoffice/settings/system/dashboard.html", {
        "title": "Sistema",
    })


@login_required
def chat_list(request):
    """Lista de chats con clientes"""
    from clients.models import ChatRoom
    from django.db.models import Q, Count
    
    gym_id = request.session.get("current_gym_id")
    
    # Obtener todas las salas de chat del gimnasio
    chat_rooms = ChatRoom.objects.filter(
        gym_id=gym_id
    ).select_related('client__user').prefetch_related('messages').annotate(
        unread_count=Count('messages', filter=Q(messages__is_read=False, messages__sender__client_profile__isnull=False))
    ).order_by('-last_message_at', '-created_at')
    
    context = {
        "title": "Chat con Clientes",
        "chat_rooms": chat_rooms,
    }
    return render(request, "backoffice/chat/list.html", context)


@login_required
def chat_detail(request, room_id):
    """Vista de chat con un cliente específico"""
    from clients.models import ChatRoom, ChatMessage
    
    gym_id = request.session.get("current_gym_id")
    
    chat_room = ChatRoom.objects.select_related('client__user').get(
        id=room_id,
        gym_id=gym_id
    )
    
    # Obtener mensajes
    messages = chat_room.messages.select_related('sender').order_by('created_at')
    
    # Marcar mensajes del cliente como leídos
    chat_room.messages.filter(is_read=False, sender__client_profile__isnull=False).update(is_read=True)
    
    context = {
        "title": f"Chat con {chat_room.client.first_name} {chat_room.client.last_name}",
        "chat_room": chat_room,
        "messages": messages,
    }
    return render(request, "backoffice/chat/detail.html", context)


@login_required
def chat_start_with_client(request, client_id):
    """Iniciar o abrir chat existente con un cliente"""
    from clients.models import Client, ChatRoom
    from django.utils import timezone
    
    gym_id = request.session.get("current_gym_id")
    if not gym_id:
        return redirect('home')
    
    # Verificar que el cliente existe y tiene acceso al portal
    try:
        client = Client.objects.get(id=client_id, gym_id=gym_id, user__isnull=False)
    except Client.DoesNotExist:
        return redirect('chat_list')
    
    # Obtener o crear la sala de chat
    chat_room, created = ChatRoom.objects.get_or_create(
        client=client,
        gym_id=gym_id,
        defaults={'last_message_at': timezone.now()}
    )
    
    # Redirigir al chat
    return redirect('chat_detail', room_id=chat_room.id)


@login_required
@require_POST
def chat_send_message(request, room_id):
    """Enviar mensaje desde el backoffice (AJAX)"""
    from clients.models import ChatRoom, ChatMessage
    from django.utils import timezone
    import json
    
    gym_id = request.session.get("current_gym_id")
    
    try:
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return JsonResponse({'error': 'Mensaje vacío'}, status=400)
        
        chat_room = ChatRoom.objects.get(id=room_id, gym_id=gym_id)
        
        # Crear mensaje
        message = ChatMessage.objects.create(
            room=chat_room,
            sender=request.user,
            message=message_text
        )
        
        # Actualizar timestamp de la sala
        chat_room.last_message_at = timezone.now()
        chat_room.save(update_fields=['last_message_at'])
        
        # Construir nombre del sender
        sender_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'text': message.message,
                'created_at': message.created_at.strftime('%H:%M'),
                'is_from_client': False,
                'sender_name': sender_name
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def chat_poll_messages(request, room_id):
    """Obtener nuevos mensajes (AJAX polling)"""
    from clients.models import ChatRoom
    
    gym_id = request.session.get("current_gym_id")
    
    try:
        chat_room = ChatRoom.objects.get(id=room_id, gym_id=gym_id)
        
        last_message_id = request.GET.get('last_message_id', 0)
        
        # Obtener mensajes nuevos
        new_messages = chat_room.messages.filter(
            id__gt=last_message_id
        ).select_related('sender')
        
        # Marcar como leídos los del cliente
        new_messages.filter(is_read=False, sender__client_profile__isnull=False).update(is_read=True)
        
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
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def chat_search_clients(request):
    """Buscar clientes para iniciar chat (AJAX)"""
    from clients.models import Client
    from django.db.models import Q
    
    gym_id = request.session.get("current_gym_id")
    if not gym_id:
        return JsonResponse({'error': 'No hay gimnasio seleccionado'}, status=400)
    
    search_term = request.GET.get('q', '').strip()
    
    # Buscar clientes con portal access
    clients = Client.objects.filter(
        gym_id=gym_id,
        user__isnull=False  # Solo clientes con acceso al portal
    )
    
    if search_term:
        clients = clients.filter(
            Q(first_name__icontains=search_term) |
            Q(last_name__icontains=search_term) |
            Q(email__icontains=search_term) |
            Q(phone_number__icontains=search_term)
        )
    
    clients = clients[:20]  # Limitar a 20 resultados
    
    results = [{
        'id': client.id,
        'name': f"{client.first_name} {client.last_name}".strip(),
        'email': client.email or '',
        'phone': client.phone_number or '',
        'photo_url': client.photo.url if client.photo else None
    } for client in clients]
    
    return JsonResponse({'clients': results})

