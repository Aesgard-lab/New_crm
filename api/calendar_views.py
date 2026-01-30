"""
API endpoints para sincronización de calendario en la app móvil.

Endpoints:
- GET /api/calendar/settings/ - Obtener URL del feed de calendario
- POST /api/calendar/regenerate-token/ - Regenerar token del calendario
- GET /api/calendar/booking/<id>/ics/ - Descargar .ics de una reserva
"""

from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from clients.models import Client
from clients import calendar_service
from activities.models import ActivitySessionBooking


class CalendarSettingsView(views.APIView):
    """
    GET: Obtener la URL del feed de calendario del cliente.
    
    Response:
    {
        "feed_url": "https://domain.com/calendar/feed/TOKEN.ics",
        "has_token": true,
        "instructions": {
            "google": "...",
            "apple": "...",
            "outlook": "..."
        }
    }
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
        
        token = calendar_service.get_or_create_calendar_token(client)
        feed_url = calendar_service.get_calendar_feed_url(client, request)
        
        return Response({
            'feed_url': feed_url,
            'has_token': bool(token),
            'instructions': {
                'google': 'Abre Google Calendar > + junto a "Otros calendarios" > Desde URL > Pega la URL',
                'apple': 'Ajustes > Calendario > Cuentas > Añadir cuenta > Otra > Añadir suscripción de calendario',
                'outlook': 'Outlook Calendar > Añadir calendario > Suscribirse desde la web > Pega la URL'
            }
        })


class RegenerateCalendarTokenView(views.APIView):
    """
    POST: Regenerar el token del calendario.
    Esto invalidará todas las URLs de suscripción anteriores.
    
    Response:
    {
        "success": true,
        "feed_url": "https://domain.com/calendar/feed/NEW_TOKEN.ics",
        "message": "Token regenerado correctamente"
    }
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
        
        new_token = calendar_service.regenerate_calendar_token(client)
        new_url = calendar_service.get_calendar_feed_url(client, request)
        
        return Response({
            'success': True,
            'feed_url': new_url,
            'message': 'Token regenerado correctamente. Las URLs anteriores ya no funcionarán.'
        })


class DownloadBookingICSView(views.APIView):
    """
    GET: Descargar archivo .ics para una reserva específica.
    
    Path params:
    - booking_id: ID de la reserva
    
    Response: archivo .ics (text/calendar)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, booking_id):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
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


class AddToCalendarView(views.APIView):
    """
    POST: Endpoint para que la app Flutter pueda añadir un evento
    al calendario nativo del dispositivo.
    
    Retorna los datos del evento en formato estructurado para que
    la app lo añada usando el plugin device_calendar.
    
    Request body:
    {
        "booking_id": 123
    }
    
    Response:
    {
        "title": "Yoga",
        "description": "Clase de Yoga en GymName...",
        "start": "2024-01-15T10:00:00+01:00",
        "end": "2024-01-15T11:00:00+01:00",
        "location": "Sala 1, Calle Principal 123",
        "reminder_minutes": [30, 120]
    }
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
        
        booking_id = request.data.get('booking_id')
        if not booking_id:
            return Response(
                {'error': 'booking_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking = get_object_or_404(
            ActivitySessionBooking,
            id=booking_id,
            client=client,
            status='CONFIRMED'
        )
        
        session = booking.session
        activity = session.activity
        gym = session.gym
        
        # Construir descripción
        description_parts = [f"📍 {gym.commercial_name or gym.name}"]
        if session.staff:
            description_parts.append(f"👤 Instructor: {session.staff.user.get_full_name()}")
        if session.room:
            description_parts.append(f"🚪 Sala: {session.room.name}")
        if booking.spot_number:
            description_parts.append(f"🎯 Tu puesto: #{booking.spot_number}")
        description_parts.append(f"\n📱 Reserva #{booking.id}")
        
        # Construir ubicación
        location_parts = []
        if session.room:
            location_parts.append(f"Sala: {session.room.name}")
        if gym.address:
            location_parts.append(gym.address)
        if gym.city:
            location_parts.append(gym.city)
        
        return Response({
            'title': activity.name,
            'description': "\n".join(description_parts),
            'start': session.start_datetime.isoformat(),
            'end': session.end_datetime.isoformat(),
            'location': ", ".join(location_parts) if location_parts else gym.commercial_name or gym.name,
            'reminder_minutes': [30, 120],  # 30 minutos y 2 horas antes
            'gym_name': gym.commercial_name or gym.name,
            'activity_name': activity.name,
            'booking_id': booking.id
        })
