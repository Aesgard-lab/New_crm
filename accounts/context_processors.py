from accounts.permissions import user_has_gym_permission

def gym_permissions(request):
    if not request.user.is_authenticated:
        return {}

    gym_id = request.session.get("current_gym_id")
    if not gym_id:
        return {}

    
    # Obtener el gym para sacar su color
    from organizations.models import Gym
    from accounts.services import user_gym_ids
    
    gym = Gym.objects.filter(id=gym_id).first()
    brand_color = gym.brand_color if gym else "#0f172a"
    
    # Gyms available for switching
    my_gym_ids = user_gym_ids(request.user)
    my_gyms = Gym.objects.filter(id__in=my_gym_ids)

    return {
        "can_view_clients": user_has_gym_permission(request.user, gym_id, "clients.view"),
        "can_view_staff": user_has_gym_permission(request.user, gym_id, "staff.view"),
        "can_view_marketing": user_has_gym_permission(request.user, gym_id, "marketing.view"),
        "brand_color": brand_color,
        "current_gym": gym,
        "my_gyms": my_gyms,
    }
