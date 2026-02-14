from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Service
from .services import invalidate_service_cache

@receiver(post_save, sender=Service)
@receiver(post_delete, sender=Service)
def service_cache_invalidation(sender, instance, **kwargs):
    if instance.gym_id:
        invalidate_service_cache(instance.gym_id)
