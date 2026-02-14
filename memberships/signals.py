from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import MembershipPlan
from .services import invalidate_plan_cache

@receiver(post_save, sender=MembershipPlan)
@receiver(post_delete, sender=MembershipPlan)
def plan_cache_invalidation(sender, instance, **kwargs):
    if instance.gym_id:
        invalidate_plan_cache(instance.gym_id)
