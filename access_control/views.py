"""
Vistas del módulo de Control de Acceso
======================================
Incluye:
- Dashboard de accesos en tiempo real
- Listado de entradas/salidas
- API para dispositivos de hardware (con autenticación por API Key)
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from functools import wraps
import json
import hmac
import hashlib
import logging

from .models import AccessDevice, AccessZone, AccessLog, AccessAlert, ClientAccessCredential
from .services import AccessControlService

# Security logger
security_logger = logging.getLogger('django.security')


# ===========================================
# SECURITY: API Key Authentication Decorator
# ===========================================

def require_device_api_key(view_func):
    """
    Decorator that validates API Key for hardware device endpoints.
    
    The API Key can be provided in:
    1. Header: X-API-Key
    2. Header: Authorization: Bearer <api_key>
    
    SECURITY: This prevents unauthorized access to hardware control APIs.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Extract API Key from headers
        api_key = None
        
        # Method 1: X-API-Key header
        api_key = request.headers.get('X-API-Key')
        
        # Method 2: Authorization Bearer
        if not api_key:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                api_key = auth_header[7:]
        
        if not api_key:
            security_logger.warning(
                f"Access API request without API key from IP: {get_client_ip(request)}"
            )
            return JsonResponse({
                'error': 'API Key required',
                'code': 'MISSING_API_KEY'
            }, status=401)
        
        # Validate API Key against active devices
        try:
            device = AccessDevice.objects.select_related('gym').get(
                api_key=api_key,
                is_active=True
            )
            # Attach device to request for use in view
            request.access_device = device
        except AccessDevice.DoesNotExist:
            security_logger.warning(
                f"Invalid API key attempt from IP: {get_client_ip(request)}, key: {api_key[:8]}..."
            )
            return JsonResponse({
                'error': 'Invalid API Key',
                'code': 'INVALID_API_KEY'
            }, status=401)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def get_client_ip(request):
    """Extract client IP from request, handling proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


# ===========================================
# VISTAS DEL BACKOFFICE
# ===========================================

@login_required
def access_dashboard(request):
    """Dashboard de control de acceso en tiempo real."""
    gym = request.gym
    now = timezone.now()
    today = now.date()
    
    # Servicio de control de acceso
    service = AccessControlService(gym)
    
    # Aforo actual
    occupancy = service.get_current_occupancy()
    clients_inside = service.get_clients_inside()
    
    # Estadísticas de hoy
    today_logs = AccessLog.objects.filter(gym=gym, timestamp__date=today)
    stats = {
        'entries_today': today_logs.filter(direction='ENTRY', status='GRANTED').count(),
        'exits_today': today_logs.filter(direction='EXIT', status='GRANTED').count(),
        'denied_today': today_logs.filter(status='DENIED').count(),
        'current_inside': occupancy['current_count'],
    }
    
    # Dispositivos
    devices = AccessDevice.objects.filter(gym=gym, is_active=True)
    devices_online = devices.filter(status='ONLINE').count()
    devices_total = devices.count()
    
    # Alertas sin resolver
    alerts = AccessAlert.objects.filter(
        gym=gym,
        is_resolved=False
    ).order_by('-created_at')[:10]
    
    # Zonas con aforo
    zones = AccessZone.objects.filter(gym=gym, is_active=True, max_capacity__isnull=False)
    zones_data = []
    for zone in zones:
        zones_data.append({
            'id': zone.id,
            'name': zone.name,
            'color': zone.color,
            'current': zone.get_current_occupancy(),
            'max': zone.max_capacity,
            'percentage': zone.occupancy_percentage
        })
    
    # Últimos accesos
    recent_logs = AccessLog.objects.filter(gym=gym).select_related('client', 'device')[:20]
    
    # Gráfico de accesos por hora (últimas 24h)
    hours_data = []
    for i in range(24):
        hour_start = now - timedelta(hours=24-i)
        hour_end = hour_start + timedelta(hours=1)
        count = AccessLog.objects.filter(
            gym=gym,
            direction='ENTRY',
            status='GRANTED',
            timestamp__gte=hour_start,
            timestamp__lt=hour_end
        ).count()
        hours_data.append({
            'hour': hour_start.strftime('%H:00'),
            'count': count
        })
    
    context = {
        'stats': stats,
        'clients_inside': clients_inside,
        'devices_online': devices_online,
        'devices_total': devices_total,
        'alerts': alerts,
        'zones_data': zones_data,
        'recent_logs': recent_logs,
        'hours_data': json.dumps(hours_data),
    }
    
    return render(request, 'backoffice/access_control/dashboard.html', context)


@login_required
def access_log_list(request):
    """Listado de todos los registros de acceso."""
    gym = request.gym
    
    # Filtros
    direction = request.GET.get('direction', '')
    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    client_search = request.GET.get('client', '')
    device_id = request.GET.get('device', '')
    
    logs = AccessLog.objects.filter(gym=gym).select_related('client', 'device')
    
    if direction:
        logs = logs.filter(direction=direction)
    if status:
        logs = logs.filter(status=status)
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    if client_search:
        logs = logs.filter(
            Q(client__first_name__icontains=client_search) |
            Q(client__last_name__icontains=client_search) |
            Q(client__email__icontains=client_search)
        )
    if device_id:
        logs = logs.filter(device_id=device_id)
    
    # Paginación
    paginator = Paginator(logs, 50)
    page = request.GET.get('page', 1)
    logs_page = paginator.get_page(page)
    
    # Datos para filtros
    devices = AccessDevice.objects.filter(gym=gym, is_active=True)
    
    context = {
        'logs': logs_page,
        'devices': devices,
        'filters': {
            'direction': direction,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
            'client': client_search,
            'device': device_id,
        }
    }
    
    return render(request, 'backoffice/access_control/log_list.html', context)


@login_required
def device_list(request):
    """Listado y gestión de dispositivos de acceso."""
    gym = request.gym
    today = timezone.now().date()
    
    devices = AccessDevice.objects.filter(gym=gym).select_related('zone')
    zones = AccessZone.objects.filter(gym=gym, is_active=True)
    
    # Añadir estadísticas a cada dispositivo
    for device in devices:
        today_logs = AccessLog.objects.filter(device=device, timestamp__date=today)
        device.today_entries = today_logs.filter(direction='ENTRY').count()
        device.today_exits = today_logs.filter(direction='EXIT').count()
    
    # Contadores de estado
    total_devices = devices.count()
    online_devices = devices.filter(status='ONLINE').count()
    offline_devices = devices.filter(status='OFFLINE').count()
    warning_devices = devices.filter(status='WARNING').count()
    
    context = {
        'devices': devices,
        'zones': zones,
        'total_devices': total_devices,
        'online_devices': online_devices,
        'offline_devices': offline_devices,
        'warning_devices': warning_devices,
    }
    
    return render(request, 'backoffice/access_control/device_list.html', context)


@login_required
def zone_list(request):
    """Listado y gestión de zonas de acceso."""
    gym = request.gym
    zones = AccessZone.objects.filter(gym=gym).prefetch_related('devices', 'allowed_membership_plans')
    
    zones_with_occupancy = []
    for zone in zones:
        zones_with_occupancy.append({
            'zone': zone,
            'current_occupancy': zone.get_current_occupancy(),
            'occupancy_percentage': zone.occupancy_percentage,
        })
    
    context = {
        'zones': zones_with_occupancy,
    }
    
    return render(request, 'backoffice/access_control/zone_list.html', context)


@login_required
def alert_list(request):
    """Listado de alertas de acceso."""
    gym = request.gym
    
    show_resolved = request.GET.get('show_resolved', 'false') == 'true'
    
    alerts = AccessAlert.objects.filter(gym=gym).select_related('client', 'device')
    
    if not show_resolved:
        alerts = alerts.filter(is_resolved=False)
    
    paginator = Paginator(alerts, 50)
    page = request.GET.get('page', 1)
    alerts_page = paginator.get_page(page)
    
    context = {
        'alerts': alerts_page,
        'show_resolved': show_resolved,
    }
    
    return render(request, 'backoffice/access_control/alert_list.html', context)


@login_required
@require_http_methods(['POST'])
def resolve_alert(request, alert_id):
    """Marca una alerta como resuelta."""
    alert = get_object_or_404(AccessAlert, id=alert_id, gym=request.gym)
    
    data = json.loads(request.body) if request.body else {}
    notes = data.get('notes', '')
    
    alert.mark_resolved(request.user, notes)
    
    return JsonResponse({'success': True})


@login_required
def client_access_history(request, client_id):
    """Historial de accesos de un cliente específico (para ficha de cliente)."""
    from clients.models import Client
    
    client = get_object_or_404(Client, id=client_id, gym=request.gym)
    
    # Estadísticas del cliente
    all_logs = AccessLog.objects.filter(client=client, gym=request.gym)
    
    stats = {
        'total_entries': all_logs.filter(direction='ENTRY', status='GRANTED').count(),
        'total_denials': all_logs.filter(status='DENIED').count(),
        'last_entry': all_logs.filter(direction='ENTRY', status='GRANTED').first(),
        'entries_this_month': all_logs.filter(
            direction='ENTRY',
            status='GRANTED',
            timestamp__month=timezone.now().month,
            timestamp__year=timezone.now().year
        ).count(),
    }
    
    # Calcular tiempo promedio de estancia
    exit_logs = all_logs.filter(direction='EXIT', status='GRANTED')[:30]
    durations = []
    for exit_log in exit_logs:
        duration = exit_log.duration_inside
        if duration:
            durations.append(duration.total_seconds())
    
    if durations:
        avg_seconds = sum(durations) / len(durations)
        stats['avg_duration'] = timedelta(seconds=int(avg_seconds))
    else:
        stats['avg_duration'] = None
    
    # Historial paginado
    logs = all_logs.select_related('device')
    paginator = Paginator(logs, 20)
    page = request.GET.get('page', 1)
    logs_page = paginator.get_page(page)
    
    # Credenciales del cliente
    credentials = ClientAccessCredential.objects.filter(client=client)
    
    context = {
        'client': client,
        'stats': stats,
        'logs': logs_page,
        'credentials': credentials,
    }
    
    return render(request, 'backoffice/access_control/client_history.html', context)


# ===========================================
# API PARA HARDWARE (Dispositivos)
# SECURITY: All endpoints require API Key authentication
# ===========================================

@csrf_exempt
@require_device_api_key
@require_http_methods(['POST'])
def api_validate_access(request):
    """
    API endpoint para que los dispositivos de hardware validen accesos.
    
    SECURITY: Requires valid API Key in X-API-Key header.
    
    POST /api/access/validate/
    Headers: X-API-Key: <device_api_key>
    {
        "credential_type": "RFID",
        "credential_value": "1234567890",
        "direction": "ENTRY"
    }
    
    Response:
    {
        "granted": true/false,
        "client_id": 123,
        "client_name": "Juan Pérez",
        "message": "Acceso concedido",
        "denial_reason": "" (si aplica)
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # SECURITY: Device is already validated by decorator
    device = request.access_device
    
    credential_type = data.get('credential_type')
    credential_value = data.get('credential_value')
    direction = data.get('direction', 'ENTRY')
    
    if not all([credential_type, credential_value]):
        return JsonResponse({
            'error': 'Missing required fields: credential_type, credential_value'
        }, status=400)
    
    # Actualizar heartbeat del dispositivo
    device.update_heartbeat()
    
    # Validar acceso
    service = AccessControlService(device.gym)
    result = service.validate_access(
        credential_type=credential_type,
        credential_value=credential_value,
        device=device,
        direction=direction
    )
    
    # Registrar en el log
    service.register_access(
        validation_result=result,
        device=device,
        direction=direction,
        credential_type=credential_type,
        credential_value=credential_value,
        raw_data=data
    )
    
    return JsonResponse(result.to_dict())


@csrf_exempt
@require_device_api_key
@require_http_methods(['POST'])
def api_validate_qr(request):
    """
    API endpoint para validar QR dinámicos de la app móvil.
    
    SECURITY: Requires valid API Key in X-API-Key header.
    
    POST /api/access/validate-qr/
    Headers: X-API-Key: <device_api_key>
    {
        "qr_token": "abc123...",
        "direction": "ENTRY"
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # SECURITY: Device is already validated by decorator
    device = request.access_device
    
    qr_token = data.get('qr_token')
    direction = data.get('direction', 'ENTRY')
    
    if not qr_token:
        return JsonResponse({
            'error': 'Missing required field: qr_token'
        }, status=400)
    
    device.update_heartbeat()
    
    # Validar QR
    service = AccessControlService(device.gym)
    result = service.validate_qr_token(qr_token, device)
    
    # Registrar
    service.register_access(
        validation_result=result,
        device=device,
        direction=direction,
        credential_type='QR_DYNAMIC',
        credential_value=qr_token[:20] + '...',  # Don't log full token
        raw_data={'direction': direction}  # Don't log full QR
    )
    
    return JsonResponse(result.to_dict())


@csrf_exempt
@require_device_api_key
@require_http_methods(['POST'])
def api_device_heartbeat(request):
    """
    API endpoint para que los dispositivos reporten su estado.
    
    SECURITY: Requires valid API Key in X-API-Key header.
    
    POST /api/access/heartbeat/
    Headers: X-API-Key: <device_api_key>
    {
        "status": "ONLINE",
        "extra_data": {...}
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # SECURITY: Device is already validated by decorator
    device = request.access_device
    
    status = data.get('status', 'ONLINE')
    error_message = data.get('error_message', '')
    
    if status == 'ERROR':
        device.set_error(error_message)
    else:
        device.update_heartbeat()
        if status in ['ONLINE', 'OFFLINE', 'MAINTENANCE']:
            device.status = status
            device.save(update_fields=['status'])
    
    return JsonResponse({'success': True, 'timestamp': timezone.now().isoformat()})


@csrf_exempt
@require_device_api_key
@require_http_methods(['GET'])
def api_get_occupancy(request):
    """
    API endpoint para consultar el aforo actual.
    
    SECURITY: Requires valid API Key in X-API-Key header.
    
    GET /api/access/occupancy/
    Headers: X-API-Key: <device_api_key>
    Optional params: ?zone_id=2
    """
    # SECURITY: Device is already validated by decorator
    device = request.access_device
    gym = device.gym
    
    zone_id = request.GET.get('zone_id')
    zone = None
    
    if zone_id:
        try:
            zone = AccessZone.objects.get(id=zone_id, gym=gym)
        except AccessZone.DoesNotExist:
            return JsonResponse({'error': 'Zone not found'}, status=404)
    else:
        zone = device.zone  # Use device's assigned zone
    
    service = AccessControlService(gym)
    occupancy = service.get_current_occupancy(zone)
    
    return JsonResponse(occupancy)


# ===========================================
# API JSON PARA FRONTEND (AJAX)
# ===========================================

@login_required
def api_live_access_feed(request):
    """
    Endpoint para actualización en tiempo real del dashboard.
    Llamado por AJAX cada X segundos.
    """
    gym = request.gym
    service = AccessControlService(gym)
    
    # Aforo actual
    occupancy = service.get_current_occupancy()
    clients_inside = service.get_clients_inside()
    
    # Últimos 10 accesos
    recent = AccessLog.objects.filter(gym=gym).select_related('client', 'device')[:10]
    recent_data = [{
        'id': log.id,
        'client_name': f'{log.client.first_name} {log.client.last_name}' if log.client else 'Desconocido',
        'direction': log.direction,
        'status': log.status,
        'device': log.device.name if log.device else '-',
        'timestamp': log.timestamp.strftime('%H:%M:%S'),
    } for log in recent]
    
    # Alertas nuevas
    alerts_count = AccessAlert.objects.filter(gym=gym, is_resolved=False).count()
    
    return JsonResponse({
        'occupancy': occupancy,
        'clients_inside_count': len(clients_inside),
        'recent_logs': recent_data,
        'unresolved_alerts': alerts_count,
        'timestamp': timezone.now().isoformat(),
    })


@login_required
@require_http_methods(['POST'])
def api_manual_access(request):
    """
    Registrar un acceso manual (ej: recepcionista abre manualmente).
    """
    gym = request.gym
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    client_id = data.get('client_id')
    direction = data.get('direction', 'ENTRY')
    notes = data.get('notes', '')
    
    if not client_id:
        return JsonResponse({'error': 'client_id required'}, status=400)
    
    from clients.models import Client
    try:
        client = Client.objects.get(id=client_id, gym=gym)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Client not found'}, status=404)
    
    # Crear log de acceso manual
    log = AccessLog.objects.create(
        gym=gym,
        client=client,
        direction=direction,
        status='MANUAL',
        credential_type='MANUAL',
        processed_by=request.user,
        notes=notes
    )
    
    return JsonResponse({
        'success': True,
        'log_id': log.id,
        'message': f'Acceso {direction} registrado para {client.first_name} {client.last_name}'
    })


@login_required
@require_http_methods(['POST'])
def api_device_bulk(request):
    """
    Acciones masivas sobre dispositivos.
    Acciones: test, enable, disable
    """
    gym = request.gym
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    action = data.get('action')
    device_ids = data.get('device_ids', [])
    
    if not action or not device_ids:
        return JsonResponse({'error': 'action and device_ids required'}, status=400)
    
    devices = AccessDevice.objects.filter(gym=gym, id__in=device_ids)
    count = devices.count()
    
    if count == 0:
        return JsonResponse({'error': 'No devices found'}, status=404)
    
    if action == 'test':
        # Simular prueba de dispositivos
        return JsonResponse({
            'success': True,
            'message': f'Comando de prueba enviado a {count} dispositivo(s)'
        })
    
    elif action == 'enable':
        devices.update(is_active=True)
        return JsonResponse({
            'success': True,
            'message': f'{count} dispositivo(s) activado(s)'
        })
    
    elif action == 'disable':
        devices.update(is_active=False)
        return JsonResponse({
            'success': True,
            'message': f'{count} dispositivo(s) desactivado(s)'
        })
    
    else:
        return JsonResponse({'error': f'Unknown action: {action}'}, status=400)


# ===========================================
# VISTAS CRUD DE DISPOSITIVOS Y ZONAS
# ===========================================

@login_required
def device_create(request):
    """Crear nuevo dispositivo de acceso."""
    gym = request.gym
    zones = AccessZone.objects.filter(gym=gym, is_active=True)
    
    if request.method == 'POST':
        import uuid
        
        device = AccessDevice(
            gym=gym,
            name=request.POST.get('name'),
            device_type=request.POST.get('device_type'),
            provider=request.POST.get('provider', 'GENERIC'),
            device_id=request.POST.get('device_id') or f"DEV-{uuid.uuid4().hex[:8].upper()}",
            location=request.POST.get('location', ''),
            direction=request.POST.get('direction', 'BIDIRECTIONAL'),
            ip_address=request.POST.get('ip_address') or None,
            api_key=request.POST.get('api_key') or uuid.uuid4().hex,
            is_active='is_active' in request.POST,
        )
        
        zone_id = request.POST.get('zone')
        if zone_id:
            device.zone_id = zone_id
        
        device.save()
        
        from django.shortcuts import redirect
        from django.contrib import messages
        messages.success(request, f'Dispositivo "{device.name}" creado correctamente.')
        return redirect('access_control:device_list')
    
    return render(request, 'backoffice/access_control/device_form.html', {
        'zones': zones,
        'provider_choices': AccessDevice.PROVIDER_CHOICES,
        'device_type_choices': AccessDevice.DEVICE_TYPES,
    })


@login_required
def device_edit(request, device_id):
    """Editar dispositivo de acceso existente."""
    gym = request.gym
    device = get_object_or_404(AccessDevice, id=device_id, gym=gym)
    zones = AccessZone.objects.filter(gym=gym, is_active=True)
    
    if request.method == 'POST':
        device.name = request.POST.get('name')
        device.device_type = request.POST.get('device_type')
        device.provider = request.POST.get('provider', 'GENERIC')
        device.device_id = request.POST.get('device_id')
        device.location = request.POST.get('location', '')
        device.direction = request.POST.get('direction', 'BIDIRECTIONAL')
        
        # Handle IP address - set to None if empty
        ip_value = request.POST.get('ip_address', '').strip()
        device.ip_address = ip_value if ip_value else None
        
        if request.POST.get('api_key'):
            device.api_key = request.POST.get('api_key')
        
        device.is_active = 'is_active' in request.POST
        
        zone_id = request.POST.get('zone')
        device.zone_id = zone_id if zone_id else None
        
        device.save()
        
        from django.shortcuts import redirect
        from django.contrib import messages
        messages.success(request, f'Dispositivo "{device.name}" actualizado.')
        return redirect('access_control:device_list')
    
    # Create form data from device
    form = {
        'name': {'value': device.name},
        'device_type': {'value': device.device_type},
        'provider': {'value': device.provider},
        'device_id': {'value': device.device_id},
        'location': {'value': device.location},
        'ip_address': {'value': device.ip_address or ''},
        'api_key': {'value': device.api_key},
        'is_active': {'value': device.is_active},
        'zone': {'value': str(device.zone_id) if device.zone_id else ''},
    }
    
    return render(request, 'backoffice/access_control/device_form.html', {
        'device': device,
        'form': form,
        'zones': zones,
        'provider_choices': AccessDevice.PROVIDER_CHOICES,
        'device_type_choices': AccessDevice.DEVICE_TYPES,
    })


@login_required
def device_detail(request, device_id):
    """Detalle de un dispositivo."""
    gym = request.gym
    device = get_object_or_404(AccessDevice, id=device_id, gym=gym)
    
    # Estadísticas del dispositivo
    today = timezone.now().date()
    logs = AccessLog.objects.filter(device=device, timestamp__date=today)
    
    stats = {
        'entries_today': logs.filter(direction='ENTRY', status='GRANTED').count(),
        'exits_today': logs.filter(direction='EXIT', status='GRANTED').count(),
        'denied_today': logs.filter(status='DENIED').count(),
    }
    
    # Últimos logs
    recent_logs = AccessLog.objects.filter(device=device).select_related('client')[:30]
    
    return render(request, 'backoffice/access_control/device_detail.html', {
        'device': device,
        'stats': stats,
        'recent_logs': recent_logs,
    })


@login_required
def zone_create(request):
    """Crear nueva zona de acceso."""
    gym = request.gym
    
    if request.method == 'POST':
        zone = AccessZone(
            gym=gym,
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            max_capacity=int(request.POST.get('max_capacity', 50)),
            warning_threshold=int(request.POST.get('warning_threshold', 75)),
            color=request.POST.get('color', '#6366f1'),
            requires_membership='requires_membership' in request.POST,
            enforce_capacity='enforce_capacity' in request.POST,
            is_active='is_active' in request.POST,
        )
        zone.save()
        
        from django.shortcuts import redirect
        from django.contrib import messages
        messages.success(request, f'Zona "{zone.name}" creada correctamente.')
        return redirect('access_control:zone_list')
    
    return render(request, 'backoffice/access_control/zone_form.html', {})


@login_required
def zone_edit(request, zone_id):
    """Editar zona de acceso existente."""
    gym = request.gym
    zone = get_object_or_404(AccessZone, id=zone_id, gym=gym)
    
    if request.method == 'POST':
        zone.name = request.POST.get('name')
        zone.description = request.POST.get('description', '')
        zone.max_capacity = int(request.POST.get('max_capacity', 50))
        zone.warning_threshold = int(request.POST.get('warning_threshold', 75))
        zone.color = request.POST.get('color', '#6366f1')
        zone.requires_membership = 'requires_membership' in request.POST
        zone.enforce_capacity = 'enforce_capacity' in request.POST
        zone.is_active = 'is_active' in request.POST
        zone.save()
        
        from django.shortcuts import redirect
        from django.contrib import messages
        messages.success(request, f'Zona "{zone.name}" actualizada.')
        return redirect('access_control:zone_list')
    
    return render(request, 'backoffice/access_control/zone_form.html', {
        'zone': zone,
    })
