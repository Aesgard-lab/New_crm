"""
Vistas para el sistema de calendario iCal.
Permite a los clientes:
1. Descargar archivo .ics de una reserva específica
2. Obtener URL de suscripción para su calendario
3. Acceder al feed iCal con todas sus reservas
"""

from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from activities.models import ActivitySessionBooking
from clients.models import Client
from . import calendar_service


@login_required
@require_GET
def download_booking_ics(request, booking_id):
    """
    Descarga un archivo .ics para una reserva específica.
    El cliente puede añadir este archivo a su calendario.
    
    URL: /portal/calendar/booking/<booking_id>/download/
    """
    client = getattr(request.user, 'client_profile', None)
    if not client:
        raise Http404("Cliente no encontrado")
    
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


@require_GET
def calendar_feed(request, token):
    """
    Feed iCal público (no requiere autenticación).
    El token identifica al cliente de forma segura.
    
    Esta URL puede ser añadida como "suscripción" en cualquier
    aplicación de calendario (Google Calendar, Apple Calendar, Outlook, etc.)
    
    URL: /calendar/feed/<token>.ics
    """
    client = get_object_or_404(Client, calendar_token=token)
    
    # Generar el feed completo
    ics_content = calendar_service.generate_client_calendar_feed(client, token)
    
    response = HttpResponse(ics_content, content_type='text/calendar; charset=utf-8')
    
    # Headers para suscripción de calendario
    response['Content-Disposition'] = 'inline; filename="mis_clases.ics"'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


@login_required
@require_GET
def get_calendar_settings(request):
    """
    Obtiene la configuración de calendario del cliente actual.
    Retorna la URL del feed y el estado del token.
    
    URL: /portal/calendar/settings/
    """
    client = getattr(request.user, 'client_profile', None)
    if not client:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    
    # Obtener o crear token
    token = calendar_service.get_or_create_calendar_token(client)
    feed_url = calendar_service.get_calendar_feed_url(client, request)
    
    return JsonResponse({
        'feed_url': feed_url,
        'has_token': bool(token),
        'instructions': {
            'google': f"1. Abre Google Calendar\n2. Click en '+' junto a 'Otros calendarios'\n3. Selecciona 'Desde URL'\n4. Pega: {feed_url}",
            'apple': f"1. Abre la app Calendario\n2. Ve a Archivo > Nueva suscripción de calendario\n3. Pega: {feed_url}",
            'outlook': f"1. Abre Outlook\n2. Ve a Calendario > Añadir calendario > Suscribirse desde la web\n3. Pega: {feed_url}",
        }
    })


@login_required
@require_POST
def regenerate_calendar_token(request):
    """
    Regenera el token del calendario.
    Útil si el cliente quiere invalidar URLs anteriores por seguridad.
    
    URL: /portal/calendar/regenerate-token/
    """
    client = getattr(request.user, 'client_profile', None)
    if not client:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    
    new_token = calendar_service.regenerate_calendar_token(client)
    new_url = calendar_service.get_calendar_feed_url(client, request)
    
    return JsonResponse({
        'success': True,
        'feed_url': new_url,
        'message': 'Token regenerado. Las URLs anteriores ya no funcionarán.'
    })


@login_required
def calendar_sync_page(request):
    """
    Página del portal donde el cliente puede ver y copiar su URL de calendario.
    
    URL: /portal/calendar/
    """
    client = getattr(request.user, 'client_profile', None)
    if not client:
        raise Http404("Cliente no encontrado")
    
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
        'feed_url': feed_url,
        'upcoming_bookings': upcoming_bookings,
        'gym': client.gym,
    }
    
    return render(request, 'portal/calendar/sync.html', context)
