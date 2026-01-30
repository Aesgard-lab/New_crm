"""
API endpoints para reconocimiento facial.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .services import FaceRecognitionService, check_face_recognition_available
from .models import ClientFaceEncoding, FaceRecognitionSettings


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

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def kiosk_verify(request, gym_id):
    """
    Endpoint para verificación en modo kiosko.
    No requiere autenticación (la tablet está en el gym).
    Debe estar protegido por token de kiosko o IP whitelist.
    """
    from organizations.models import Gym
    
    # Verificar token de kiosko (header)
    kiosk_token = request.headers.get('X-Kiosk-Token')
    
    gym = get_object_or_404(Gym, id=gym_id)
    settings, _ = FaceRecognitionSettings.objects.get_or_create(gym=gym)
    
    # TODO: Implementar verificación de token de kiosko
    # Por ahora solo verificamos que kiosk_mode está habilitado
    if not settings.kiosk_mode_enabled:
        return Response({
            'success': False,
            'error': 'Modo kiosko no habilitado'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Obtener imagen
    image = request.FILES.get('image')
    if not image:
        return Response({
            'success': False,
            'error': 'No image'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar
    service = FaceRecognitionService(gym)
    result = service.verify_face(image)
    
    if result['success']:
        client = result['client']
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
    Solo para staff.
    """
    from clients.models import Client
    from django.db.models import Exists, OuterRef
    
    staff = getattr(request.user, 'staff_profile', None)
    
    if not staff:
        return Response({
            'error': 'Solo disponible para staff'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Clientes con foto pero sin face encoding
    clients = Client.objects.filter(
        gym=staff.gym,
        status='active'
    ).exclude(
        photo=''
    ).exclude(
        photo__isnull=True
    ).exclude(
        # Excluir los que ya tienen face encoding
        id__in=ClientFaceEncoding.objects.values_list('client_id', flat=True)
    ).select_related('gym')[:50]  # Limitar a 50 para rendimiento
    
    return Response({
        'clients': [
            {
                'id': c.id,
                'full_name': c.full_name,
                'email': c.email,
                'photo': c.photo.url if c.photo else None
            }
            for c in clients
        ]
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