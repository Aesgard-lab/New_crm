from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Campaign, EmailTemplate, Popup

@login_required
def dashboard_view(request):
    """
    Marketing Dashboard Overview.
    """
    gym = request.gym
    
    # Stats
    campaigns_count = Campaign.objects.filter(gym=gym).count()
    templates_count = EmailTemplate.objects.filter(gym=gym).count()
    active_popups = Popup.objects.filter(gym=gym, is_active=True).count()
    
    # Recent Campaigns
    recent_campaigns = Campaign.objects.filter(gym=gym).order_by('-created_at')[:5]

    context = {
        'title': 'Marketing',
        'stats': {
            'campaigns': campaigns_count,
            'templates': templates_count,
            'popups': active_popups,
        },
        'recent_campaigns': recent_campaigns
    }
    return render(request, 'backoffice/marketing/dashboard.html', context)

@login_required
def template_list_view(request):
    gym = request.gym
    templates = EmailTemplate.objects.filter(gym=gym).order_by('-updated_at')
    return render(request, 'backoffice/marketing/templates/list.html', {'templates': templates})

@login_required
def template_create_view(request):
    # Create an empty template and redirect to editor
    gym = request.gym
    template = EmailTemplate.objects.create(
        gym=gym,
        name="Nueva Plantilla",
        content_json={},
        content_html=""
    )
    from django.shortcuts import redirect
    return redirect('marketing_template_editor', pk=template.pk)

@login_required
def template_editor_view(request, pk):
    from django.shortcuts import get_object_or_404
    template = get_object_or_404(EmailTemplate, pk=pk, gym=request.gym)
    return render(request, 'backoffice/marketing/templates/editor.html', {'template': template})

@login_required
def template_save_api(request, pk):
    if request.method != 'POST':
        from django.http import JsonResponse
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    import json
    from django.shortcuts import get_object_or_404
    from django.http import JsonResponse
    
    try:
        data = json.loads(request.body)
        template = get_object_or_404(EmailTemplate, pk=pk, gym=request.gym)
        
        template.content_json = data.get('components', {}) # GrapesJS JSON
        template.content_html = data.get('html', '') # Compiled HTML
        
        # Optional: Generate thumbnail here using an external service or JS canvas upload
        
        template.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def campaign_list_view(request):
    gym = request.gym
    campaigns = Campaign.objects.filter(gym=gym).order_by('-created_at')
    return render(request, 'backoffice/marketing/campaigns/list.html', {'campaigns': campaigns})

@login_required
def campaign_create_view(request):
    """
    Renders the Campaign Wizard.
    """
    gym = request.gym
    templates = EmailTemplate.objects.filter(gym=gym)
    
    # We pass templates to context for selection in the wizard
    context = {
        'templates': templates,
    }
    return render(request, 'backoffice/marketing/campaigns/wizard.html', context)

@login_required
def campaign_create_api(request):
    if request.method != 'POST':
        from django.http import JsonResponse
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    import json
    from django.utils.dateparse import parse_datetime
    
    try:
        data = json.loads(request.body)
        gym = request.gym
        
        # 1. Basic Info
        name = data.get('name')
        subject = data.get('subject')
        audience_type = data.get('audience_type')
        scheduled_at_str = data.get('scheduled_at')
        
        # 2. Template
        template_id = data.get('template_id')
        
        if not name or not subject or not template_id:
             return JsonResponse({'error': 'Faltan datos obligatorios'}, status=400)

        template = EmailTemplate.objects.get(pk=template_id, gym=gym)
        
        # Create Campaign
        campaign = Campaign.objects.create(
            gym=gym,
            name=name,
            subject=subject,
            audience_type=audience_type,
            template=template,
            scheduled_at=parse_datetime(scheduled_at_str) if scheduled_at_str else timezone.now(),
            status=Campaign.Status.SCHEDULED if scheduled_at_str else Campaign.Status.DRAFT
        )
        
        return JsonResponse({'status': 'ok', 'campaign_id': campaign.id})
        
    except Exception as e:
        from django.http import JsonResponse
        return JsonResponse({'error': str(e)}, status=500)
@login_required
def template_delete_view(request, pk):
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    template = get_object_or_404(EmailTemplate, pk=pk, gym=request.gym)
    template.delete()
    messages.success(request, 'Plantilla eliminada correctamente.')
    return redirect('marketing_template_list')
@login_required
def marketing_settings_view(request):
    from .forms import MarketingSettingsForm
    from .models import MarketingSettings
    from django.contrib import messages
    
    # Get or Create settings for this gym
    settings, created = MarketingSettings.objects.get_or_create(gym=request.gym)
    
    if request.method == 'POST':
        form = MarketingSettingsForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración actualizada correctamente.')
            return redirect('marketing_settings')
    else:
        form = MarketingSettingsForm(instance=settings)
        
    return render(request, 'backoffice/marketing/settings.html', {'form': form})

# -- Popups --

@login_required
def popup_list_view(request):
    gym = request.gym
    popups = Popup.objects.filter(gym=gym).order_by('-created_at')
    return render(request, 'backoffice/marketing/popups/list.html', {'popups': popups})

@login_required
def popup_create_view(request):
    from .forms import PopupForm
    from django.contrib import messages
    if request.method == 'POST':
        form = PopupForm(request.POST, request.FILES)
        if form.is_valid():
            popup = form.save(commit=False)
            popup.gym = request.gym
            popup.save()
            messages.success(request, 'Popup creado correctamente.')
            return redirect('marketing_popup_list')
    else:
        form = PopupForm()
    return render(request, 'backoffice/marketing/popups/form.html', {'form': form, 'title': 'Nuevo Popup'})

@login_required
def popup_edit_view(request, pk):
    from .forms import PopupForm
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    popup = get_object_or_404(Popup, pk=pk, gym=request.gym)
    
    if request.method == 'POST':
        form = PopupForm(request.POST, request.FILES, instance=popup)
        if form.is_valid():
            form.save()
            messages.success(request, 'Popup actualizado.')
            return redirect('marketing_popup_list')
    else:
        form = PopupForm(instance=popup)
    return render(request, 'backoffice/marketing/popups/form.html', {'form': form, 'title': 'Editar Popup'})

@login_required
def popup_delete_view(request, pk):
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    popup = get_object_or_404(Popup, pk=pk, gym=request.gym)
    popup.delete()
    messages.success(request, 'Popup eliminado.')
    return redirect('marketing_popup_list')
