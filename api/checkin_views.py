"""
API Views for Client Check-in QR (Mobile App).
Generates dynamic QR tokens for gym access.

SECURITY:
- Uses HMAC with SECRET_KEY for token generation (not just SHA256)
- Tokens expire every 30 seconds
- Longer token length (16 chars = 64 bits) for better security
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import hashlib
import hmac
import time

from clients.models import Client, ClientVisit
from activities.models import ActivitySession, SessionCheckin, AttendanceSettings


def _generate_secure_qr_token(client_id: int, access_code: str, timestamp: int) -> str:
    """
    Generate a secure HMAC-based QR token.
    
    SECURITY:
    - Uses HMAC-SHA256 with SECRET_KEY
    - 16 character output (64 bits of entropy)
    - Includes client ID, access code, and timestamp
    """
    secret_key = getattr(settings, 'SECRET_KEY', 'fallback-key')
    message = f"{client_id}-{access_code}-{timestamp}"
    
    token = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()[:16].upper()
    
    return token


class GenerateQRTokenView(views.APIView):
    """
    Generate a QR token for check-in.
    The token refreshes every 30 seconds for security.
    
    GET or POST /api/checkin/generate/
    """
    permission_classes = [IsAuthenticated]
    
    def _generate_qr_response(self, request):
        """Shared logic for GET and POST"""
        # Get client
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if client has active membership
        active_membership = client.memberships.filter(status='ACTIVE').first()
        
        # Generate QR token (refreshes every 30 seconds)
        timestamp = int(time.time() / 30)
        qr_token = _generate_secure_qr_token(client.id, client.access_code, timestamp)
        
        # Calculate time until token expires
        current_time = time.time()
        next_refresh = (timestamp + 1) * 30
        expires_in = int(next_refresh - current_time)
        
        # Build membership info
        membership_info = None
        if active_membership:
            plan = active_membership.plan
            membership_info = {
                'name': plan.name if plan else 'Membresía Activa',
                'status': active_membership.status,
                'end_date': active_membership.end_date.isoformat() if active_membership.end_date else None,
                'is_unlimited': plan.duration_type == 'UNLIMITED' if plan else False,
                'sessions_remaining': active_membership.sessions_remaining if hasattr(active_membership, 'sessions_remaining') else None,
                'sessions_total': plan.sessions_included if plan and hasattr(plan, 'sessions_included') else None,
            }
        
        return Response({
            'token': qr_token,
            'expires_in': expires_in,
            'membership': membership_info
        })
    
    def get(self, request):
        """GET method for browser compatibility"""
        return self._generate_qr_response(request)
    
    def post(self, request):
        """POST method (preferred)"""
        return self._generate_qr_response(request)


class RefreshQRTokenView(views.APIView):
    """
    Refresh the QR token.
    Called by the mobile app every 30 seconds.
    
    POST /api/checkin/refresh/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate new secure token
        timestamp = int(time.time() / 30)
        qr_token = _generate_secure_qr_token(client.id, client.access_code, timestamp)
        
        # Calculate time until token expires
        current_time = time.time()
        next_refresh = (timestamp + 1) * 30
        expires_in = int(next_refresh - current_time)
        
        return Response({
            'token': qr_token,
            'expires_in': expires_in,
            'timestamp': timestamp,
        })


