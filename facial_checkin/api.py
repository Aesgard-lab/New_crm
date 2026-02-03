"""
API endpoints para reconocimiento facial.
"""
import secrets
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .services import FaceRecognitionService, check_face_recognition_available
from .models import ClientFaceEncoding, FaceRecognitionSettings
from core.ratelimit import get_client_ip


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def face_recognition_status(request):
    """
    Verifica si el reconocimiento facial está disponible y configurado.
    """
    client = getattr(request.user, 'client', None)
    
    if not client:
        return Response({
            'available': False,
            'error': 'No client associated'
        })
    
    gym = client.gym
    service = FaceRecognitionService(gym)
    
    # Obtener settings
    settings, _ = FaceRecognitionSettings.objects.get_or_create(gym=gym)
    
    # Ver si el cliente tiene face registered
    has_face = ClientFaceEncoding.objects.filter(client=client).exists()
    
    # Verificar librería dinámicamente
    library_available = check_face_recognition_available()
    
    return Response({
        'library_available': library_available,
        'enabled_for_gym': settings.enabled and settings.allow_face_checkin,
        'client_registered': has_face,
        'checkin_methods': {
            'qr': settings.allow_qr_checkin,
            'face': settings.allow_face_checkin,
            'manual': settings.allow_manual_checkin,
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def register_face(request):
    """
    Registra el rostro del cliente autenticado.
    
    POST con:
    - image: archivo de imagen (JPEG/PNG)
    - consent: bool (consentimiento GDPR)
    """
    client = getattr(request.user, 'client', None)
    
    if not client:
        return Response({
            'success': False,
            'error': 'No se encontró cliente asociado'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar que el gym tiene face recognition habilitado
    settings, _ = FaceRecognitionSettings.objects.get_or_create(gym=client.gym)
    
    if not settings.enabled:
        return Response({
            'success': False,
            'error': 'El reconocimiento facial no está habilitado para este gimnasio'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Obtener imagen
    image = request.FILES.get('image')
    if not image:
        return Response({
            'success': False,
            'error': 'No se proporcionó imagen'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar consentimiento
    consent = request.data.get('consent', 'false').lower() == 'true'
    
    if not consent:
        return Response({
            'success': False,
            'error': 'Se requiere consentimiento para procesar datos biométricos'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Registrar rostro
    service = FaceRecognitionService(client.gym)
    result = service.register_face(client, image, consent=consent)
    
    if result['success']:
        return Response({
            'success': True,
            'message': 'Rostro registrado correctamente',
            'quality_score': result['quality_score']
        })
    else:
        return Response({
            'success': False,
            'error': result.get('error', 'Error desconocido')
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_from_photo(request):
    """
    Registra el rostro del cliente usando su foto de perfil existente.
    Solo para staff - permite registrar masivamente.
    
    POST con:
    - client_id: ID del cliente
    - consent: bool (consentimiento GDPR)
    """
    staff = getattr(request.user, 'staff_profile', None)
    
    if not staff:
        return Response({
            'success': False,
            'error': 'Solo disponible para staff'
        }, status=status.HTTP_403_FORBIDDEN)
    
    client_id = request.data.get('client_id')
    if not client_id:
        return Response({
            'success': False,
            'error': 'Se requiere client_id'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    from clients.models import Client
    try:
        client = Client.objects.get(id=client_id, gym=staff.gym)
    except Client.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Cliente no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    
    consent = request.data.get('consent', 'false').lower() == 'true'
    
    service = FaceRecognitionService(staff.gym)
    result = service.register_from_client_photo(client, consent=consent)
    
    if result['success']:
        return Response({
            'success': True,
            'message': f'Rostro de {client.full_name} registrado correctamente',
            'quality_score': result['quality_score']
        })
    else:
        return Response({
            'success': False,
            'error': result.get('error', 'Error desconocido')
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def verify_face(request):
    """
    Verifica un rostro para check-in.
    
    POST con:
    - image: archivo de imagen
    - session_id: (opcional) ID de la sesión de actividad
    """
    from activities.models import ActivitySession, SessionCheckin
    
    client = getattr(request.user, 'client', None)
    staff = getattr(request.user, 'staff_profile', None)
    
    # Determinar el gym
    if client:
        gym = client.gym
    elif staff:
        gym = staff.gym
    else:
        return Response({
            'success': False,
            'error': 'No autorizado'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Verificar configuración
    settings, _ = FaceRecognitionSettings.objects.get_or_create(gym=gym)
    
    if not settings.allow_face_checkin:
        return Response({
            'success': False,
            'error': 'Check-in facial no habilitado'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Obtener imagen
    image = request.FILES.get('image')
    if not image:
        return Response({
            'success': False,
            'error': 'No se proporcionó imagen'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar rostro
    service = FaceRecognitionService(gym)
    result = service.verify_face(image)
    
    if result['success']:
        matched_client = result['client']
        
        # Si hay session_id, hacer check-in automático
        session_id = request.data.get('session_id')
        checkin_result = None
        
        if session_id:
            try:
                session = ActivitySession.objects.get(id=session_id, activity__gym=gym)
                checkin_result = service.do_session_checkin(
                    client=matched_client,
                    session=session,
                    confidence=result['confidence']
                )
            except ActivitySession.DoesNotExist:
                checkin_result = {'success': False, 'error': 'Sesión no encontrada'}
        
        return Response({
            'success': True,
            'client': {
                'id': matched_client.id,
                'name': matched_client.full_name,
                'photo': matched_client.photo.url if matched_client.photo else None,
            },
            'confidence': result['confidence'],
            'processing_time_ms': result.get('processing_time_ms'),
            'checkin_done': checkin_result['success'] if checkin_result else False,
            'checkin_error': checkin_result.get('error') if checkin_result and not checkin_result['success'] else None,
            'message': f'¡Hola {matched_client.first_name}!'
        })
    else:
        return Response({
            'success': False,
            'error': result.get('error', 'No se reconoció el rostro'),
            'processing_time_ms': result.get('processing_time_ms')
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_face_data(request):
    """
    Elimina los datos faciales del cliente (GDPR - derecho al olvido).
    """
    client = getattr(request.user, 'client', None)
    
    if not client:
        return Response({
            'success': False,
            'error': 'No se encontró cliente'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    service = FaceRecognitionService(client.gym)
    deleted = service.delete_face_data(client)
    
    return Response({
        'success': True,
        'deleted': deleted,
        'message': 'Datos faciales eliminados' if deleted else 'No había datos registrados'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def face_recognition_stats(request):
    """
    Obtiene estadísticas de uso (solo para staff).
    """
    staff = getattr(request.user, 'staff', None)
    
    if not staff:
        return Response({
            'error': 'Solo disponible para staff'
        }, status=status.HTTP_403_FORBIDDEN)
    
    service = FaceRecognitionService(staff.gym)
    stats = service.get_stats()
    
    return Response(stats)


# ============================================
# Endpoints para el modo Kiosko
# ============================================

import logging
security_logger = logging.getLogger('django.security')


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def kiosk_verify(request, gym_id):
    """
    Endpoint para verificación en modo kiosko.
    
    SECURITY:
    - Requiere token de kiosko válido en header X-Kiosk-Token
    - Opcionalmente valida IP whitelist
    - Rate limited implícitamente por el procesamiento de imagen
    """
    from organizations.models import Gym
    from django_ratelimit.decorators import ratelimit
    from django_ratelimit.exceptions import Ratelimited
    
    client_ip = get_client_ip(request)
    
    # Verificar token de kiosko (header)
    kiosk_token = request.headers.get('X-Kiosk-Token', '')
    
    gym = get_object_or_404(Gym, id=gym_id)
    settings, _ = FaceRecognitionSettings.objects.get_or_create(gym=gym)
    
    # SECURITY: Verificar que el modo kiosko está habilitado
    if not settings.kiosk_mode_enabled:
        security_logger.warning(
            f"Kiosk access attempt on disabled gym: gym_id={gym_id}, ip={client_ip}"
        )
        return Response({
            'success': False,
            'error': 'Modo kiosko no habilitado'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # SECURITY: Verificar token de kiosko
    if not settings.kiosk_token:
        # Auto-generar token si no existe
        import secrets
        settings.kiosk_token = secrets.token_urlsafe(32)
        settings.save(update_fields=['kiosk_token'])
        security_logger.info(
            f"Kiosk token auto-generated for gym_id={gym_id}. "
            f"Configure it in admin panel."
        )
    
    if not kiosk_token or not secrets.compare_digest(kiosk_token, settings.kiosk_token):
        security_logger.warning(
            f"Invalid kiosk token attempt: gym_id={gym_id}, ip={client_ip}, "
            f"token_provided={'yes' if kiosk_token else 'no'}"
        )
        return Response({
            'success': False,
            'error': 'Token de kiosko inválido'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # SECURITY: Verificar IP whitelist (si está configurada)
    if settings.kiosk_allowed_ips:
        allowed_ips = [ip.strip() for ip in settings.kiosk_allowed_ips.split('\n') if ip.strip()]
        if allowed_ips and client_ip not in allowed_ips:
            security_logger.warning(
                f"Kiosk IP not in whitelist: gym_id={gym_id}, ip={client_ip}"
            )
            return Response({
                'success': False,
                'error': 'IP no autorizada'
            }, status=status.HTTP_403_FORBIDDEN)
    
    # Obtener imagen
    image = request.FILES.get('image')
    if not image:
        return Response({
            'success': False,
            'error': 'No image'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # SECURITY: Validar tamaño de imagen (máx 10MB)
    if image.size > 10 * 1024 * 1024:
        return Response({
            'success': False,
            'error': 'Imagen demasiado grande (máx 10MB)'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar
    service = FaceRecognitionService(gym)
    result = service.verify_face(image)
    
    if result['success']:
        client = result['client']
        security_logger.info(
            f"Kiosk face recognition success: gym_id={gym_id}, "
            f"client_id={client.id}, confidence={result['confidence']}"
        )
        return Response({
            'success': True,
            'client_name': client.first_name,
            'client_photo': client.photo.url if client.photo else None,
            'confidence': result['confidence'],
            'welcome_message': f"¡Hola {client.first_name}!",
            'auto_open_turnstile': settings.auto_open_turnstile
        })
    else:
        return Response({
            'success': False,
            'error': 'not_recognized',
            'message': 'No reconocido. Usa QR o contacta recepción.'
        }, status=status.HTTP_404_NOT_FOUND)

# ============================================
# Endpoints auxiliares para gestión de clientes
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def clients_with_photos_no_face(request):
    """
    Devuelve la lista de clientes que tienen foto de perfil pero no tienen
    rostro registrado para reconocimiento facial.
    Solo para staff o usuarios con gimnasio asignado.
    """
    from clients.models import Client
    from django.db.models import Exists, OuterRef
    
    # Obtener el gimnasio del request (middleware) o del staff_profile
    gym = getattr(request, 'gym', None)
    
    if not gym:
        staff = getattr(request.user, 'staff_profile', None)
        if staff:
            gym = staff.gym
    
    if not gym:
        return Response({
            'error': 'No se pudo determinar el gimnasio'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Subquery para verificar si tiene face encoding
    has_face_encoding = ClientFaceEncoding.objects.filter(
        client_id=OuterRef('pk')
    )
    
    # Clientes con foto pero sin face encoding
    clients_qs = Client.objects.filter(
        gym=gym,
        status='active'
    ).exclude(
        photo=''
    ).exclude(
        photo__isnull=True
    ).annotate(
        has_face=Exists(has_face_encoding)
    ).filter(
        has_face=False
    ).select_related('gym')
    
    # Log para debug
    import logging
    logger = logging.getLogger(__name__)
    
    # Filtrar solo los que realmente tienen una foto válida
    clients = []
    for c in clients_qs[:100]:  # Revisar hasta 100
        if c.photo and c.photo.name:  # Verificar que tiene nombre de archivo
            try:
                # Intentar obtener la URL (puede fallar si el archivo no existe)
                photo_url = c.photo.url
                clients.append({
                    'id': c.id,
                    'full_name': c.full_name,
                    'email': c.email,
                    'photo': photo_url
                })
                if len(clients) >= 50:
                    break
            except Exception:
                pass  # Ignorar si hay error con la foto
    
    logger.info(f"Clientes con foto válida sin face encoding en gym {gym.id}: {len(clients)}")
    
    return Response({
        'clients': clients
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_clients(request):
    """
    Busca clientes por nombre, email o teléfono.
    Solo para staff.
    """
    from clients.models import Client
    from django.db.models import Q
    
    staff = getattr(request.user, 'staff_profile', None)
    
    if not staff:
        return Response({
            'error': 'Solo disponible para staff'
        }, status=status.HTTP_403_FORBIDDEN)
    
    query = request.query_params.get('q', '')
    
    if len(query) < 2:
        return Response({'results': []})
    
    clients = Client.objects.filter(
        gym=staff.gym,
        status='active'
    ).filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(phone__icontains=query)
    )[:20]
    
    return Response({
        'results': [
            {
                'id': c.id,
                'full_name': c.full_name,
                'email': c.email,
                'phone': c.phone,
                'photo': c.photo.url if c.photo else None
            }
            for c in clients
        ]
    })