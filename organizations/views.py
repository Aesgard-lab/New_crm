from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import translation
from .forms import GymSettingsForm
from .models import Gym, PublicPortalSettings

LANGUAGE_SESSION_KEY = 'django_language'

# Create your views here.

@login_required
def gym_settings_view(request):
    gym = request.gym
    
    if request.method == 'POST':
        form = GymSettingsForm(request.POST, request.FILES, instance=gym)
        if form.is_valid():
            gym_instance = form.save()
            
            # Activar el idioma seleccionado en la sesión del usuario
            if 'language' in form.changed_data:
                translation.activate(gym_instance.language)
                request.session[LANGUAGE_SESSION_KEY] = gym_instance.language
            
            messages.success(request, 'Configuración del gimnasio actualizada.')
            return redirect('gym_settings')
    else:
        form = GymSettingsForm(instance=gym)
        
    return render(request, 'backoffice/settings/gym.html', {'form': form})


@login_required
def widget_code_generator(request):
    """Vista para generar código del widget embebible"""
    gym = request.gym
    
    # Obtener configuración del portal público
    try:
        portal_settings = PublicPortalSettings.objects.get(gym=gym)
    except PublicPortalSettings.DoesNotExist:
        portal_settings = None
    
    # URL base (en producción debe ser el dominio real)
    base_url = request.build_absolute_uri('/').rstrip('/')
    
    # Obtener servicios, productos y cuotas del gimnasio
    from services.models import Service
    from products.models import Product
    from memberships.models import MembershipPlan
    
    services = Service.objects.filter(gym=gym, is_active=True).select_related('category')
    products = Product.objects.filter(gym=gym, is_active=True, is_visible_online=True).select_related('category')
    membership_plans = MembershipPlan.objects.filter(gym=gym, is_active=True)
    
    context = {
        'gym': gym,
        'portal_settings': portal_settings,
        'base_url': base_url,
        'services': services,
        'products': products,
        'membership_plans': membership_plans,
    }
    
    return render(request, 'organizations/widget_code.html', context)
