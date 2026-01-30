"""
Servicio de Calendario iCal para sincronización con calendarios externos.

Funcionalidades:
1. Generar archivo .ics para una reserva individual
2. Generar feed iCal (URL de suscripción) con todas las reservas del cliente
"""

import hashlib
import secrets
from datetime import timedelta
from icalendar import Calendar, Event, vText
from django.utils import timezone
from django.conf import settings


def generate_booking_ics(booking):
    """
    Genera un archivo iCal (.ics) para una reserva específica.
    
    Args:
        booking: ActivitySessionBooking instance
    
    Returns:
        bytes: Contenido del archivo .ics
    """
    cal = Calendar()
    
    # Propiedades del calendario
    cal.add('prodid', '-//GymCRM//Booking Calendar//ES')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', 'Mi Reserva')
    
    event = _create_event_from_booking(booking)
    cal.add_component(event)
    
    return cal.to_ical()


def generate_client_calendar_feed(client, token):
    """
    Genera un feed iCal completo con todas las reservas futuras del cliente.
    Este feed se actualiza automáticamente cuando el cliente de calendario
    lo refresca (normalmente cada pocas horas).
    
    Args:
        client: Client instance
        token: Token único del cliente para el feed
    
    Returns:
        bytes: Contenido del feed iCal
    """
    from activities.models import ActivitySessionBooking
    
    cal = Calendar()
    
    # Propiedades del calendario
    gym_name = client.gym.commercial_name or client.gym.name
    cal.add('prodid', f'-//GymCRM//{gym_name}//ES')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', f'Mis Clases - {gym_name}')
    cal.add('x-wr-timezone', str(timezone.get_current_timezone()))
    
    # Obtener reservas confirmadas (pasadas recientes + futuras)
    # Incluimos las últimas 2 semanas para que el usuario vea historial reciente
    two_weeks_ago = timezone.now() - timedelta(days=14)
    
    bookings = ActivitySessionBooking.objects.filter(
        client=client,
        status='CONFIRMED',
        session__start_datetime__gte=two_weeks_ago
    ).select_related(
        'session',
        'session__activity',
        'session__room',
        'session__staff',
        'session__staff__user',
        'session__gym'
    ).order_by('session__start_datetime')
    
    for booking in bookings:
        event = _create_event_from_booking(booking)
        cal.add_component(event)
    
    return cal.to_ical()


def _create_event_from_booking(booking):
    """
    Crea un evento iCal a partir de una reserva.
    
    Args:
        booking: ActivitySessionBooking instance
    
    Returns:
        Event: Componente de evento iCal
    """
    session = booking.session
    activity = session.activity
    gym = session.gym
    
    event = Event()
    
    # Identificador único del evento (importante para actualizaciones)
    uid = f"booking-{booking.id}@gymcrm.local"
    event.add('uid', uid)
    
    # Título del evento
    event.add('summary', activity.name)
    
    # Fechas/horas
    event.add('dtstart', session.start_datetime)
    event.add('dtend', session.end_datetime)
    
    # Timestamps
    event.add('dtstamp', timezone.now())
    event.add('created', booking.booked_at)
    event.add('last-modified', booking.updated_at)
    
    # Ubicación
    location_parts = []
    if session.room:
        location_parts.append(f"Sala: {session.room.name}")
    if gym.address:
        location_parts.append(gym.address)
    if gym.city:
        location_parts.append(gym.city)
    
    location = ", ".join(location_parts) if location_parts else gym.commercial_name or gym.name
    event.add('location', location)
    
    # Descripción detallada
    description_parts = [
        f"📍 {gym.commercial_name or gym.name}",
    ]
    
    if session.staff:
        description_parts.append(f"👤 Instructor: {session.staff.user.get_full_name()}")
    
    if session.room:
        description_parts.append(f"🚪 Sala: {session.room.name}")
    
    if activity.description:
        description_parts.append(f"\n{activity.description}")
    
    if booking.spot_number:
        description_parts.append(f"\n🎯 Tu puesto: #{booking.spot_number}")
    
    description_parts.append(f"\n📱 Reserva #{booking.id}")
    
    event.add('description', "\n".join(description_parts))
    
    # Categoría
    if activity.category:
        event.add('categories', [activity.category.name])
    
    # Estado (confirmado)
    event.add('status', 'CONFIRMED')
    
    # Organizador (el gimnasio)
    if gym.email:
        organizer = vText(f"mailto:{gym.email}")
        organizer.params['CN'] = vText(gym.commercial_name or gym.name)
        event.add('organizer', organizer)
    
    # Alarma/Recordatorio (30 minutos antes por defecto)
    from icalendar import Alarm
    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('description', f'Tu clase de {activity.name} empieza en 30 minutos')
    alarm.add('trigger', timedelta(minutes=-30))
    event.add_component(alarm)
    
    # Segunda alarma (2 horas antes)
    alarm2 = Alarm()
    alarm2.add('action', 'DISPLAY')
    alarm2.add('description', f'Recordatorio: Tienes clase de {activity.name} hoy')
    alarm2.add('trigger', timedelta(hours=-2))
    event.add_component(alarm2)
    
    return event


def get_or_create_calendar_token(client):
    """
    Obtiene o crea un token único para el feed de calendario del cliente.
    Este token se usa en la URL de suscripción para identificar al cliente
    de forma segura sin exponer su ID.
    
    Args:
        client: Client instance
    
    Returns:
        str: Token único del cliente
    """
    # El token se guarda en el campo calendar_token del cliente
    # Si no existe, lo creamos
    if not client.calendar_token:
        client.calendar_token = secrets.token_urlsafe(32)
        client.save(update_fields=['calendar_token'])
    
    return client.calendar_token


def regenerate_calendar_token(client):
    """
    Regenera el token del calendario del cliente.
    Útil si el cliente quiere invalidar URLs de suscripción anteriores.
    
    Args:
        client: Client instance
    
    Returns:
        str: Nuevo token único
    """
    client.calendar_token = secrets.token_urlsafe(32)
    client.save(update_fields=['calendar_token'])
    return client.calendar_token


def get_calendar_feed_url(client, request=None):
    """
    Genera la URL completa del feed de calendario para el cliente.
    
    Args:
        client: Client instance
        request: HttpRequest (opcional, para construir URL absoluta)
    
    Returns:
        str: URL del feed de calendario
    """
    from django.urls import reverse
    
    token = get_or_create_calendar_token(client)
    
    # URL relativa
    url_path = reverse('calendar_feed', kwargs={'token': token})
    
    if request:
        return request.build_absolute_uri(url_path)
    
    # Fallback: construir URL con settings
    base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    return f"{base_url.rstrip('/')}{url_path}"
