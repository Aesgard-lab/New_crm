from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_gym_permission
from django.contrib import messages
from .models import MembershipPlan
from .forms import MembershipPlanForm, PlanAccessRuleFormSet
from activities.models import ActivityCategory, Activity
from services.models import ServiceCategory, Service

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
        form = MembershipPlanForm(request.POST, request.FILES, gym=gym)
        formset = PlanAccessRuleFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            plan = form.save(commit=False)
            plan.gym = gym
            plan.save()
            
            formset.instance = plan
            formset.save()
            
            messages.success(request, 'Cuota creada correctamente.')
            return redirect('membership_plan_list')
    else:
        form = MembershipPlanForm(gym=gym)
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
        form = MembershipPlanForm(request.POST, request.FILES, instance=plan, gym=gym)
        formset = PlanAccessRuleFormSet(request.POST, instance=plan)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Cuota actualizada.')
            return redirect('membership_plan_list')
    else:
        form = MembershipPlanForm(instance=plan, gym=gym)
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
