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
    from django.utils import timezone
    
    if request.method == 'POST':
        form = PopupForm(request.POST, request.FILES)
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
        form = PopupForm()
    return render(request, 'backoffice/marketing/popups/form.html', {'form': form, 'title': 'Nuevo Popup'})

@login_required
def popup_edit_view(request, pk):
    from .forms import PopupForm
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    from django.utils import timezone
    
    popup = get_object_or_404(Popup, pk=pk, gym=request.gym)
    
    if request.method == 'POST':
        form = PopupForm(request.POST, request.FILES, instance=popup)
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
        form = AdvertisementForm(request.POST, request.FILES, user=request.user)
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
        form = AdvertisementForm(user=request.user)
    
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
        form = AdvertisementForm(request.POST, request.FILES, instance=ad, user=request.user)
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
        form = AdvertisementForm(instance=ad, user=request.user)
    
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
    from django.contrib import messages
    
    gym = request.gym
    pipeline = LeadPipeline.objects.filter(gym=gym, is_active=True).first()
    
    if not pipeline:
        messages.warning(request, 'No hay pipeline activo. Ve al tablero para crear uno.')
        return redirect('lead_board')
    
    stages = pipeline.stages.all()
    automations = LeadStageAutomation.objects.filter(
        from_stage__pipeline=pipeline
    ).select_related('from_stage', 'to_stage')
    
    context = {
        'pipeline': pipeline,
        'stages': stages,
        'automations': automations,
        'trigger_choices': LeadStageAutomation.TriggerType.choices,
    }
    return render(request, 'backoffice/marketing/leads/settings.html', context)


@login_required
def lead_card_move_api(request, card_id):
    """
    API endpoint for drag & drop card movement.
    """
    from django.http import JsonResponse
    from .models import LeadCard, LeadStage
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
        
        new_stage = LeadStage.objects.get(
            id=new_stage_id,
            pipeline__gym=request.gym
        )
        
        card.stage = new_stage
        card.save()
        
        # If moved to "won" stage, convert client to active
        if new_stage.is_won and card.client.status == 'LEAD':
            card.client.status = 'ACTIVE'
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
    from .models import LeadCard
    import json
    
    try:
        card = LeadCard.objects.select_related('client', 'stage', 'assigned_to').get(
            id=card_id,
            client__gym=request.gym
        )
        
        if request.method == 'GET':
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
