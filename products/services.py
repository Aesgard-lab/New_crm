from django.core.cache import cache
from .models import Product

PRODUCT_CACHE_KEY = "gym_shop_products_{}"

def get_cached_gym_products(gym_id):
    """
    Returns a cached list of active products for the shop.
    List of dictionaries.
    """
    key = PRODUCT_CACHE_KEY.format(gym_id)
    products = cache.get(key)
    if products is None:
        products = list(Product.objects.filter(
            gym_id=gym_id,
            is_active=True,
            is_visible_online=True
        ).values('id', 'name', 'base_price', 'description', 'stock_quantity'))
        cache.set(key, products, timeout=86400) # 24 hours
    return products

def invalidate_product_cache(gym_id):
    key = PRODUCT_CACHE_KEY.format(gym_id)
    cache.delete(key)
