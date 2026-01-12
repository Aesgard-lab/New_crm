from django.shortcuts import redirect
from django.urls import reverse
from accounts.services import user_gym_ids, default_gym_id

EXEMPT_PATH_PREFIXES = (
    "/admin/",
    "/login/",
    "/logout/",
)

class CurrentGymMiddleware:
    """
    Asegura que, si el usuario tiene gyms, exista un current_gym_id válido en sesión.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""

        if path.startswith(EXEMPT_PATH_PREFIXES):
            return self.get_response(request)

        user = request.user
        if not user.is_authenticated:
            return self.get_response(request)

        gym_ids = user_gym_ids(user)
        if not gym_ids:
            return self.get_response(request)

        current_gym_id = request.session.get("current_gym_id")
        if current_gym_id not in gym_ids:
            current_gym_id = default_gym_id(user)
            request.session["current_gym_id"] = current_gym_id
            
        # Attach the actual Gym object to the request
        from organizations.models import Gym
        try:
            request.gym = Gym.objects.get(pk=current_gym_id)
        except Gym.DoesNotExist:
            request.gym = None

        return self.get_response(request)
