from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import GymSettingsForm

# Create your views here.

@login_required
def gym_settings_view(request):
    gym = request.gym
    
    if request.method == 'POST':
        form = GymSettingsForm(request.POST, request.FILES, instance=gym)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración del gimnasio actualizada.')
            return redirect('gym_settings')
    else:
        form = GymSettingsForm(instance=gym)
        
    return render(request, 'backoffice/settings/gym.html', {'form': form})
