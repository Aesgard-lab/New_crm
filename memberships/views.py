from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_gym_permission
from django.contrib import messages
from .models import MembershipPlan
from .forms import MembershipPlanForm, PlanAccessRuleFormSet
from activities.models import ActivityCategory, Activity
from services.models import ServiceCategory, Service
from services.franchise_service import FranchisePropagationService

@login_required
@require_gym_permission('memberships.view_membershipplan')
def plan_list(request):
    gym = request.gym
    plans = MembershipPlan.objects.filter(gym=gym).order_by('display_order', '-created_at')
    return render(request, 'backoffice/memberships/list.html', {'plans': plans})

@login_required
@require_gym_permission('memberships.add_membershipplan')
def plan_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = MembershipPlanForm(request.POST, request.FILES, gym=gym, user=request.user)
        formset = PlanAccessRuleFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            plan = form.save(commit=False)
            plan.gym = gym
            plan.save()
            
            formset.instance = plan
            formset.save()
            
            # Handle Propagation
            if 'propagate_to_gyms' in form.fields and form.cleaned_data.get('propagate_to_gyms'):
                target_gyms = form.cleaned_data['propagate_to_gyms']
                results = FranchisePropagationService.propagate_membership(plan, target_gyms)
                
                msg = f'Cuota creada. Propagación: {results["created"]} creadas, {results["updated"]} actualizadas.'
                if results['errors']: msg += f' Warning: {len(results["errors"])} errores.'
                messages.success(request, msg)
            else:
                messages.success(request, 'Cuota creada correctamente.')
            return redirect('membership_plan_list')
    else:
        form = MembershipPlanForm(gym=gym, user=request.user)
        formset = PlanAccessRuleFormSet()
        
    # We need to filter the choices in the formset to only show THIS gym's categories
    # This is a bit advanced for standard formsets, but we can patch the querysets on the forms
    # Filter choices for existing forms
    for subform in formset.forms:
        subform.fields['activity_category'].queryset = ActivityCategory.objects.filter(gym=gym)
        subform.fields['activity'].queryset = Activity.objects.filter(gym=gym)
        subform.fields['service_category'].queryset = ServiceCategory.objects.filter(gym=gym)
        subform.fields['service'].queryset = Service.objects.filter(gym=gym)

    # Filter choices for the empty form (used for dynamic rows)
    formset.empty_form.fields['activity_category'].queryset = ActivityCategory.objects.filter(gym=gym)
    formset.empty_form.fields['activity'].queryset = Activity.objects.filter(gym=gym)
    formset.empty_form.fields['service_category'].queryset = ServiceCategory.objects.filter(gym=gym)
    formset.empty_form.fields['service'].queryset = Service.objects.filter(gym=gym)

    return render(request, 'backoffice/memberships/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Nueva Cuota / Bono'
    })

@login_required
@require_gym_permission('memberships.change_membershipplan')
def plan_edit(request, pk):
    gym = request.gym
    plan = get_object_or_404(MembershipPlan, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = MembershipPlanForm(request.POST, request.FILES, instance=plan, gym=gym, user=request.user)
        formset = PlanAccessRuleFormSet(request.POST, instance=plan)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            
            # Handle Propagation
            if 'propagate_to_gyms' in form.fields and form.cleaned_data.get('propagate_to_gyms'):
                target_gyms = form.cleaned_data['propagate_to_gyms']
                results = FranchisePropagationService.propagate_membership(plan, target_gyms)
                
                msg = f'Cuota actualizada. Propagación: {results["created"]} creadas, {results["updated"]} actualizados.'
                messages.success(request, msg)
            else:
                messages.success(request, 'Cuota actualizada.')
            return redirect('membership_plan_list')
    else:
        form = MembershipPlanForm(instance=plan, gym=gym, user=request.user)
        formset = PlanAccessRuleFormSet(instance=plan)

    # Filter formset choices
    for subform in formset.forms:
        subform.fields['activity_category'].queryset = ActivityCategory.objects.filter(gym=gym)
        subform.fields['activity'].queryset = Activity.objects.filter(gym=gym)
        subform.fields['service_category'].queryset = ServiceCategory.objects.filter(gym=gym)
        subform.fields['service'].queryset = Service.objects.filter(gym=gym)

    # Filter choices for empty form (dynamic rows)
    formset.empty_form.fields['activity_category'].queryset = ActivityCategory.objects.filter(gym=gym)
    formset.empty_form.fields['activity'].queryset = Activity.objects.filter(gym=gym)
    formset.empty_form.fields['service_category'].queryset = ServiceCategory.objects.filter(gym=gym)
    formset.empty_form.fields['service'].queryset = Service.objects.filter(gym=gym)

    return render(request, 'backoffice/memberships/form.html', {
        'form': form,
        'formset': formset,
        'title': f'Editar {plan.name}'
    })


from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from datetime import datetime
from django.utils import timezone
from .models import MembershipPause
from clients.models import ClientMembership

@login_required
@require_POST
def api_create_pause(request):
    """API para crear una pausa en una membresía"""
    try:
        data = json.loads(request.body)
        membership_id = data.get('membership_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        reason = data.get('reason', '')
        
        if not all([membership_id, start_date, end_date]):
            return JsonResponse({'error': 'Faltan datos requeridos'}, status=400)
        
        # Obtener la membresía
        membership = get_object_or_404(ClientMembership, id=membership_id, client__gym=request.gym)
        
        # Validar que la membresía esté activa
        if membership.status != 'ACTIVE':
            return JsonResponse({'error': 'Solo se pueden pausar membresías activas'}, status=400)
        
        # Validar que sea recurrente
        if not membership.is_recurring:
            return JsonResponse({'error': 'Solo se pueden pausar membresías recurrentes'}, status=400)
        
        # Convertir fechas
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
        
        # Validar fechas
        today = timezone.now().date()
        if start_date_obj < today:
            return JsonResponse({'error': 'La fecha de inicio no puede ser en el pasado'}, status=400)
        
        if end_date_obj <= start_date_obj:
            return JsonResponse({'error': 'La fecha de fin debe ser posterior a la de inicio'}, status=400)
        
        # Verificar pausas activas
        active_pauses = membership.pauses.filter(status__in=['PENDING', 'ACTIVE'])
        if active_pauses.exists():
            return JsonResponse({'error': 'Ya existe una pausa activa o pendiente para esta membresía'}, status=400)
        
        # Crear la pausa
        pause = MembershipPause.objects.create(
            membership=membership,
            start_date=start_date_obj,
            end_date=end_date_obj,
            reason=reason,
            fee_charged=0,  # Por ahora sin cargo
            created_by=request.user,
            status='PENDING' if start_date_obj > today else 'ACTIVE',
            gym_access_allowed=False,  # Configurar según el plan en el futuro
            booking_allowed=False
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Pausa creada correctamente',
            'pause_id': pause.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
