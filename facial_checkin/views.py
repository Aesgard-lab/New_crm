"""
Vistas web para reconocimiento facial.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from .models import FaceRecognitionSettings, ClientFaceEncoding
from .services import FaceRecognitionService, check_face_recognition_available


@login_required
def face_settings_view(request):
    """
    Vista de configuración de reconocimiento facial (backoffice).
    """
    gym = getattr(request, 'gym', None)
    
    if not gym:
        messages.error(request, 'Acceso no autorizado')
        return redirect('home')
    
    settings, created = FaceRecognitionSettings.objects.get_or_create(gym=gym)
    service = FaceRecognitionService(gym)
    
    # Re-verificar disponibilidad de la librería (por si se instaló en caliente)
    library_available = check_face_recognition_available()
    
    if request.method == 'POST':
        # Actualizar configuración
        settings.enabled = request.POST.get('enabled') == 'on'
        settings.allow_qr_checkin = request.POST.get('allow_qr_checkin') == 'on'
        settings.allow_face_checkin = request.POST.get('allow_face_checkin') == 'on'
        settings.allow_manual_checkin = request.POST.get('allow_manual_checkin') == 'on'
        settings.kiosk_mode_enabled = request.POST.get('kiosk_mode_enabled') == 'on'
        settings.auto_open_turnstile = request.POST.get('auto_open_turnstile') == 'on'
        
        kiosk_message = request.POST.get('kiosk_welcome_message', '').strip()
        if kiosk_message:
            settings.kiosk_welcome_message = kiosk_message
        
        try:
            threshold = float(request.POST.get('confidence_threshold', 0.6))
            settings.confidence_threshold = max(0.3, min(0.9, threshold))
        except ValueError:
            pass
        
        settings.save()
        messages.success(request, 'Configuración guardada correctamente')
        return redirect('facial_checkin:settings')
    
    # Obtener estadísticas
    stats = service.get_stats()
    
    context = {
        'settings': settings,
        'stats': stats,
        'library_available': library_available,
        'gym': gym,
    }
    
    return render(request, 'face_recognition/settings.html', context)


@login_required
def client_register_face(request):
    """
    Vista para que el cliente registre su rostro.
    """
    client = getattr(request.user, 'client', None)
    
    if not client:
        messages.error(request, 'Acceso no autorizado')
        return redirect('/')
    
    gym = client.gym
    settings, _ = FaceRecognitionSettings.objects.get_or_create(gym=gym)
    
    # Verificar si está habilitado
    if not settings.enabled or not settings.allow_face_checkin:
        messages.warning(request, 'El reconocimiento facial no está disponible en este momento')
        return redirect('portal:home')
    
    # Ver si ya tiene rostro registrado
    existing = ClientFaceEncoding.objects.filter(client=client).first()
    
    context = {
        'has_face_registered': existing is not None,
        'registration_date': existing.registered_at if existing else None,
        'library_available': check_face_recognition_available(),
        'gym': gym,
    }
    
    return render(request, 'face_recognition/register.html', context)


def kiosk_view(request):
    """
    Vista de kiosko para check-in facial.
    Esta vista es fullscreen para tablets.
    """
    # Obtener gym desde query param o sesión
    gym_id = request.GET.get('gym_id')
    
    if not gym_id:
        return render(request, 'face_recognition/kiosk_setup.html')
    
    from organizations.models import Gym
    gym = get_object_or_404(Gym, id=gym_id)
    settings, _ = FaceRecognitionSettings.objects.get_or_create(gym=gym)
    
    if not settings.kiosk_mode_enabled:
        return render(request, 'face_recognition/kiosk_disabled.html', {'gym': gym})
    
    context = {
        'gym': gym,
        'settings': settings,
        'welcome_message': settings.kiosk_welcome_message,
    }
    
    return render(request, 'face_recognition/kiosk.html', context)

