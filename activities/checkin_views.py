"""
Vistas para el sistema de Check-in por QR de clases.

SECURITY FEATURES:
- HMAC-based tokens with SECRET_KEY
- Time-limited tokens (configurable expiry)
- Rate limiting on check-in endpoint
- Timing-safe token comparison
"""
import hashlib
import hmac
import time
import json
import logging
from datetime import timedelta

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django_ratelimit.decorators import ratelimit

from core.ratelimit import get_client_ip

from organizations.models import Gym
from clients.models import Client
from .models import ActivitySession, AttendanceSettings, SessionCheckin

# Security logger
security_logger = logging.getLogger('django.security')


def get_secret_key():
    """Obtiene la clave secreta para generar tokens QR"""
    if not hasattr(settings, 'SECRET_KEY') or not settings.SECRET_KEY:
        raise ValueError("Django SECRET_KEY is not configured!")
    return settings.SECRET_KEY


def generate_qr_token(session_id: int, timestamp: int) -> str:
    """
    Genera un token HMAC para el QR de una sesión.
    El token cambia cada N segundos según la configuración.
    """
    message = f"{session_id}:{timestamp}"
    signature = hmac.new(
        get_secret_key().encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()[:32]
    return f"{session_id}:{timestamp}:{signature}"


def verify_qr_token(token: str, session_id: int, max_age_seconds: int = 60) -> bool:
    """
    Verifica que un token QR sea válido y no haya expirado.
    """
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return False
        
        token_session_id, token_timestamp, token_signature = parts
        
        if int(token_session_id) != session_id:
            return False
        
        # Verificar que no haya expirado
        token_time = int(token_timestamp)
        current_time = int(time.time())
        if current_time - token_time > max_age_seconds:
            return False
        
        # Verificar firma
        expected_token = generate_qr_token(session_id, token_time)
        return hmac.compare_digest(token, expected_token)
        
    except (ValueError, TypeError):
        return False


def get_current_qr_data(session: ActivitySession, gym: Gym) -> dict:
    """
    Genera los datos actuales del QR para una sesión.
    """
    try:
        att_settings = gym.attendance_settings
        refresh_seconds = att_settings.qr_refresh_seconds
    except AttendanceSettings.DoesNotExist:
        refresh_seconds = 30
    
    # Redondear timestamp al intervalo de refresh
    current_time = int(time.time())
    rounded_time = (current_time // refresh_seconds) * refresh_seconds
    
    token = generate_qr_token(session.id, rounded_time)
    
    # URL para check-in (el cliente escanea esto)
    checkin_url = f"/activities/checkin/qr/{token}/"
    
    return {
        'token': token,
        'url': checkin_url,
        'refresh_in': refresh_seconds - (current_time - rounded_time),
        'session_id': session.id,
        'session_name': session.activity.name,
        'start_time': session.start_datetime.strftime('%H:%M'),
    }


@login_required
def session_qr_display(request, session_id):
    """
    Vista para proyectar el QR de una clase en una tablet/pantalla.
    Diseñada para modo kiosko/pantalla completa.
    """
    gym = request.gym
    session = get_object_or_404(
        ActivitySession.objects.select_related('activity', 'room', 'staff'),
        id=session_id,
        gym=gym
    )
    
    # Verificar que QR está habilitado para esta actividad
    if not session.activity.qr_checkin_enabled:
        try:
            if gym.attendance_settings.checkin_mode == 'STAFF_ONLY':
                return render(request, 'activities/checkin/qr_disabled.html', {
                    'session': session,
                    'message': 'El check-in por QR no está habilitado para esta clase.'
                })
        except AttendanceSettings.DoesNotExist:
            pass
    
    qr_data = get_current_qr_data(session, gym)
    
    context = {
        'session': session,
        'qr_data': qr_data,
        'gym': gym,
    }
    
    return render(request, 'activities/checkin/qr_display.html', context)


@login_required
def qr_display_api(request, session_id):
    """
    API para obtener datos actualizados del QR (llamado por JS cada N segundos).
    """
    gym = request.gym
    session = get_object_or_404(ActivitySession, id=session_id, gym=gym)
    
    qr_data = get_current_qr_data(session, gym)
    
    # Agregar info de asistentes
    qr_data['attendee_count'] = session.attendees.count()
    qr_data['max_capacity'] = session.max_capacity
    qr_data['checkins'] = SessionCheckin.objects.filter(session=session).count()
    
    return JsonResponse(qr_data)


@csrf_exempt
@ratelimit(key='ip', rate='20/m', method=['POST', 'GET'], block=True)
@require_http_methods(["POST", "GET"])
def qr_checkin(request, token):
    """
    Endpoint para procesar el check-in por QR.
    El cliente escanea el QR y llega aquí.
    
    SECURITY:
    - Rate limited to prevent brute force (20/min per IP)
    - HMAC token verification with timing-safe comparison
    - Token expiration validation
    """
    # Get client IP for logging
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', 'unknown')
    
    try:
        parts = token.split(':')
        if len(parts) != 3:
            security_logger.warning(f"Invalid QR token format from IP: {client_ip}")
            return JsonResponse({
                'success': False,
                'error': 'QR inválido'
            }, status=400)
        
        session_id = int(parts[0])
        session = get_object_or_404(
            ActivitySession.objects.select_related('activity', 'gym'),
            id=session_id
        )
        gym = session.gym
        
        # Obtener configuración
        try:
            att_settings = gym.attendance_settings
            max_age = att_settings.qr_refresh_seconds * 2  # Permitir 2x el tiempo de refresh
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
                'error': 'QR expirado. Por favor escanea de nuevo.'
            }, status=400)
        
        # Verificar ventana de tiempo
        now = timezone.now()
        window_start = session.start_datetime - timedelta(minutes=minutes_before)
        window_end = session.start_datetime + timedelta(minutes=minutes_after)
        
        if now < window_start:
            return JsonResponse({
                'success': False,
                'error': f'Demasiado pronto. El check-in abre {minutes_before} minutos antes de la clase.'
            }, status=400)
        
        if now > window_end:
            return JsonResponse({
                'success': False,
                'error': 'La ventana de check-in ha cerrado.'
            }, status=400)
        
        # Identificar al cliente
        client = None
        
        # Si hay usuario autenticado con perfil de cliente
        if request.user.is_authenticated:
            try:
                client = request.user.client_profile
            except:
                pass
        
        # Si viene por POST con client_id (desde app)
        if not client and request.method == 'POST':
            try:
                data = json.loads(request.body)
                client_id = data.get('client_id')
                if client_id:
                    client = Client.objects.get(id=client_id, gym=gym)
            except:
                pass
        
        if not client:
            # Mostrar página de login/identificación
            return render(request, 'activities/checkin/identify.html', {
                'session': session,
                'token': token,
            })
        
        # Verificar que el cliente está en la lista de reservados
        if client not in session.attendees.all():
            return JsonResponse({
                'success': False,
                'error': 'No tienes reserva para esta clase. Contacta con recepción.'
            }, status=400)
        
        # Verificar si ya hizo check-in
        existing = SessionCheckin.objects.filter(session=session, client=client).first()
        if existing:
            return JsonResponse({
                'success': True,
                'already_checked_in': True,
                'message': f'Ya hiciste check-in a las {existing.checked_in_at.strftime("%H:%M")}',
                'session_name': session.activity.name,
            })
        
        # Crear check-in
        checkin = SessionCheckin.objects.create(
            session=session,
            client=client,
            method='QR',
            qr_token=token,
            ip_address=get_client_ip(request)
        )
        
        return JsonResponse({
            'success': True,
            'message': success_message,
            'session_name': session.activity.name,
            'checked_in_at': checkin.checked_in_at.strftime('%H:%M'),
            'client_name': client.first_name,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def attendance_settings_view(request):
    """
    Vista para configurar las opciones de asistencia/check-in del gimnasio.
    """
    gym = request.gym
    
    # Obtener o crear configuración
    settings_obj, created = AttendanceSettings.objects.get_or_create(
        gym=gym,
        defaults={
            'checkin_mode': 'STAFF_ONLY',
        }
    )
    
    if request.method == 'POST':
        settings_obj.checkin_mode = request.POST.get('checkin_mode', 'STAFF_ONLY')
        settings_obj.qr_checkin_minutes_before = int(request.POST.get('qr_checkin_minutes_before', 15))
        settings_obj.qr_checkin_minutes_after = int(request.POST.get('qr_checkin_minutes_after', 30))
        settings_obj.qr_refresh_seconds = int(request.POST.get('qr_refresh_seconds', 30))
        settings_obj.checkin_success_message = request.POST.get('checkin_success_message', '✅ ¡Check-in completado!')
        settings_obj.save()
        
        from django.contrib import messages
        messages.success(request, 'Configuración de asistencias guardada correctamente.')
    
    context = {
        'settings': settings_obj,
        'checkin_modes': AttendanceSettings.CHECKIN_MODE_CHOICES,
    }
    
    return render(request, 'activities/checkin/settings.html', context)


@login_required
def today_sessions_qr_list(request):
    """
    Lista de sesiones del día con enlaces a sus QRs para proyectar.
    Útil para que el staff seleccione qué clase proyectar.
    """
    gym = request.gym
    today = timezone.now().date()
    
    sessions = ActivitySession.objects.filter(
        gym=gym,
        start_datetime__date=today,
        status='SCHEDULED'
    ).select_related('activity', 'room', 'staff').order_by('start_datetime')
    
    context = {
        'sessions': sessions,
        'today': today,
    }
    
    return render(request, 'activities/checkin/sessions_list.html', context)
