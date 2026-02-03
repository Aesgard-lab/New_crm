from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_gym_permission
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
    
    # Advertisement stats
    from .models import Advertisement
    active_ads = Advertisement.objects.filter(gym=gym, is_active=True).count()
    
    # Recent Campaigns
    recent_campaigns = Campaign.objects.filter(gym=gym).order_by('-created_at')[:5]
    recent_popups = Popup.objects.filter(gym=gym).order_by('-created_at')[:5]

    context = {
        'title': 'Marketing',
        'stats': {
            'campaigns': campaigns_count,
            'templates': templates_count,
            'popups': active_popups,
            'ads': active_ads,
        },
        'recent_campaigns': recent_campaigns,
        'recent_popups': recent_popups
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
        
        # Update template name if provided
        if data.get('name'):
            template.name = data.get('name')
        
        template.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def template_update_name(request, pk):
    """API endpoint to update template name"""
    if request.method != 'POST':
        from django.http import JsonResponse
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    import json
    from django.shortcuts import get_object_or_404
    from django.http import JsonResponse
    
    try:
        data = json.loads(request.body)
        template = get_object_or_404(EmailTemplate, pk=pk, gym=request.gym)
        template.name = data.get('name', template.name)
        template.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
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
    from .models import SavedAudience
    
    gym = request.gym
    templates = EmailTemplate.objects.filter(gym=gym)
    saved_audiences = SavedAudience.objects.filter(gym=gym, is_active=True)
    
    # We pass templates to context for selection in the wizard
    context = {
        'templates': templates,
        'saved_audiences': saved_audiences,
    }
    return render(request, 'backoffice/marketing/campaigns/wizard.html', context)

@login_required
def campaign_create_api(request):
    if request.method != 'POST':
        from django.http import JsonResponse
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    import json
    from django.utils.dateparse import parse_datetime
    from .models import SavedAudience
    
    try:
        data = json.loads(request.body)
        gym = request.gym
        
        # 1. Basic Info
        name = data.get('name')
        subject = data.get('subject')
        audience_type = data.get('audience_type')
        scheduled_at_str = data.get('scheduled_at')
        saved_audience_id = data.get('saved_audience_id')
        
        # 2. Template
        template_id = data.get('template_id')
        
        if not name or not subject or not template_id:
             return JsonResponse({'error': 'Faltan datos obligatorios'}, status=400)

        template = EmailTemplate.objects.get(pk=template_id, gym=gym)
        
        # Obtener audiencia guardada si aplica
        saved_audience = None
        if audience_type == 'SAVED_AUDIENCE' and saved_audience_id:
            saved_audience = SavedAudience.objects.filter(pk=saved_audience_id, gym=gym).first()
        
        # Create Campaign
        campaign = Campaign.objects.create(
            gym=gym,
            name=name,
            subject=subject,
            audience_type=audience_type,
            saved_audience=saved_audience,
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
    """Vista de configuración de marketing - muestra datos SMTP del gimnasio"""
    return render(request, 'backoffice/marketing/settings.html')


@login_required
def test_smtp_email_view(request):
    """Enviar email de prueba usando la configuración SMTP del gimnasio"""
    from django.contrib import messages
    from organizations.email_utils import send_gym_email
    
    if request.method == 'POST':
        test_email = request.POST.get('test_email')
        gym = request.gym
        
        if not gym.smtp_host:
            messages.error(request, 'No hay configuración SMTP. Configúrala en Ajustes del Gimnasio.')
            return redirect('marketing_settings')
        
        try:
            sender_name = gym.commercial_name or gym.name
            base_url = request.build_absolute_uri('/').rstrip('/')
            
            # Enviar email de prueba (incluye firma con logo y footer automáticamente)
            result = send_gym_email(
                gym=gym,
                subject=f'✅ Email de prueba desde {sender_name}',
                body=f'''¡Hola!

Este es un email de prueba enviado desde {sender_name}.

Si recibes este mensaje, la configuración SMTP está funcionando correctamente.

Detalles de la configuración:
• Servidor: {gym.smtp_host}
• Puerto: {gym.smtp_port}
• TLS: {"Sí" if gym.smtp_use_tls else "No"}
• SSL: {"Sí" if gym.smtp_use_ssl else "No"}''',
                to_emails=test_email,
                base_url=base_url
            )
            
            if result:
                messages.success(request, f'✅ Email de prueba enviado correctamente a {test_email}')
            else:
                messages.error(request, '❌ No se pudo enviar el email')
        except Exception as e:
            messages.error(request, f'❌ Error al enviar: {str(e)}')
    
    return redirect('marketing_settings')


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
    from django.utils import timezone
    
    if request.method == 'POST':
        form = PopupForm(request.POST, request.FILES, gym=request.gym)
        if form.is_valid():
            popup = form.save(commit=False)
            popup.gym = request.gym
            
            # Handle Send Now
            if request.POST.get('send_now') == 'on' or request.POST.get('send_now') == 'true':
                popup.start_date = timezone.now()
                popup.is_active = True
            
            popup.save()
            messages.success(request, 'Popup creado correctamente.')
            return redirect('marketing_popup_list')
    else:
        form = PopupForm(gym=request.gym)
    return render(request, 'backoffice/marketing/popups/form.html', {'form': form, 'title': 'Nuevo Popup'})

@login_required
def popup_edit_view(request, pk):
    from .forms import PopupForm
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    from django.utils import timezone
    
    popup = get_object_or_404(Popup, pk=pk, gym=request.gym)
    
    if request.method == 'POST':
        form = PopupForm(request.POST, request.FILES, instance=popup, gym=request.gym)
        if form.is_valid():
            popup_obj = form.save(commit=False)
            
            # Handle Send Now update
            if request.POST.get('send_now') == 'on':
                popup_obj.start_date = timezone.now()
                popup_obj.is_active = True
                
            popup_obj.save()
            messages.success(request, 'Popup actualizado.')
            return redirect('marketing_popup_list')
    else:
        form = PopupForm(instance=popup, gym=request.gym)
    return render(request, 'backoffice/marketing/popups/form.html', {'form': form, 'title': 'Editar Popup'})

@login_required
def popup_delete_view(request, pk):
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    popup = get_object_or_404(Popup, pk=pk, gym=request.gym)
    popup.delete()
    messages.success(request, 'Popup eliminado.')
    return redirect('marketing_popup_list')


# =============================================================================
# ADVERTISEMENTS / BANNERS VIEWS
# =============================================================================

@login_required
def advertisement_list_view(request):
    """
    Lista de todos los anuncios publicitarios del gimnasio
    """
    from .models import Advertisement
    
    gym = request.gym
    advertisements = Advertisement.objects.filter(gym=gym).order_by('priority', '-created_at')
    
    # Stats
    total_ads = advertisements.count()
    active_ads = advertisements.filter(is_active=True).count()
    total_impressions = sum(ad.impressions for ad in advertisements)
    total_clicks = sum(ad.clicks for ad in advertisements)
    avg_ctr = round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2)
    
    context = {
        'advertisements': advertisements,
        'stats': {
            'total': total_ads,
            'active': active_ads,
            'impressions': total_impressions,
            'clicks': total_clicks,
            'ctr': avg_ctr,
        }
    }
    return render(request, 'backoffice/marketing/advertisements/list.html', context)


@login_required
def advertisement_create_view(request):
    """
    Crear nuevo anuncio publicitario
    """
    from .forms import AdvertisementForm
    from django.contrib import messages
    from django.utils import timezone
    
    if request.method == 'POST':
        form = AdvertisementForm(request.POST, request.FILES, user=request.user, gym=request.gym)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.gym = request.gym
            ad.created_by = request.user
            
            # Si marca "Activar Ahora"
            if request.POST.get('activate_now') == 'on':
                ad.start_date = timezone.now()
                ad.is_active = True
            
            ad.save()
            form.save_m2m()  # Para ManyToMany (target_gyms)
            
            messages.success(request, f'Anuncio "{ad.title}" creado correctamente.')
            return redirect('marketing_advertisement_list')
    else:
        form = AdvertisementForm(user=request.user, gym=request.gym)
    
    return render(request, 'backoffice/marketing/advertisements/form.html', {
        'form': form,
        'title': 'Crear Anuncio Publicitario',
        'is_create': True
    })


@login_required
def advertisement_edit_view(request, pk):
    """
    Editar anuncio publicitario existente
    """
    from .models import Advertisement
    from .forms import AdvertisementForm
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    
    ad = get_object_or_404(Advertisement, pk=pk, gym=request.gym)
    
    if request.method == 'POST':
        form = AdvertisementForm(request.POST, request.FILES, instance=ad, user=request.user, gym=request.gym)
        if form.is_valid():
            ad_obj = form.save(commit=False)
            
            # Handle Activate Now
            if request.POST.get('activate_now') == 'on':
                from django.utils import timezone
                ad_obj.start_date = timezone.now()
                ad_obj.is_active = True
            
            ad_obj.save()
            form.save_m2m()
            
            messages.success(request, f'Anuncio "{ad_obj.title}" actualizado.')
            return redirect('marketing_advertisement_list')
    else:
        form = AdvertisementForm(instance=ad, user=request.user, gym=request.gym)
    
    return render(request, 'backoffice/marketing/advertisements/form.html', {
        'form': form,
        'title': 'Editar Anuncio',
        'is_create': False,
        'advertisement': ad
    })


@login_required
def advertisement_delete_view(request, pk):
    """
    Eliminar anuncio publicitario
    """
    from .models import Advertisement
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    
    ad = get_object_or_404(Advertisement, pk=pk, gym=request.gym)
    title = ad.title
    ad.delete()
    
    messages.success(request, f'Anuncio "{title}" eliminado correctamente.')
    return redirect('marketing_advertisement_list')


@login_required
def advertisement_toggle_status_view(request, pk):
    """
    Activar/desactivar anuncio rápidamente
    """
    from .models import Advertisement
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from django.http import JsonResponse
    
    ad = get_object_or_404(Advertisement, pk=pk, gym=request.gym)
    ad.is_active = not ad.is_active
    ad.save()
    
    status_text = "activado" if ad.is_active else "desactivado"
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_active': ad.is_active,
            'message': f'Anuncio {status_text}'
        })
    
    messages.success(request, f'Anuncio {status_text}.')
    return redirect('marketing_advertisement_list')


