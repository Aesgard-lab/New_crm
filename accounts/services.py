from typing import Optional
from django.apps import apps
from django.contrib.auth import get_user_model

User = get_user_model()

def _GymMembership():
    return apps.get_model("accounts", "GymMembership")

def user_gym_ids(user: User):
    if not getattr(user, "is_authenticated", False):
        return []

    GymMembership = _GymMembership()

    if user.is_superuser:
        from organizations.models import Gym
        return list(Gym.objects.values_list("id", flat=True))

    # 1. Gyms via Membership (Clients/Admins)
    ids = set(GymMembership.objects.filter(user=user, is_active=True).values_list("gym_id", flat=True))
    
    # 2. Gyms via StaffProfile (Employees)
    if hasattr(user, "staff_profile"):
        # StaffProfile has a single 'gym' field, so we add its ID
        ids.add(user.staff_profile.gym_id)

    return list(ids)

def default_gym_id(user: User) -> Optional[int]:
    ids = user_gym_ids(user)
    return ids[0] if ids else None
