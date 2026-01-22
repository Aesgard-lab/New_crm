from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from .models import Advertisement, AdvertisementImpression
from clients.models import Client
import json


@login_required
@require_http_methods(["GET"])
def api_get_active_advertisements(request):
    """
    API endpoint para obtener anuncios activos para el cliente actual.
    
    Query params:
    - position: Filtrar por posición (HERO_CAROUSEL, STICKY_FOOTER, INLINE_MIDDLE, STORIES)
    - screen: Filtrar por pantalla (HOME, CLASS_CATALOG, CLASS_DETAIL, PROFILE, BOOKINGS, SHOP, CHECKIN, SETTINGS)
    
    Returns:
    {
        "count": 2,
        "results": [
            {
                "id": 1,
                "title": "Black Friday 50% OFF",
                "description": "...",
                "position": "HERO_CAROUSEL",
                "ad_type": "INTERNAL_PROMO",
                "image_url": "https://...",
                "image_mobile_url": "https://...",
                "video_url": null,
                "cta": {
                    "text": "¡Reserva Ahora!",
                    "action": "BOOK_CLASS",
                    "url": ""
                },
                "priority": 1,
                "duration_seconds": 5,
                "is_collapsible": true,
                "background_color": "#9333ea",
                "target_screens": ["HOME", "CLASS_CATALOG"]
            }
        ]
    }
    """
    try:
        # Obtener el cliente del usuario autenticado
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
        
        # Filtros
        position = request.GET.get('position', None)
        screen = request.GET.get('screen', None)
        
        # Query base: anuncios activos
        now = timezone.now()
        ads_query = Advertisement.objects.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now),
            Q(end_date__isnull=True) | Q(end_date__gte=now),
            is_active=True
        )
        
        # Filtrar por gimnasio del cliente
        ads_query = ads_query.filter(
            Q(target_gyms__isnull=True) | Q(target_gyms=client.gym)
        ).distinct()
        
        # Filtrar por posición si se especifica
        if position:
            ads_query = ads_query.filter(position=position)
        
        # Filtrar por pantalla si se especifica
        if screen:
            # Mostrar anuncios que:
            # 1. Tengan target_screens vacío (todas las pantallas)
            # 2. O que contengan la pantalla específica en su lista
            ads_query = ads_query.filter(
                Q(target_screens=[]) | Q(target_screens__contains=[screen])
            )
        
        # Ordenar por prioridad y fecha de creación
        ads_query = ads_query.order_by('-priority', '-created_at')
        
        # Serializar resultados
        results = []
        for ad in ads_query:
            # Construir URLs absolutas de imágenes
            image_url = None
            image_mobile_url = None
            video_url = None
            
            if ad.image_desktop:
                image_url = request.build_absolute_uri(ad.image_desktop.url)
            if ad.image_mobile:
                image_mobile_url = request.build_absolute_uri(ad.image_mobile.url)
            if ad.video_url:
                video_url = ad.video_url  # Es una URL, no un archivo
            
            # CTA
            cta = None
            if ad.cta_text:
                cta = {
                    'text': ad.cta_text,
                    'action': ad.cta_action,
                    'url': ad.cta_url or ''
                }
            
            results.append({
                'id': ad.id,
                'title': ad.title,
                'position': ad.position,
                'ad_type': ad.ad_type,
                'image_url': image_url,
                'image_mobile_url': image_mobile_url,
                'video_url': video_url,
                'cta': cta,
                'priority': ad.priority,
                'duration_seconds': ad.duration_seconds,
                'is_collapsible': ad.is_collapsible,
                'background_color': '#ffffff',
                'target_screens': ad.target_screens if ad.target_screens else []
            })
        
        return JsonResponse({
            'count': len(results),
            'results': results
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_POST
def api_track_advertisement_impression(request, ad_id):
    """
    Registra que el usuario ha visto el anuncio.
    
    POST /api/advertisements/{ad_id}/impression/
    
    Returns:
    {
        "success": true,
        "message": "Impresión registrada"
    }
    """
    try:
        # Obtener el cliente del usuario autenticado
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
        
        # Obtener el anuncio
        advertisement = get_object_or_404(Advertisement, id=ad_id)
        
        # Crear la impresión
        AdvertisementImpression.objects.create(
            advertisement=advertisement,
            client=client,
            clicked=False
        )
        
        # Incrementar el contador de impresiones
        advertisement.impressions += 1
        advertisement.save(update_fields=['impressions'])
        
        return JsonResponse({
            'success': True,
            'message': 'Impresión registrada'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_POST
def api_track_advertisement_click(request, ad_id):
    """
    Registra que el usuario ha hecho click en el CTA del anuncio.
    
    POST /api/advertisements/{ad_id}/click/
    Body: {"action": "BOOK_CLASS"}
    
    Returns:
    {
        "success": true,
        "message": "Click registrado",
        "redirect_to": "/classes/" (opcional)
    }
    """
    try:
        # Obtener el cliente del usuario autenticado
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
        
        # Obtener el anuncio
        advertisement = get_object_or_404(Advertisement, id=ad_id)
        
        # Parsear el body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}
        
        action = data.get('action', advertisement.cta_action)
        
        # Crear la impresión con click=True
        AdvertisementImpression.objects.create(
            advertisement=advertisement,
            client=client,
            clicked=True
        )
        
        # Incrementar el contador de clicks
        advertisement.clicks += 1
        advertisement.save(update_fields=['clicks'])
        
        # Determinar la redirección según la acción
        redirect_map = {
            'BOOK_CLASS': '/portal/activities/',
            'VIEW_CATALOG': '/portal/catalog/',
            'VIEW_MEMBERSHIPS': '/portal/memberships/',
            'VIEW_SERVICES': '/portal/services/',
            'VIEW_PROFILE': '/portal/profile/',
            'CONTACT_US': '/portal/contact/',
            'EXTERNAL_URL': advertisement.cta_url or '#',
        }
        
        redirect_to = redirect_map.get(action, '#')
        
        return JsonResponse({
            'success': True,
            'message': 'Click registrado',
            'redirect_to': redirect_to,
            'action': action
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_advertisement_positions(request):
    """
    Retorna las posiciones disponibles para anuncios.
    Útil para que el frontend sepa qué posiciones puede solicitar.
    
    Returns:
    {
        "positions": [
            {"value": "HERO_CAROUSEL", "label": "Hero Carousel (Home)"},
            {"value": "STICKY_FOOTER", "label": "Banner Inferior Fijo"},
            ...
        ]
    }
    """
    from .models import Advertisement
    
    positions = [
        {'value': choice[0], 'label': choice[1]}
        for choice in Advertisement.PositionType.choices
    ]
    
    return JsonResponse({'positions': positions})
