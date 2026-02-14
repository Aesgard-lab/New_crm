from django.core.cache import cache
from .models import MembershipPlan

PLAN_CACHE_KEY = "gym_shop_plans_{}"

def get_cached_gym_plans(gym_id):
    """
    Returns a cached list of active membership plans for the shop.
    List of MembershipPlan objects.
    """
    key = PLAN_CACHE_KEY.format(gym_id)
    plans = cache.get(key)
    if plans is None:
        plans = list(MembershipPlan.objects.filter(
            gym_id=gym_id,
            is_active=True,
            is_visible_online=True
        ))
        cache.set(key, plans, timeout=86400) # 24 hours
    return plans

def invalidate_plan_cache(gym_id):
    key = PLAN_CACHE_KEY.format(gym_id)
    cache.delete(key)
