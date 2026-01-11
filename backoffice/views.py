from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from organizations.models import Gym
from accounts.services import user_gym_ids


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    error = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(request, username=email, password=password)  # username=email en tu User model
        if user is not None:
            login(request, user)
            return redirect("home")
        error = "Credenciales incorrectas"

    return render(request, "auth/login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def home(request):
    gym_id = request.session.get("current_gym_id")
    gym = Gym.objects.filter(id=gym_id).first()
    
    # Dashboard Stats
    from .dashboard_service import DashboardService
    dashboard = DashboardService(gym)
    stats = dashboard.get_kpi_stats()
    risk_clients = dashboard.get_risk_clients()
    top_clients = dashboard.get_top_clients()
    
    context = {
        "gym": gym,
        "stats": stats,
        "risk_clients": risk_clients,
        "top_clients": top_clients,
    }
    return render(request, "backoffice/dashboard.html", context)


@login_required
def whoami(request):
    gym_id = request.session.get("current_gym_id")
    gym = Gym.objects.filter(id=gym_id).first()
    return JsonResponse({
        "user": request.user.email,
        "current_gym_id": gym_id,
        "current_gym_name": gym.name if gym else None,
    })


@login_required
@require_POST
def select_gym(request):
    gym_id = request.POST.get("gym_id")
    try:
        gym_id_int = int(gym_id)
    except (TypeError, ValueError):
        return redirect("home")

    allowed_ids = set(user_gym_ids(request.user))
    if gym_id_int in allowed_ids:
        request.session["current_gym_id"] = gym_id_int

    return redirect("home")


from accounts.decorators import require_gym_permission

# clients_list movido a clients/views.py


@login_required
@require_gym_permission("staff.view")
def staff_page(request):
    return render(request, "backoffice/staff/list.html")


@login_required
@require_gym_permission("marketing.view")
def marketing_page(request):
    return render(request, "backoffice/marketing/list.html")
