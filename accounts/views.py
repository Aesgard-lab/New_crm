from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("home")
    else:
        form = AuthenticationForm()
    return render(request, "auth/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def switch_gym(request, gym_id):
    """Switch the current gym in session"""
    from accounts.services import user_gym_ids
    available_ids = user_gym_ids(request.user)
    
    if int(gym_id) in available_ids:
        request.session["current_gym_id"] = int(gym_id)
    
    # Redirect back to where they came from, or home
    next_url = request.META.get('HTTP_REFERER', 'home')
    return redirect(next_url)
