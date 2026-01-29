"""
Context processors para el portal público del cliente.
Proporciona variables automáticas en todas las plantillas del portal.
"""
from django.utils import timezone


def portal_advertisements(request):
    """
    Añade los anuncios activos al contexto de todas las páginas del portal.
    Los anuncios se filtran por el gym actual (basado en el slug de la URL).
    """
    # Solo procesar si estamos en una ruta del portal público
    path = request.path
    if not path.startswith('/public/gym/'):
        return {}
    
    # Extraer el slug del gym de la URL
    # URL pattern: /public/gym/<slug>/...
    try:
        parts = path.split('/')
        if len(parts) >= 4:
            slug = parts[3]  # /public/gym/<slug>/...
        else:
            return {}
    except Exception:
        return {}
    
    if not slug:
        return {}
    
    try:
        from django.db import models
        from marketing.models import Advertisement, Popup
        from organizations.models import Gym
        
        gym = Gym.objects.filter(slug=slug).first()
        if not gym:
            return {}
        
        now = timezone.now()
        
        # Obtener todos los anuncios activos del gym
        active_ads = Advertisement.objects.filter(
            is_active=True,
            target_gyms=gym,
            start_date__lte=now,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
        ).order_by('-priority', '-created_at')
        
        # Obtener popups activos del gym
        active_popups = Popup.objects.filter(
            is_active=True,
            gym=gym,
            start_date__lte=now,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
        ).order_by('-priority', '-created_at')
        
        # Función helper para filtrar por pantalla (compatible con SQLite)
        def filter_ads_by_screen(ads, screen_name):
            """Filtra anuncios por pantalla de destino (compatible con SQLite)."""
            result = []
            for ad in ads:
                screens = ad.target_screens or []
                if 'ALL' in screens or screen_name in screens:
                    result.append(ad)
            return result
        
        # Determinar la pantalla actual basándose en la URL
        current_screen = 'HOME'  # Por defecto
        if '/profile' in path:
            current_screen = 'PROFILE'
        elif '/bookings' in path or '/booking' in path:
            current_screen = 'BOOKINGS'
        elif '/schedule' in path or '/activities' in path:
            current_screen = 'CLASS_CATALOG'
        elif '/shop' in path or '/tienda' in path:
            current_screen = 'SHOP'
        elif '/checkin' in path:
            current_screen = 'CHECKIN'
        elif '/settings' in path or '/config' in path:
            current_screen = 'SETTINGS'
        
        # Filtrar anuncios para la pantalla actual
        screen_ads = filter_ads_by_screen(active_ads, current_screen)
        
        # Separar por posición
        hero_ads = [ad for ad in screen_ads if ad.position == 'HERO_CAROUSEL']
        footer_ad = next((ad for ad in screen_ads if ad.position == 'STICKY_FOOTER'), None)
        inline_ads = [ad for ad in screen_ads if ad.position == 'INLINE_MIDDLE']
        
        return {
            'portal_hero_ads': hero_ads,
            'portal_footer_ad': footer_ad,
            'portal_inline_ads': inline_ads,
            'portal_current_screen': current_screen,
            'portal_popups': list(active_popups),
        }
        
    except Exception as e:
        # En caso de error, no romper la página
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error cargando anuncios del portal: {e}")
        return {}