class CheckinHistoryView(views.APIView):
    """
    Get client's check-in history.
    
    GET /api/checkin/history/
    Query params:
    - limit: Number of records (default 10)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        limit = int(request.query_params.get('limit', 10))
        
        visits = ClientVisit.objects.filter(
            client=client,
            status='ATTENDED'
        ).order_by('-date', '-check_in_time')[:limit]
        
        visits_data = []
        for visit in visits:
            visits_data.append({
                'id': visit.id,
                'date': visit.date.isoformat(),
                'check_in_time': visit.check_in_time.strftime('%H:%M') if visit.check_in_time else None,
                'check_out_time': visit.check_out_time.strftime('%H:%M') if visit.check_out_time else None,
                'activity': visit.activity.name if hasattr(visit, 'activity') and visit.activity else None,
            })
        
        return Response({
            'count': len(visits_data),
            'visits': visits_data,
        })


class TodaysSessionsView(views.APIView):
    """
    GET: Obtener las clases reservadas de hoy para check-in rápido.
    Incluye info sobre si ya se hizo check-in.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            client = Client.objects.select_related('gym').get(user=request.user)
        except Client.DoesNotExist:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        today = timezone.now().date()
        now = timezone.now()
        
        # Sesiones de hoy donde el cliente está inscrito
        sessions = ActivitySession.objects.filter(
            gym=client.gym,
            attendees=client,
            start_datetime__date=today,
            status='SCHEDULED'
        ).select_related('activity', 'room').order_by('start_datetime')
        
        # Obtener configuración de check-in
        try:
            att_settings = client.gym.attendance_settings
            minutes_before = att_settings.qr_checkin_minutes_before
            minutes_after = att_settings.qr_checkin_minutes_after
        except AttendanceSettings.DoesNotExist:
            minutes_before = 30
            minutes_after = 30
        
        sessions_data = []
        for session in sessions:
            # Verificar si ya hizo check-in
            checked_in = SessionCheckin.objects.filter(
                session=session,
                client=client
            ).first()
            
            # Calcular ventana de check-in
            window_start = session.start_datetime - timedelta(minutes=minutes_before)
            window_end = session.start_datetime + timedelta(minutes=minutes_after)
            
            can_checkin = window_start <= now <= window_end
            
            sessions_data.append({
                'session_id': session.id,
                'activity_name': session.activity.name,
                'activity_color': session.activity.color or '#6366F1',
                'start_time': session.start_datetime.strftime('%H:%M'),
                'end_time': (session.start_datetime + timedelta(minutes=session.duration)).strftime('%H:%M'),
                'duration': session.duration,
                'room': session.room.name if session.room else None,
                'checked_in': checked_in is not None,
                'checked_in_at': checked_in.checked_in_at.strftime('%H:%M') if checked_in else None,
                'can_checkin': can_checkin and not checked_in,
                'checkin_window': {
                    'start': window_start.strftime('%H:%M'),
                    'end': window_end.strftime('%H:%M'),
                },
            })
        
        return Response({
            'date': today.isoformat(),
            'sessions': sessions_data,
        })


class QuickCheckinView(views.APIView):
    """
    POST: Check-in rápido a una clase reservada.
    Solo requiere el session_id, no necesita escanear QR.
    
    Body: {
        "session_id": 123
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            client = Client.objects.select_related('gym').get(user=request.user)
        except Client.DoesNotExist:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({'error': 'session_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            session = ActivitySession.objects.select_related('activity', 'gym').get(id=session_id)
        except ActivitySession.DoesNotExist:
            return Response({'error': 'Clase no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar que pertenece al mismo gimnasio
        if session.gym != client.gym:
            return Response(
                {'error': 'Esta clase no es de tu gimnasio'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que tiene reserva
        if client not in session.attendees.all():
            return Response(
                {'error': 'No tienes reserva para esta clase'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar ventana de tiempo
        try:
            att_settings = client.gym.attendance_settings
            minutes_before = att_settings.qr_checkin_minutes_before
            minutes_after = att_settings.qr_checkin_minutes_after
        except AttendanceSettings.DoesNotExist:
            minutes_before = 30
            minutes_after = 30
        
        now = timezone.now()
        window_start = session.start_datetime - timedelta(minutes=minutes_before)
        window_end = session.start_datetime + timedelta(minutes=minutes_after)
        
        if now < window_start:
            mins_to_wait = int((window_start - now).total_seconds() / 60)
            return Response({
                'success': False,
                'error': f'Demasiado pronto. El check-in abre en {mins_to_wait} min.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if now > window_end:
            return Response({
                'success': False,
                'error': 'La ventana de check-in ha cerrado.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar si ya hizo check-in
        existing = SessionCheckin.objects.filter(session=session, client=client).first()
        if existing:
            return Response({
                'success': True,
                'already_checked_in': True,
                'message': f'Ya hiciste check-in a las {existing.checked_in_at.strftime("%H:%M")}',
                'session_name': session.activity.name,
            })
        
        # Crear check-in
        checkin = SessionCheckin.objects.create(
            session=session,
            client=client,
            method='APP',
        )
        
        return Response({
            'success': True,
            'message': '¡Check-in completado!',
            'session_name': session.activity.name,
            'session_time': session.start_datetime.strftime('%H:%M'),
            'checked_in_at': checkin.checked_in_at.strftime('%H:%M'),
        })

