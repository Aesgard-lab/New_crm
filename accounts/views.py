from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    print(f"[DEBUG ACCOUNTS LOGIN] Request method: {request.method}")
    if request.method == "POST":
        print(f"[DEBUG ACCOUNTS LOGIN] POST data: {dict(request.POST)}")
        form = AuthenticationForm(request, data=request.POST)
        print(f"[DEBUG ACCOUNTS LOGIN] Form is_valid: {form.is_valid()}")
        if form.is_valid():
            user = form.get_user()
            print(f"[DEBUG ACCOUNTS LOGIN] User authenticated: {user.email}")
            login(request, user)
            return redirect("home")
        else:
            print(f"[DEBUG ACCOUNTS LOGIN] Form errors: {form.errors}")
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
