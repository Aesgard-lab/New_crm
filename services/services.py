from django.core.cache import cache
from .models import Service

SERVICE_CACHE_KEY = "gym_shop_services_{}"

def get_cached_gym_services(gym_id):
    """
    Returns a cached list of active services for the shop.
    List of Service objects.
    """
    key = SERVICE_CACHE_KEY.format(gym_id)
    services = cache.get(key)
    if services is None:
        services = list(Service.objects.filter(
            gym_id=gym_id,
            is_active=True,
            is_visible_online=True
        ))
        cache.set(key, services, timeout=86400) # 24 hours
    return services

def invalidate_service_cache(gym_id):
    key = SERVICE_CACHE_KEY.format(gym_id)
    cache.delete(key)