# =============================================================================
# LEAD MANAGEMENT VIEWS
# =============================================================================

@login_required
def lead_board_view(request):
    """
    Kanban board view for lead management.
    """
    from .models import LeadPipeline, LeadStage, LeadCard
    from staff.models import StaffProfile
    
    gym = request.gym
    
    # Get the active pipeline or first available
    pipeline = LeadPipeline.objects.filter(gym=gym, is_active=True).first()
    
    if not pipeline:
        # Create a default pipeline with stages
        pipeline = LeadPipeline.objects.create(gym=gym, name="Sales Pipeline", is_active=True)
        default_stages = [
            {'name': 'Nuevo Lead', 'order': 0, 'color': '#6366f1'},
            {'name': 'Contactado', 'order': 1, 'color': '#f59e0b'},
            {'name': 'En Prueba', 'order': 2, 'color': '#10b981'},
            {'name': 'Convertido', 'order': 3, 'color': '#22c55e', 'is_won': True},
            {'name': 'Perdido', 'order': 4, 'color': '#ef4444', 'is_lost': True},
        ]
        for stage_data in default_stages:
            LeadStage.objects.create(pipeline=pipeline, **stage_data)
    
    # Get stages with their cards
    stages = pipeline.stages.prefetch_related(
        'lead_cards__client',
        'lead_cards__assigned_to'
    ).all()
    
    # Filters
    assigned_filter = request.GET.get('assigned')
    source_filter = request.GET.get('source')
    
    # Staff for filter dropdown
    staff_list = StaffProfile.objects.filter(gym=gym)
    
    context = {
        'pipeline': pipeline,
        'stages': stages,
        'staff_list': staff_list,
        'source_choices': LeadCard.Source.choices,
        'filters': {
            'assigned': assigned_filter,
            'source': source_filter,
        }
    }
    return render(request, 'backoffice/marketing/leads/board.html', context)


@login_required
def lead_settings_view(request):
    """
    Pipeline and automation settings.
    """
    from .models import LeadPipeline, LeadStage, LeadStageAutomation
    from services.models import Service
    from memberships.models import MembershipPlan
    from django.contrib import messages
    
    gym = request.gym
    pipeline = LeadPipeline.objects.filter(gym=gym, is_active=True).first()
    
    if not pipeline:
        messages.warning(request, 'No hay pipeline activo. Ve al tablero para crear uno.')
        return redirect('lead_board')
    
    stages = pipeline.stages.prefetch_related('required_services', 'required_plans').all()
    automations = LeadStageAutomation.objects.filter(
        from_stage__pipeline=pipeline
    ).select_related('from_stage', 'to_stage').order_by('priority', 'created_at')
    
    # Servicios y planes disponibles para asignar
    services = Service.objects.filter(gym=gym, is_active=True)
    plans = MembershipPlan.objects.filter(gym=gym, is_active=True)
    
    context = {
        'pipeline': pipeline,
        'stages': stages,
        'automations': automations,
        'trigger_choices': LeadStageAutomation.TriggerType.choices,
        'services': services,
        'plans': plans,
    }
    return render(request, 'backoffice/marketing/leads/settings.html', context)


