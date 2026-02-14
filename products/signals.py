from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product
from .services import invalidate_product_cache

@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def product_cache_invalidation(sender, instance, **kwargs):
    if instance.gym_id:
        invalidate_product_cache(instance.gym_id)