@login_required
def lead_stage_create(request):
    """Create a new pipeline stage."""
    from .models import LeadPipeline, LeadStage
    from django.http import JsonResponse
    import json
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    gym = request.gym
    pipeline = LeadPipeline.objects.filter(gym=gym, is_active=True).first()
    
    if not pipeline:
        return JsonResponse({'error': 'No pipeline found'}, status=404)
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        color = data.get('color', '#6366f1')
        description = data.get('description', '')
        
        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)
        
        # Get max order
        max_order = pipeline.stages.aggregate(models.Max('order'))['order__max'] or 0
        
        stage = LeadStage.objects.create(
            pipeline=pipeline,
            name=name,
            color=color,
            description=description,
            order=max_order + 1
        )
        
        return JsonResponse({
            'success': True,
            'stage': {
                'id': stage.id,
                'name': stage.name,
                'color': stage.color,
                'order': stage.order
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def lead_stage_update(request, stage_id):
    """Update a pipeline stage."""
    from .models import LeadStage
    from services.models import Service
    from memberships.models import MembershipPlan
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    import json
    
    stage = get_object_or_404(LeadStage, id=stage_id, pipeline__gym=request.gym)
    
    if request.method == 'GET':
        # Return stage data for editing
        return JsonResponse({
            'id': stage.id,
            'name': stage.name,
            'description': stage.description,
            'color': stage.color,
            'monthly_quota': stage.monthly_quota,
            'is_won': stage.is_won,
            'is_lost': stage.is_lost,
            'required_services': list(stage.required_services.values_list('id', flat=True)),
            'required_plans': list(stage.required_plans.values_list('id', flat=True)),
        })
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        stage.name = data.get('name', stage.name)
        stage.description = data.get('description', '')
        stage.color = data.get('color', stage.color)
        stage.monthly_quota = data.get('monthly_quota', 0)
        stage.is_won = data.get('is_won', False)
        stage.is_lost = data.get('is_lost', False)
        stage.save()
        
        # Update services and plans
        service_ids = data.get('required_services', [])
        plan_ids = data.get('required_plans', [])
        
        stage.required_services.set(
            Service.objects.filter(id__in=service_ids, gym=request.gym)
        )
        stage.required_plans.set(
            MembershipPlan.objects.filter(id__in=plan_ids, gym=request.gym)
        )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def lead_stage_delete(request, stage_id):
    """Delete a pipeline stage."""
    from .models import LeadStage
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    stage = get_object_or_404(LeadStage, id=stage_id, pipeline__gym=request.gym)
    
    # Check if stage has leads
    if stage.lead_cards.exists():
        return JsonResponse({
            'error': 'No se puede eliminar una etapa que tiene leads. Mueve los leads primero.'
        }, status=400)
    
    stage.delete()
    return JsonResponse({'success': True})


@login_required
def lead_stage_reorder(request):
    """Reorder pipeline stages."""
    from .models import LeadStage, LeadPipeline
    from django.http import JsonResponse
    import json
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        stage_order = data.get('order', [])  # List of stage IDs in new order
        
        pipeline = LeadPipeline.objects.filter(gym=request.gym, is_active=True).first()
        if not pipeline:
            return JsonResponse({'error': 'No pipeline found'}, status=404)
        
        for index, stage_id in enumerate(stage_order):
            LeadStage.objects.filter(
                id=stage_id, 
                pipeline=pipeline
            ).update(order=index)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==========================================
# LEAD STAGE AUTOMATION CRUD
# ==========================================

@login_required
def lead_automation_create(request):
    """Create a new automation rule for the pipeline."""
    from .models import LeadStageAutomation, LeadStage, LeadPipeline
    from django.http import JsonResponse
    import json
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    gym = request.gym
    pipeline = LeadPipeline.objects.filter(gym=gym, is_active=True).first()
    
    if not pipeline:
        return JsonResponse({'error': 'No pipeline found'}, status=404)
    
    try:
        data = json.loads(request.body)
        
        from_stage = LeadStage.objects.get(id=data['from_stage'], pipeline=pipeline)
        to_stage = None
        if data.get('to_stage'):
            to_stage = LeadStage.objects.get(id=data['to_stage'], pipeline=pipeline)
        
        rule = LeadStageAutomation.objects.create(
            name=data.get('name', ''),
            from_stage=from_stage,
            to_stage=to_stage,
            trigger_type=data['trigger_type'],
            trigger_days=data.get('trigger_days'),
            action_type=data.get('action_type', 'MOVE_STAGE'),
            notify_message=data.get('notify_message', ''),
            priority=data.get('priority', 0),
            is_active=data.get('is_active', True)
        )
        
        return JsonResponse({'success': True, 'id': rule.id})
    except LeadStage.DoesNotExist:
        return JsonResponse({'error': 'Stage not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def lead_automation_detail(request, rule_id):
    """Get or update an automation rule."""
    from .models import LeadStageAutomation, LeadStage, LeadPipeline
    from django.http import JsonResponse
    import json
    
    gym = request.gym
    pipeline = LeadPipeline.objects.filter(gym=gym, is_active=True).first()
    
    if not pipeline:
        return JsonResponse({'error': 'No pipeline found'}, status=404)
    
    try:
        rule = LeadStageAutomation.objects.get(
            id=rule_id,
            from_stage__pipeline=pipeline
        )
    except LeadStageAutomation.DoesNotExist:
        return JsonResponse({'error': 'Rule not found'}, status=404)
    
    if request.method == 'GET':
        return JsonResponse({
            'id': rule.id,
            'name': rule.name,
            'from_stage': rule.from_stage_id,
            'to_stage': rule.to_stage_id,
            'trigger_type': rule.trigger_type,
            'trigger_days': rule.trigger_days,
            'action_type': rule.action_type,
            'notify_message': rule.notify_message,
            'priority': rule.priority,
            'is_active': rule.is_active
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            from_stage = LeadStage.objects.get(id=data['from_stage'], pipeline=pipeline)
            to_stage = None
            if data.get('to_stage'):
                to_stage = LeadStage.objects.get(id=data['to_stage'], pipeline=pipeline)
            
            rule.name = data.get('name', rule.name)
            rule.from_stage = from_stage
            rule.to_stage = to_stage
            rule.trigger_type = data['trigger_type']
            rule.trigger_days = data.get('trigger_days')
            rule.action_type = data.get('action_type', 'MOVE_STAGE')
            rule.notify_message = data.get('notify_message', '')
            rule.priority = data.get('priority', 0)
            rule.is_active = data.get('is_active', True)
            rule.save()
            
            return JsonResponse({'success': True})
        except LeadStage.DoesNotExist:
            return JsonResponse({'error': 'Stage not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def lead_automation_toggle(request, rule_id):
    """Toggle an automation rule active/inactive."""
    from .models import LeadStageAutomation, LeadPipeline
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    gym = request.gym
    pipeline = LeadPipeline.objects.filter(gym=gym, is_active=True).first()
    
    if not pipeline:
        return JsonResponse({'error': 'No pipeline found'}, status=404)
    
    try:
        rule = LeadStageAutomation.objects.get(
            id=rule_id,
            from_stage__pipeline=pipeline
        )
        rule.is_active = not rule.is_active
        rule.save()
        
        return JsonResponse({'success': True, 'is_active': rule.is_active})
    except LeadStageAutomation.DoesNotExist:
        return JsonResponse({'error': 'Rule not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def lead_automation_delete(request, rule_id):
    """Delete an automation rule."""
    from .models import LeadStageAutomation, LeadPipeline
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    gym = request.gym
    pipeline = LeadPipeline.objects.filter(gym=gym, is_active=True).first()
    
    if not pipeline:
        return JsonResponse({'error': 'No pipeline found'}, status=404)
    
    try:
        rule = LeadStageAutomation.objects.get(
            id=rule_id,
            from_stage__pipeline=pipeline
        )
        rule.delete()
        
        return JsonResponse({'success': True})
    except LeadStageAutomation.DoesNotExist:
        return JsonResponse({'error': 'Rule not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def lead_card_move_api(request, card_id):
    """
    API endpoint for drag & drop card movement.
    Records history for funnel analytics.
    """
    from django.http import JsonResponse
    from .models import LeadCard, LeadStage, LeadStageHistory
    from django.utils import timezone
    import json
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        new_stage_id = data.get('stage_id')
        
        card = LeadCard.objects.select_related('client', 'stage').get(
            id=card_id,
            client__gym=request.gym
        )
        old_stage = card.stage
        old_stage_updated_at = card.updated_at
        
        new_stage = LeadStage.objects.get(
            id=new_stage_id,
            pipeline__gym=request.gym
        )
        
        # Only create history if stage actually changed
        if old_stage != new_stage:
            # Calculate time in previous stage
            time_in_stage = None
            if old_stage and old_stage_updated_at:
                time_in_stage = timezone.now() - old_stage_updated_at
            
            # Get staff profile for the user making the change
            staff_profile = None
            if hasattr(request.user, 'staff_profile'):
                staff_profile = request.user.staff_profile
            
            # Record the movement in history
            LeadStageHistory.objects.create(
                lead_card=card,
                from_stage=old_stage,
                to_stage=new_stage,
                changed_by=staff_profile,
                time_in_previous_stage=time_in_stage,
                notes=f"Movido manualmente desde {old_stage.name if old_stage else 'N/A'} a {new_stage.name}"
            )
        
        card.stage = new_stage
        card.save()
        
        # If moved to "won" stage, convert client to active
        if new_stage.is_won and card.client.status == 'LEAD':
            card.client.status = 'ACTIVE'
            card.client.save()
        
        # If moved to "lost" stage, mark client as inactive
        if new_stage.is_lost and card.client.status == 'LEAD':
            card.client.status = 'INACTIVE'
            card.client.save()
        
        return JsonResponse({
            'status': 'ok',
            'card_id': card.id,
            'old_stage': old_stage.name if old_stage else None,
            'new_stage': new_stage.name
        })
        
    except LeadCard.DoesNotExist:
        return JsonResponse({'error': 'Card not found'}, status=404)
    except LeadStage.DoesNotExist:
        return JsonResponse({'error': 'Stage not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def lead_card_detail_api(request, card_id):
    """
    API endpoint for getting/updating card details.
    """
    from django.http import JsonResponse
    from .models import LeadCard, LeadStageHistory
    import json
    
    try:
        card = LeadCard.objects.select_related('client', 'stage', 'assigned_to').get(
            id=card_id,
            client__gym=request.gym
        )
        
        if request.method == 'GET':
            # Get stage history
            stage_history = LeadStageHistory.objects.filter(
                lead_card=card
            ).select_related(
                'from_stage', 'to_stage', 'changed_by', 'changed_by_automation'
            ).order_by('-changed_at')[:10]
            
            history_data = []
            for h in stage_history:
                history_data.append({
                    'date': h.changed_at.isoformat(),
                    'from_stage': h.from_stage.name if h.from_stage else 'Nuevo',
                    'to_stage': h.to_stage.name if h.to_stage else '-',
                    'changed_by': h.changed_by.user.get_full_name() if h.changed_by else None,
                    'automation': h.changed_by_automation.name if h.changed_by_automation else None,
                    'time_in_stage': str(h.time_in_previous_stage) if h.time_in_previous_stage else None,
                    'notes': h.notes,
                })
            
            return JsonResponse({
                'id': card.id,
                'client': {
                    'id': card.client.id,
                    'name': f"{card.client.first_name} {card.client.last_name}",
                    'email': card.client.email,
                    'phone': card.client.phone_number,
                },
                'stage': card.stage.name if card.stage else None,
                'assigned_to': card.assigned_to.user.get_full_name() if card.assigned_to else None,
                'source': card.source,
                'notes': card.notes,
                'next_followup': card.next_followup.isoformat() if card.next_followup else None,
                'stage_history': history_data,
            })
        
        elif request.method == 'POST':
            data = json.loads(request.body)
            
            if 'notes' in data:
                card.notes = data['notes']
            if 'source' in data:
                card.source = data['source']
            if 'assigned_to' in data:
                from staff.models import StaffProfile
                if data['assigned_to']:
                    card.assigned_to = StaffProfile.objects.get(id=data['assigned_to'])
                else:
                    card.assigned_to = None
            if 'next_followup' in data:
                from django.utils.dateparse import parse_datetime
                card.next_followup = parse_datetime(data['next_followup']) if data['next_followup'] else None
            
            card.save()
            return JsonResponse({'status': 'ok'})
        
    except LeadCard.DoesNotExist:
        return JsonResponse({'error': 'Card not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# =============================================================================
# AUTOMATIZACIONES AVANZADAS
# =============================================================================

@login_required
@require_gym_permission("marketing.view")
def automation_dashboard(request):
    """
    Panel principal de automatizaciones con resumen.
    """
    from .models import (
        EmailWorkflow, EmailWorkflowExecution,
        LeadScoringRule, LeadScore, RetentionAlert
    )
    
    gym = request.gym
    
    # Stats
    active_workflows = EmailWorkflow.objects.filter(gym=gym, is_active=True).count()
    active_executions = EmailWorkflowExecution.objects.filter(
        workflow__gym=gym, status='ACTIVE'
    ).count()
    
    scoring_rules = LeadScoringRule.objects.filter(gym=gym, is_active=True).count()
    total_scores = LeadScore.objects.filter(client__gym=gym).count()
    
    open_alerts = RetentionAlert.objects.filter(gym=gym, status='OPEN').count()
    high_risk_alerts = RetentionAlert.objects.filter(
        gym=gym, status='OPEN', risk_score__gte=70
    ).count()
    
    context = {
        'title': 'Automatizaciones',
        'workflows': {
            'active': active_workflows,
            'running': active_executions,
        },
        'scoring': {
            'rules': scoring_rules,
            'total_leads': total_scores,
        },
        'retention': {
            'open': open_alerts,
            'high_risk': high_risk_alerts,
        }
    }
    return render(request, 'backoffice/marketing/automation/dashboard.html', context)


# =============================================================================
# EMAIL WORKFLOWS
# =============================================================================

@login_required
@require_gym_permission("marketing.view")
def workflow_list(request):
    """Lista de workflows de email."""
    from .models import EmailWorkflow
    
    gym = request.gym
    workflows = EmailWorkflow.objects.filter(gym=gym).prefetch_related('steps').order_by('-created_at')
    
    context = {
        'workflows': workflows,
        'title': 'Secuencias de Email'
    }
    return render(request, 'backoffice/marketing/automation/workflow_list.html', context)


@login_required
@require_gym_permission("marketing.view")
def workflow_detail(request, pk):
    """Detalle y edición de workflow."""
    from .models import EmailWorkflow, EmailWorkflowExecution
    from django.shortcuts import get_object_or_404
    
    gym = request.gym
    workflow = get_object_or_404(EmailWorkflow, pk=pk, gym=gym)
    
    steps = workflow.steps.all().order_by('order')
    executions = workflow.executions.select_related('client').order_by('-started_at')[:20]
    
    # Stats
    total_executions = workflow.executions.count()
    active_executions = workflow.executions.filter(status='ACTIVE').count()
    completed_executions = workflow.executions.filter(status='COMPLETED').count()
    
    context = {
        'workflow': workflow,
        'steps': steps,
        'executions': executions,
        'stats': {
            'total': total_executions,
            'active': active_executions,
            'completed': completed_executions,
        },
        'title': workflow.name
    }
    return render(request, 'backoffice/marketing/automation/workflow_detail.html', context)


# =============================================================================
# LEAD SCORING
# =============================================================================

@login_required
@require_gym_permission("marketing.view")
def scoring_dashboard(request):
    """Dashboard de lead scoring."""
    from .models import LeadScoringRule, LeadScore, LeadScoringAutomation
    from django.db.models import Avg, Max, Min
    
    gym = request.gym
    
    rules = LeadScoringRule.objects.filter(gym=gym).order_by('-created_at')
    automations = LeadScoringAutomation.objects.filter(gym=gym, is_active=True).order_by('min_score')
    
    # Top scores
    top_scores = LeadScore.objects.filter(
        client__gym=gym,
        client__status='LEAD'
    ).select_related('client').order_by('-score')[:20]
    
    # Stats
    score_stats = LeadScore.objects.filter(client__gym=gym).aggregate(
        avg=Avg('score'),
        max=Max('score'),
        min=Min('score')
    )
    
    context = {
        'rules': rules,
        'automations': automations,
        'top_scores': top_scores,
        'stats': score_stats,
        'title': 'Lead Scoring'
    }
    return render(request, 'backoffice/marketing/automation/scoring_dashboard.html', context)


# =============================================================================
# ALERTAS DE RETENCIÓN
# =============================================================================

@login_required
@require_gym_permission("marketing.view")
def retention_alerts_list(request):
    """Lista de alertas de retención."""
    from .models import RetentionAlert
    from django.db.models import Q
    
    gym = request.gym
    
    # Filters
    status_filter = request.GET.get('status', 'OPEN')
    alert_type_filter = request.GET.get('type')
    assigned_filter = request.GET.get('assigned')
    
    alerts = RetentionAlert.objects.filter(gym=gym)
    
    if status_filter and status_filter != 'ALL':
        alerts = alerts.filter(status=status_filter)
    
    if alert_type_filter:
        alerts = alerts.filter(alert_type=alert_type_filter)
    
    if assigned_filter:
        if assigned_filter == 'me':
            alerts = alerts.filter(assigned_to__user=request.user)
        elif assigned_filter == 'unassigned':
            alerts = alerts.filter(assigned_to__isnull=True)
    
    alerts = alerts.select_related('client', 'assigned_to').order_by('-risk_score', '-created_at')
    
    # Stats
    stats = {
        'total': RetentionAlert.objects.filter(gym=gym, status='OPEN').count(),
        'high_risk': RetentionAlert.objects.filter(gym=gym, status='OPEN', risk_score__gte=70).count(),
        'unassigned': RetentionAlert.objects.filter(gym=gym, status='OPEN', assigned_to__isnull=True).count(),
    }
    
    context = {
        'alerts': alerts,
        'stats': stats,
        'status_choices': RetentionAlert.Status.choices,
        'type_choices': RetentionAlert.AlertType.choices,
        'current_filters': {
            'status': status_filter,
            'type': alert_type_filter,
            'assigned': assigned_filter,
        },
        'title': 'Alertas de Retención'
    }
    return render(request, 'backoffice/marketing/automation/retention_alerts.html', context)


@login_required
@require_gym_permission("marketing.edit")
def retention_alert_resolve(request, pk):
    """Resolver/actualizar una alerta de retención."""
    from .models import RetentionAlert
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    from django.utils import timezone
    import json
    
    gym = request.gym
    alert = get_object_or_404(RetentionAlert, pk=pk, gym=gym)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'resolve':
            alert.status = 'RESOLVED'
            alert.resolved_at = timezone.now()
            alert.notes = data.get('notes', '')
            alert.save()
            return JsonResponse({'status': 'ok', 'message': 'Alerta resuelta'})
        
        elif action == 'dismiss':
            alert.status = 'DISMISSED'
            alert.save()
            return JsonResponse({'status': 'ok', 'message': 'Alerta descartada'})
        
        elif action == 'assign':
            from staff.models import StaffProfile
            staff_id = data.get('staff_id')
            if staff_id:
                alert.assigned_to = StaffProfile.objects.get(id=staff_id, gym=gym)
                alert.status = 'IN_PROGRESS'
                alert.save()
                return JsonResponse({'status': 'ok', 'message': 'Alerta asignada'})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


# =============================================================================
# CREAR NUEVAS AUTOMATIZACIONES
# =============================================================================

@login_required
@require_gym_permission("marketing.edit")
def workflow_create(request):
    """Crear nuevo workflow de email."""
    from .models import EmailWorkflow, EmailWorkflowStep
    from django.contrib import messages
    
    gym = request.gym
    
    if request.method == 'POST':
        name = request.POST.get('name')
        trigger_event = request.POST.get('trigger_event')
        description = request.POST.get('description', '')
        
        workflow = EmailWorkflow.objects.create(
            gym=gym,
            name=name,
            trigger_event=trigger_event,
            description=description,
            is_active=False
        )
        
        messages.success(request, f'Workflow "{name}" creado correctamente')
        return redirect('workflow_detail', pk=workflow.pk)
    
    context = {
        'title': 'Crear Workflow',
        'trigger_choices': EmailWorkflow.TriggerEvent.choices,
    }
    return render(request, 'backoffice/marketing/automation/workflow_create.html', context)


@login_required
@require_gym_permission("marketing.edit")
def scoring_rule_create(request):
    """Crear nueva regla de lead scoring."""
    from .models import LeadScoringRule
    from django.contrib import messages
    
    gym = request.gym
    
    if request.method == 'POST':
        name = request.POST.get('name')
        event_type = request.POST.get('event_type')
        points = int(request.POST.get('points', 0))
        description = request.POST.get('description', '')
        
        rule = LeadScoringRule.objects.create(
            gym=gym,
            name=name,
            event_type=event_type,
            points=points,
            description=description,
            is_active=True
        )
        
        messages.success(request, f'Regla "{name}" creada correctamente')
        return redirect('scoring_dashboard')
    
    context = {
        'title': 'Crear Regla de Scoring',
        'event_choices': LeadScoringRule.EventType.choices,
    }
    return render(request, 'backoffice/marketing/automation/scoring_rule_create.html', context)


@login_required
@require_gym_permission("marketing.edit")
def retention_rule_create(request):
    """Crear nueva regla de retención."""
    from .models import RetentionRule, RetentionAlert
    from staff.models import StaffProfile
    from django.contrib import messages
    
    gym = request.gym
    
    if request.method == 'POST':
        name = request.POST.get('name')
        alert_type = request.POST.get('alert_type')
        days_threshold = int(request.POST.get('days_threshold', 14))
        risk_score = int(request.POST.get('risk_score', 50))
        auto_assign = request.POST.get('auto_assign') == 'on'
        assigned_staff_id = request.POST.get('assigned_staff')
        send_notification = request.POST.get('send_notification') == 'on'
        
        rule = RetentionRule.objects.create(
            gym=gym,
            name=name,
            alert_type=alert_type,
            days_threshold=days_threshold,
            risk_score=risk_score,
            auto_assign_to_staff=auto_assign,
            assigned_staff_id=assigned_staff_id if assigned_staff_id else None,
            send_notification=send_notification,
            is_active=True
        )
        
        messages.success(request, f'Regla "{name}" creada correctamente')
        return redirect('retention_alerts_list')
    
    # Get staff list for selection
    staff_list = StaffProfile.objects.filter(gym=gym, user__is_active=True).select_related('user')
    
    context = {
        'title': 'Crear Regla de Retención',
        'alert_type_choices': RetentionAlert.AlertType.choices,
        'staff_list': staff_list,
    }
    return render(request, 'backoffice/marketing/automation/retention_rule_create.html', context)


# =============================================================================
# DEMO VIEW (Solo para desarrollo)
# =============================================================================

def demo_advertisements_view(request):
    """
    Vista demo para mostrar cómo se ven los anuncios en la app del cliente.
    Renderiza el archivo HTML con ejemplos visuales.
    """
    return render(request, 'demo_advertisements.html')


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================
from django.http import HttpResponse
from django.utils import timezone as tz_utils
from core.export_service import GenericExportService, ExportConfig


@login_required
def campaign_export_excel(request):
    """Exporta listado de campañas a Excel"""
    gym = request.gym
    campaigns = Campaign.objects.filter(gym=gym).select_related('template')
    
    config = ExportConfig(
        title="Listado de Campañas",
        headers=['ID', 'Nombre', 'Asunto', 'Plantilla', 'Estado', 'Programada', 'Creada'],
        data_extractor=lambda c: [
            c.id,
            c.name,
            c.subject,
            c.template.name if c.template else '-',
            c.get_status_display(),
            c.scheduled_at.strftime('%d/%m/%Y %H:%M') if c.scheduled_at else '-',
            c.created_at.strftime('%d/%m/%Y') if c.created_at else '-',
        ],
        column_widths=[8, 25, 30, 20, 12, 18, 14]
    )
    
    excel_file = GenericExportService.export_to_excel(campaigns.order_by('-created_at'), config, gym.name)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="campanas_{gym.name}_{tz_utils.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
def campaign_export_pdf(request):
    """Exporta listado de campañas a PDF"""
    gym = request.gym
    campaigns = Campaign.objects.filter(gym=gym).select_related('template')
    
    config = ExportConfig(
        title="Listado de Campañas",
        headers=['Nombre', 'Asunto', 'Estado', 'Programada'],
        data_extractor=lambda c: [
            c.name,
            c.subject[:40] + '...' if len(c.subject) > 40 else c.subject,
            c.get_status_display(),
            c.scheduled_at.strftime('%d/%m/%Y') if c.scheduled_at else '-',
        ],
        column_widths=[25, 35, 12, 14],
        landscape=True
    )
    
    pdf_file = GenericExportService.export_to_pdf(campaigns.order_by('-created_at'), config, gym.name)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="campanas_{gym.name}_{tz_utils.now().strftime("%Y%m%d")}.pdf"'
    return response


@login_required
def popup_export_excel(request):
    """Exporta listado de popups a Excel"""
    gym = request.gym
    popups = Popup.objects.filter(gym=gym)
    
    config = ExportConfig(
        title="Listado de Popups",
        headers=['ID', 'Título', 'Tipo', 'Posición', 'Activo', 'Inicio', 'Fin'],
        data_extractor=lambda p: [
            p.id,
            p.title,
            p.popup_type if hasattr(p, 'popup_type') else '-',
            p.position if hasattr(p, 'position') else '-',
            'Sí' if p.is_active else 'No',
            p.start_date.strftime('%d/%m/%Y') if hasattr(p, 'start_date') and p.start_date else '-',
            p.end_date.strftime('%d/%m/%Y') if hasattr(p, 'end_date') and p.end_date else '-',
        ],
        column_widths=[8, 30, 15, 15, 10, 14, 14]
    )
    
    excel_file = GenericExportService.export_to_excel(popups.order_by('-created_at'), config, gym.name)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="popups_{gym.name}_{tz_utils.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
def popup_export_pdf(request):
    """Exporta listado de popups a PDF"""
    gym = request.gym
    popups = Popup.objects.filter(gym=gym)
    
    config = ExportConfig(
        title="Listado de Popups",
        headers=['Título', 'Activo', 'Inicio', 'Fin'],
        data_extractor=lambda p: [
            p.title,
            'Sí' if p.is_active else 'No',
            p.start_date.strftime('%d/%m/%Y') if hasattr(p, 'start_date') and p.start_date else '-',
            p.end_date.strftime('%d/%m/%Y') if hasattr(p, 'end_date') and p.end_date else '-',
        ],
        column_widths=[40, 10, 14, 14]
    )
    
    pdf_file = GenericExportService.export_to_pdf(popups.order_by('-created_at'), config, gym.name)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="popups_{gym.name}_{tz_utils.now().strftime("%Y%m%d")}.pdf"'
    return response


@login_required
def advertisement_export_excel(request):
    """Exporta listado de anuncios a Excel"""
    gym = request.gym
    from .models import Advertisement
    ads = Advertisement.objects.filter(gym=gym)
    
    config = ExportConfig(
        title="Listado de Anuncios",
        headers=['ID', 'Título', 'Posición', 'Activo', 'Clics', 'Impresiones', 'Inicio', 'Fin'],
        data_extractor=lambda a: [
            a.id,
            a.title,
            a.position if hasattr(a, 'position') else '-',
            'Sí' if a.is_active else 'No',
            a.clicks if hasattr(a, 'clicks') else 0,
            a.impressions if hasattr(a, 'impressions') else 0,
            a.start_date.strftime('%d/%m/%Y') if hasattr(a, 'start_date') and a.start_date else '-',
            a.end_date.strftime('%d/%m/%Y') if hasattr(a, 'end_date') and a.end_date else '-',
        ],
        column_widths=[8, 30, 15, 10, 10, 12, 14, 14]
    )
    
    excel_file = GenericExportService.export_to_excel(ads.order_by('-created_at'), config, gym.name)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="anuncios_{gym.name}_{tz_utils.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
def advertisement_export_pdf(request):
    """Exporta listado de anuncios a PDF"""
    gym = request.gym
    from .models import Advertisement
    ads = Advertisement.objects.filter(gym=gym)
    
    config = ExportConfig(
        title="Listado de Anuncios",
        headers=['Título', 'Posición', 'Activo', 'Clics', 'Impresiones'],
        data_extractor=lambda a: [
            a.title,
            a.position if hasattr(a, 'position') else '-',
            'Sí' if a.is_active else 'No',
            a.clicks if hasattr(a, 'clicks') else 0,
            a.impressions if hasattr(a, 'impressions') else 0,
        ],
        column_widths=[35, 15, 10, 12, 14],
        landscape=True
    )
    
    pdf_file = GenericExportService.export_to_pdf(ads.order_by('-created_at'), config, gym.name)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="anuncios_{gym.name}_{tz_utils.now().strftime("%Y%m%d")}.pdf"'
    return response


# =============================================================================
# META (FACEBOOK/INSTAGRAM) LEAD ADS INTEGRATION
# =============================================================================

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
import json
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
def meta_webhook(request, gym_id):
    """
    Webhook endpoint for receiving Meta Lead Ads.
    This endpoint handles both verification (GET) and lead data (POST).
    
    URL: /marketing/meta/webhook/{gym_id}/
    """
    from .models import MetaLeadIntegration, MetaLeadEntry, MetaLeadForm, LeadCard
    from clients.models import Client
    from organizations.models import Gym
    from django.utils import timezone
    
    try:
        gym = Gym.objects.get(id=gym_id)
    except Gym.DoesNotExist:
        logger.error(f"Meta webhook: Gym {gym_id} not found")
        return HttpResponse("Gym not found", status=404)
    
    try:
        integration = gym.meta_integration
    except MetaLeadIntegration.DoesNotExist:
        logger.error(f"Meta webhook: No integration for gym {gym_id}")
        return HttpResponse("Integration not found", status=404)
    
    # GET - Webhook verification
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        if mode == 'subscribe' and token == integration.webhook_verify_token:
            logger.info(f"Meta webhook verified for gym {gym_id}")
            return HttpResponse(challenge, content_type='text/plain')
        else:
            logger.warning(f"Meta webhook verification failed for gym {gym_id}")
            return HttpResponse("Verification failed", status=403)
    
    # POST - Receive lead data
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Meta webhook received for gym {gym_id}: {json.dumps(data)[:500]}")
            
            # Process leadgen entries
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'leadgen':
                        lead_data = change.get('value', {})
                        
                        # Create MetaLeadEntry
                        lead_entry = MetaLeadEntry.objects.create(
                            integration=integration,
                            leadgen_id=lead_data.get('leadgen_id', ''),
                            ad_id=lead_data.get('ad_id', ''),
                            ad_name=lead_data.get('ad_name', ''),
                            campaign_id=lead_data.get('campaign_id', ''),
                            campaign_name=lead_data.get('campaign_name', ''),
                            raw_data=lead_data,
                            platform='facebook'  # or detect from data
                        )
                        
                        # Try to link to form
                        form_id = lead_data.get('form_id')
                        if form_id:
                            form = MetaLeadForm.objects.filter(
                                integration=integration,
                                form_id=form_id
                            ).first()
                            if form:
                                lead_entry.form = form
                        
                        # Extract field data
                        field_data = lead_data.get('field_data', [])
                        for field in field_data:
                            name = field.get('name', '').lower()
                            values = field.get('values', [])
                            value = values[0] if values else ''
                            
                            if 'email' in name:
                                lead_entry.email = value
                            elif 'phone' in name or 'tel' in name:
                                lead_entry.phone = value
                            elif 'first' in name or 'nombre' in name:
                                lead_entry.first_name = value
                            elif 'last' in name or 'apellido' in name:
                                lead_entry.last_name = value
                        
                        lead_entry.save()
                        
                        # Auto-create lead if configured
                        if integration.auto_create_lead:
                            _process_meta_lead(lead_entry, gym)
                        
                        # Update stats
                        integration.leads_received += 1
                        integration.last_lead_at = timezone.now()
                        integration.save(update_fields=['leads_received', 'last_lead_at'])
                        
                        if lead_entry.form:
                            lead_entry.form.leads_received += 1
                            lead_entry.form.last_lead_at = timezone.now()
                            lead_entry.form.save(update_fields=['leads_received', 'last_lead_at'])
            
            return HttpResponse("OK", status=200)
            
        except Exception as e:
            logger.error(f"Meta webhook error for gym {gym_id}: {str(e)}")
            return HttpResponse(str(e), status=500)
    
    return HttpResponse("Method not allowed", status=405)


def _process_meta_lead(lead_entry, gym):
    """
    Process a Meta lead entry and create/link a LeadCard.
    """
    from .models import MetaLeadEntry, LeadCard, LeadPipeline, LeadDistributionRule
    from clients.models import Client
    from django.utils import timezone
    
    # Check for duplicate by email
    existing_client = None
    if lead_entry.email:
        existing_client = Client.objects.filter(
            gym=gym,
            email__iexact=lead_entry.email
        ).first()
    
    # Check by phone if no email match
    if not existing_client and lead_entry.phone:
        existing_client = Client.objects.filter(
            gym=gym,
            phone=lead_entry.phone
        ).first()
    
    if existing_client:
        # Mark as duplicate if client already exists with a lead card
        if hasattr(existing_client, 'lead_card'):
            lead_entry.status = MetaLeadEntry.Status.DUPLICATE
            lead_entry.error_message = f"Cliente existente: {existing_client.id}"
            lead_entry.lead_card = existing_client.lead_card
            lead_entry.save()
            return
        else:
            client = existing_client
    else:
        # Create new client
        client = Client.objects.create(
            gym=gym,
            email=lead_entry.email or '',
            phone=lead_entry.phone or '',
            first_name=lead_entry.first_name or 'Sin nombre',
            last_name=lead_entry.last_name or '',
            status='LEAD'
        )
    
    # Get target stage
    target_stage = None
    if lead_entry.form and lead_entry.form.target_stage:
        target_stage = lead_entry.form.target_stage
    elif lead_entry.integration.default_stage:
        target_stage = lead_entry.integration.default_stage
    else:
        # Get first stage from active pipeline
        pipeline = LeadPipeline.objects.filter(gym=gym, is_active=True).first()
        if pipeline:
            target_stage = pipeline.stages.order_by('order').first()
    
    # Determine source based on platform
    source = LeadCard.Source.FACEBOOK if lead_entry.platform == 'facebook' else LeadCard.Source.INSTAGRAM
    
    # Create lead card
    lead_card = LeadCard.objects.create(
        client=client,
        stage=target_stage,
        source=source,
        notes=f"Lead desde Meta Ads\nCampaña: {lead_entry.campaign_name}\nAnuncio: {lead_entry.ad_name}"
    )
    
    # Auto-assign based on form or distribution rules
    assignee = None
    if lead_entry.form and lead_entry.form.assign_to:
        assignee = lead_entry.form.assign_to
    else:
        # Try distribution rules
        rule = LeadDistributionRule.objects.filter(
            gym=gym,
            is_active=True,
            source_filter__in=[source, '']  # Matching source or no filter
        ).order_by('-priority').first()
        
        if rule:
            assignee = rule.get_next_assignee()
    
    if assignee:
        lead_card.assigned_to = assignee
        lead_card.save()
        
        # Log assignment
        from .models import LeadAssignmentLog
        LeadAssignmentLog.objects.create(
            lead_card=lead_card,
            assigned_to=assignee,
            rule=rule if 'rule' in dir() else None,
            assignment_type='AUTO'
        )
    
    # Update lead entry
    lead_entry.status = MetaLeadEntry.Status.PROCESSED
    lead_entry.lead_card = lead_card
    lead_entry.processed_at = timezone.now()
    lead_entry.save()
    
    # Create stage history
    from .models import LeadStageHistory
    LeadStageHistory.objects.create(
        lead_card=lead_card,
        from_stage=None,
        to_stage=target_stage,
        notes=f"Lead creado desde Meta Ads ({lead_entry.platform})"
    )


@login_required
def meta_integration_settings(request):
    """
    Meta Lead Ads integration settings page.
    """
    from .models import MetaLeadIntegration, MetaLeadForm, MetaLeadEntry, LeadStage, LeadPipeline
    from staff.models import StaffProfile
    from django.contrib import messages
    
    gym = request.gym
    
    # Get or create integration
    integration, created = MetaLeadIntegration.objects.get_or_create(gym=gym)
    
    # Generate webhook URL
    webhook_url = request.build_absolute_uri(f'/marketing/meta/webhook/{gym.id}/')
    if not integration.webhook_url or integration.webhook_url != webhook_url:
        integration.webhook_url = webhook_url
        integration.save(update_fields=['webhook_url'])
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save_credentials':
            integration.app_id = request.POST.get('app_id', '')
            integration.app_secret = request.POST.get('app_secret', '')
            integration.page_id = request.POST.get('page_id', '')
            integration.page_name = request.POST.get('page_name', '')
            integration.is_active = request.POST.get('is_active') == 'on'
            integration.auto_create_lead = request.POST.get('auto_create_lead') == 'on'
            
            default_stage_id = request.POST.get('default_stage')
            if default_stage_id:
                integration.default_stage_id = default_stage_id
            
            integration.save()
            messages.success(request, 'Configuración de Meta guardada correctamente.')
            return redirect('meta_integration_settings')
        
        elif action == 'save_access_token':
            integration.access_token = request.POST.get('access_token', '')
            integration.save()
            messages.success(request, 'Token de acceso guardado.')
            return redirect('meta_integration_settings')
        
        elif action == 'disconnect':
            integration.access_token = ''
            integration.page_id = ''
            integration.page_name = ''
            integration.is_active = False
            integration.save()
            messages.info(request, 'Integración desconectada.')
            return redirect('meta_integration_settings')
    
    # Get pipeline stages for dropdown
    pipeline = LeadPipeline.objects.filter(gym=gym, is_active=True).first()
    stages = pipeline.stages.all() if pipeline else []
    
    # Get staff for assignment
    staff_list = StaffProfile.objects.filter(gym=gym, is_active=True)
    
    # Get lead forms
    lead_forms = integration.lead_forms.all()
    
    # Recent entries
    recent_entries = MetaLeadEntry.objects.filter(
        integration=integration
    ).select_related('form', 'lead_card').order_by('-created_at')[:20]
    
    context = {
        'integration': integration,
        'stages': stages,
        'staff_list': staff_list,
        'lead_forms': lead_forms,
        'recent_entries': recent_entries,
    }
    
    return render(request, 'backoffice/marketing/leads/meta_integration.html', context)


# =============================================================================
# LEAD DISTRIBUTION (Auto-assignment)
# =============================================================================

@login_required
def lead_distribution_settings(request):
    """
    Lead distribution rules configuration.
    """
    from .models import LeadDistributionRule, LeadCard, LeadAssignmentLog
    from staff.models import StaffProfile
    from django.contrib import messages
    
    gym = request.gym
    
    # Get rules
    rules = LeadDistributionRule.objects.filter(gym=gym).prefetch_related('staff_members')
    
    # Get staff for selection
    staff_list = StaffProfile.objects.filter(gym=gym, is_active=True)
    
    # Source choices
    source_choices = LeadCard.Source.choices
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_rule':
            rule = LeadDistributionRule.objects.create(
                gym=gym,
                name=request.POST.get('name', 'Nueva Regla'),
                method=request.POST.get('method', 'ROUND_ROBIN'),
                source_filter=request.POST.get('source_filter', ''),
                max_leads_per_day=int(request.POST.get('max_leads_per_day', 0)),
                max_active_leads=int(request.POST.get('max_active_leads', 0)),
                notify_on_assignment=request.POST.get('notify_on_assignment') == 'on',
                priority=int(request.POST.get('priority', 0)),
            )
            
            # Add staff members
            staff_ids = request.POST.getlist('staff_members')
            if staff_ids:
                rule.staff_members.set(staff_ids)
            
            messages.success(request, f'Regla "{rule.name}" creada correctamente.')
            return redirect('lead_distribution_settings')
        
        elif action == 'delete_rule':
            rule_id = request.POST.get('rule_id')
            try:
                rule = LeadDistributionRule.objects.get(id=rule_id, gym=gym)
                rule.delete()
                messages.success(request, 'Regla eliminada.')
            except LeadDistributionRule.DoesNotExist:
                messages.error(request, 'Regla no encontrada.')
            return redirect('lead_distribution_settings')
        
        elif action == 'toggle_rule':
            rule_id = request.POST.get('rule_id')
            try:
                rule = LeadDistributionRule.objects.get(id=rule_id, gym=gym)
                rule.is_active = not rule.is_active
                rule.save()
            except LeadDistributionRule.DoesNotExist:
                pass
            return redirect('lead_distribution_settings')
    
    # Recent assignments
    recent_assignments = LeadAssignmentLog.objects.filter(
        lead_card__client__gym=gym
    ).select_related('lead_card__client', 'assigned_to', 'rule').order_by('-created_at')[:20]
    
    context = {
        'rules': rules,
        'staff_list': staff_list,
        'source_choices': source_choices,
        'method_choices': LeadDistributionRule.DistributionMethod.choices,
        'recent_assignments': recent_assignments,
    }
    
    return render(request, 'backoffice/marketing/leads/distribution_settings.html', context)


# =============================================================================
# SALES FUNNEL ANALYTICS
# =============================================================================

@login_required
def sales_funnel_analytics(request):
    """
    Sales Funnel Analytics dashboard with conversion rates, lead metrics, and stage analysis.
    """
    from .models import LeadPipeline, LeadStage, LeadCard, LeadStageHistory
    from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField
    from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
    from django.utils import timezone
    from datetime import timedelta
    
    gym = request.gym
    
    # Date filters
    date_range = request.GET.get('range', '30')  # days
    try:
        days = int(date_range)
    except ValueError:
        days = 30
    
    start_date = timezone.now() - timedelta(days=days)
    
    # Get pipeline
    pipeline = LeadPipeline.objects.filter(gym=gym, is_active=True).first()
    
    if not pipeline:
        return render(request, 'backoffice/marketing/leads/funnel_analytics.html', {
            'error': 'No hay pipeline activo. Crea uno desde el tablero de leads.'
        })
    
    stages = pipeline.stages.all()
    
    # Get all leads in period
    leads_in_period = LeadCard.objects.filter(
        client__gym=gym,
        created_at__gte=start_date
    )
    
    # Total leads
    total_leads = leads_in_period.count()
    
    # Leads by stage (current state)
    leads_by_stage = []
    for stage in stages:
        count = LeadCard.objects.filter(
            stage=stage,
            client__gym=gym
        ).count()
        
        created_in_period = leads_in_period.filter(stage=stage).count()
        
        # Calculate conversion rate from this stage
        moved_forward = LeadStageHistory.objects.filter(
            from_stage=stage,
            to_stage__order__gt=stage.order,
            created_at__gte=start_date
        ).count()
        
        total_in_stage = LeadStageHistory.objects.filter(
            to_stage=stage,
            created_at__gte=start_date
        ).count() or 1
        
        conversion_rate = (moved_forward / total_in_stage * 100) if total_in_stage > 0 else 0
        
        leads_by_stage.append({
            'stage': stage,
            'current_count': count,
            'created_in_period': created_in_period,
            'conversion_rate': round(conversion_rate, 1),
            'moved_forward': moved_forward,
        })
    
    # Won/Lost stats
    won_stage = stages.filter(is_won=True).first()
    lost_stage = stages.filter(is_lost=True).first()
    
    won_count = leads_in_period.filter(stage=won_stage).count() if won_stage else 0
    lost_count = leads_in_period.filter(stage=lost_stage).count() if lost_stage else 0
    
    # Overall conversion rate (leads that reached won stage)
    overall_conversion_rate = (won_count / total_leads * 100) if total_leads > 0 else 0
    
    # Leads by source
    leads_by_source = leads_in_period.values('source').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Add source labels
    source_dict = dict(LeadCard.Source.choices)
    for item in leads_by_source:
        item['label'] = source_dict.get(item['source'], item['source'])
    
    # Average time in each stage
    avg_time_by_stage = []
    for stage in stages:
        history_entries = LeadStageHistory.objects.filter(
            from_stage=stage,
            time_in_previous_stage__isnull=False,
            created_at__gte=start_date
        )
        
        if history_entries.exists():
            total_duration = sum(
                (h.time_in_previous_stage.total_seconds() for h in history_entries),
                0
            )
            avg_seconds = total_duration / history_entries.count()
            avg_days = avg_seconds / 86400  # Convert to days
        else:
            avg_days = 0
        
        avg_time_by_stage.append({
            'stage': stage,
            'avg_days': round(avg_days, 1),
        })
    
    # Trend data (leads created by week)
    leads_trend = leads_in_period.annotate(
        week=TruncWeek('created_at')
    ).values('week').annotate(
        count=Count('id')
    ).order_by('week')
    
    # Conversion trend (won leads by week)
    if won_stage:
        conversion_trend = LeadStageHistory.objects.filter(
            to_stage=won_stage,
            created_at__gte=start_date
        ).annotate(
            week=TruncWeek('created_at')
        ).values('week').annotate(
            count=Count('id')
        ).order_by('week')
    else:
        conversion_trend = []
    
    # Top performers (staff with most conversions)
    top_performers = LeadCard.objects.filter(
        client__gym=gym,
        stage=won_stage,
        assigned_to__isnull=False,
        updated_at__gte=start_date
    ).values(
        'assigned_to__user__first_name',
        'assigned_to__user__last_name',
        'assigned_to__id'
    ).annotate(
        conversions=Count('id')
    ).order_by('-conversions')[:5] if won_stage else []
    
    context = {
        'pipeline': pipeline,
        'stages': stages,
        'total_leads': total_leads,
        'won_count': won_count,
        'lost_count': lost_count,
        'overall_conversion_rate': round(overall_conversion_rate, 1),
        'leads_by_stage': leads_by_stage,
        'leads_by_source': leads_by_source,
        'avg_time_by_stage': avg_time_by_stage,
        'leads_trend': list(leads_trend),
        'conversion_trend': list(conversion_trend),
        'top_performers': top_performers,
        'date_range': days,
        'start_date': start_date,
    }
    
    return render(request, 'backoffice/marketing/leads/funnel_analytics.html', context)


# =============================================================================
# SAVED AUDIENCES (Audiencias Guardadas)
# =============================================================================

@login_required
def audience_list_view(request):
    """
    Lista de audiencias guardadas.
    """
    from .models import SavedAudience
    gym = request.gym
    
    audiences = SavedAudience.objects.filter(gym=gym).order_by('-created_at')
    
    # Obtener estadísticas de uso
    for audience in audiences:
        audience.campaigns_count = audience.campaigns.count()
        audience.popups_count = audience.popups.count()
        audience.ads_count = audience.advertisements.count()
        audience.total_uses = audience.campaigns_count + audience.popups_count + audience.ads_count
    
    context = {
        'audiences': audiences,
        'title': 'Audiencias Guardadas'
    }
    return render(request, 'backoffice/marketing/audiences/list.html', context)


@login_required
def audience_create_view(request):
    """
    Crear nueva audiencia.
    """
    from .models import SavedAudience
    from clients.models import ClientTag, ClientGroup
    from memberships.models import MembershipPlan
    from services.models import Service
    from products.models import Product
    
    gym = request.gym
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        audience_type = request.POST.get('audience_type', 'DYNAMIC')
        redirect_to = request.POST.get('redirect_to', '')
        
        if not name:
            from django.contrib import messages
            messages.error(request, 'El nombre es obligatorio')
            return redirect('marketing_audience_create')
        
        # Recoger filtros (ahora soportan múltiples valores)
        filters = {}
        
        # Filtros múltiples (listas)
        statuses = request.POST.getlist('statuses')
        if statuses:
            filters['statuses'] = statuses
        # Compatibilidad con formato antiguo (single status)
        elif request.POST.get('status') and request.POST.get('status') != 'all':
            filters['statuses'] = [request.POST.get('status')]
        
        genders = request.POST.getlist('genders')
        if genders:
            filters['genders'] = genders
        elif request.POST.get('gender') and request.POST.get('gender') != 'all':
            filters['genders'] = [request.POST.get('gender')]
        
        # Planes de membresía (múltiples)
        membership_plans = request.POST.getlist('membership_plans')
        if membership_plans:
            filters['membership_plans'] = [int(p) for p in membership_plans]
        elif request.POST.get('membership_plan') and request.POST.get('membership_plan') != 'all':
            filters['membership_plans'] = [int(request.POST.get('membership_plan'))]
        
        # Servicios (múltiples)
        services = request.POST.getlist('services')
        if services:
            filters['services'] = [int(s) for s in services]
        elif request.POST.get('service') and request.POST.get('service') != 'all':
            filters['services'] = [int(request.POST.get('service'))]
        
        # Productos (múltiples)
        products = request.POST.getlist('products')
        if products:
            filters['products'] = [int(p) for p in products]
        
        # Grupos (múltiples)
        groups = request.POST.getlist('groups')
        if groups:
            filters['groups'] = [int(g) for g in groups]
        
        # Tags (múltiples)
        tag_ids = request.POST.getlist('tags')
        if tag_ids:
            filters['tags'] = [int(t) for t in tag_ids]
        
        # Origen de alta (múltiples)
        created_from = request.POST.getlist('created_from')
        if created_from:
            filters['created_from'] = created_from
        
        # Filtros simples
        if request.POST.get('age_min'):
            filters['age_min'] = request.POST.get('age_min')
        
        if request.POST.get('age_max'):
            filters['age_max'] = request.POST.get('age_max')
        
        if request.POST.get('has_active_membership') == 'on':
            filters['has_active_membership'] = True
        
        if request.POST.get('is_inactive') == 'on':
            filters['is_inactive'] = True
        
        if request.POST.get('company') and request.POST.get('company') != 'all':
            filters['company'] = request.POST.get('company')
        
        # Filtro de saldo de monedero
        wallet_balances = request.POST.getlist('wallet_balance')
        if wallet_balances:
            filters['wallet_balances'] = wallet_balances
        
        # Crear audiencia
        audience = SavedAudience.objects.create(
            gym=gym,
            name=name,
            description=description,
            audience_type=audience_type,
            filters=filters,
            created_by=request.user
        )
        
        # Si hay clientes seleccionados (para audiencia estática/mixta)
        client_ids = request.POST.get('static_client_ids', '')
        if client_ids:
            from clients.models import Client
            ids_list = [int(i) for i in client_ids.split(',') if i.strip()]
            clients = Client.objects.filter(id__in=ids_list, gym=gym)
            audience.static_members.set(clients)
        
        from django.contrib import messages
        messages.success(request, f'Audiencia "{name}" creada con {audience.get_members_count()} clientes')
        
        # Redireccionar según origen
        if redirect_to == 'explorer':
            return redirect('client_explorer')
        return redirect('marketing_audience_list')
    
    # GET: mostrar formulario
    tags = ClientTag.objects.filter(gym=gym)
    membership_plans = MembershipPlan.objects.filter(gym=gym, is_active=True)
    services = Service.objects.filter(gym=gym, is_active=True)
    products = Product.objects.filter(gym=gym, is_active=True)
    groups = ClientGroup.objects.filter(gym=gym)
    
    # Verificar si el monedero está activo
    from finance.models import WalletSettings
    wallet_enabled = False
    try:
        wallet_settings = WalletSettings.objects.get(gym=gym)
        wallet_enabled = wallet_settings.wallet_enabled
    except WalletSettings.DoesNotExist:
        pass
    
    context = {
        'title': 'Nueva Audiencia',
        'tags': tags,
        'membership_plans': membership_plans,
        'services': services,
        'products': products,
        'groups': groups,
        'wallet_enabled': wallet_enabled,
    }
    return render(request, 'backoffice/marketing/audiences/form.html', context)


@login_required
def audience_edit_view(request, pk):
    """
    Editar audiencia existente.
    Por simplicidad, redirigimos a la lista. Para modificar, eliminar y crear nueva.
    """
    from django.contrib import messages
    messages.info(request, 'Para modificar una audiencia, elimínala y crea una nueva.')
    return redirect('marketing_audience_list')


@login_required
def audience_delete_view(request, pk):
    """
    Eliminar audiencia.
    """
    from .models import SavedAudience
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    
    gym = request.gym
    audience = get_object_or_404(SavedAudience, pk=pk, gym=gym)
    
    # Verificar si está en uso
    uses = audience.campaigns.count() + audience.popups.count() + audience.advertisements.count()
    
    if uses > 0 and request.method != 'POST':
        messages.warning(request, f'Esta audiencia está en uso en {uses} elementos. ¿Seguro que deseas eliminarla?')
    
    if request.method == 'POST':
        name = audience.name
        audience.delete()
        messages.success(request, f'Audiencia "{name}" eliminada')
        return redirect('marketing_audience_list')
    
    context = {
        'audience': audience,
        'uses': uses,
    }
    return render(request, 'backoffice/marketing/audiences/confirm_delete.html', context)


@login_required
def audience_detail_view(request, pk):
    """
    Ver detalle de audiencia con previsualización de miembros.
    """
    from .models import SavedAudience
    from django.shortcuts import get_object_or_404
    from django.core.paginator import Paginator
    
    gym = request.gym
    audience = get_object_or_404(SavedAudience, pk=pk, gym=gym)
    
    # Obtener miembros con paginación
    members_qs = audience.get_members_queryset()
    paginator = Paginator(members_qs, 50)
    page = request.GET.get('page', 1)
    members = paginator.get_page(page)
    
    # Estadísticas de uso
    campaigns_using = audience.campaigns.all()
    popups_using = audience.popups.all()
    ads_using = audience.advertisements.all()
    
    context = {
        'audience': audience,
        'members': members,
        'total_count': members_qs.count(),
        'campaigns_using': campaigns_using,
        'popups_using': popups_using,
        'ads_using': ads_using,
    }
    return render(request, 'backoffice/marketing/audiences/detail.html', context)


@login_required
def audience_preview_count(request):
    """
    API para previsualizar el conteo de una audiencia con filtros (AJAX).
    """
    from django.http import JsonResponse
    from clients.models import Client
    from django.db.models import Q
    
    gym = request.gym
    
    # Obtener filtros del request
    qs = Client.objects.filter(gym=gym)
    
    status = request.GET.get('status')
    if status and status != 'all':
        qs = qs.filter(status=status)
    
    gender = request.GET.get('gender')
    if gender and gender != 'all':
        qs = qs.filter(gender=gender)
    
    age_min = request.GET.get('age_min')
    if age_min:
        from datetime import date
        from dateutil.relativedelta import relativedelta
        max_birth = date.today() - relativedelta(years=int(age_min))
        qs = qs.filter(birth_date__lte=max_birth)
    
    age_max = request.GET.get('age_max')
    if age_max:
        from datetime import date
        from dateutil.relativedelta import relativedelta
        min_birth = date.today() - relativedelta(years=int(age_max) + 1)
        qs = qs.filter(birth_date__gt=min_birth)
    
    membership_plan = request.GET.get('membership_plan')
    if membership_plan and membership_plan != 'all':
        qs = qs.filter(memberships__plan_id=membership_plan, memberships__status='ACTIVE').distinct()
    
    has_active = request.GET.get('has_active_membership')
    if has_active == 'true':
        qs = qs.filter(memberships__status='ACTIVE').distinct()
    
    is_inactive = request.GET.get('is_inactive')
    if is_inactive == 'true':
        qs = qs.exclude(memberships__status='ACTIVE')
    
    company = request.GET.get('company')
    if company == 'company':
        qs = qs.filter(is_company_client=True)
    elif company == 'individual':
        qs = qs.filter(is_company_client=False)
    
    tags = request.GET.getlist('tags')
    if tags:
        qs = qs.filter(tags__id__in=tags).distinct()
    
    count = qs.distinct().count()
    
    return JsonResponse({
        'count': count,
        'formatted': f'{count:,}'.replace(',', '.')
    })


@login_required  
def audience_create_from_selection(request):
    """
    Crear audiencia desde una selección de clientes (desde listado de clientes).
    """
    from .models import SavedAudience
    from clients.models import Client
    from django.http import JsonResponse
    from django.contrib import messages
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    gym = request.gym
    
    import json
    try:
        data = json.loads(request.body)
    except:
        data = request.POST
    
    name = data.get('name', '').strip()
    client_ids = data.get('client_ids', [])
    
    if not name:
        return JsonResponse({'error': 'El nombre es obligatorio'}, status=400)
    
    if not client_ids:
        return JsonResponse({'error': 'Selecciona al menos un cliente'}, status=400)
    
    # Crear audiencia estática
    audience = SavedAudience.objects.create(
        gym=gym,
        name=name,
        audience_type='STATIC',
        created_by=request.user
    )
    
    # Añadir miembros
    clients = Client.objects.filter(id__in=client_ids, gym=gym)
    audience.static_members.set(clients)
    
    return JsonResponse({
        'success': True,
        'audience_id': audience.id,
        'count': clients.count(),
        'message': f'Audiencia "{name}" creada con {clients.count()} clientes'
    })
