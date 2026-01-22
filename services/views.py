from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_gym_permission
from django.contrib import messages
from .models import Service, ServiceCategory
from .forms import ServiceForm, ServiceCategoryForm
from services.franchise_service import FranchisePropagationService

# --- Services ---

@login_required
@require_gym_permission('services.view_service')
def service_list(request):
    gym = request.gym
    services = Service.objects.filter(gym=gym).select_related('category')
    return render(request, 'backoffice/services/list.html', {'services': services})

@login_required
@require_gym_permission('services.add_service')
def service_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, gym=gym, user=request.user)
        if form.is_valid():
            service = form.save(commit=False)
            service.gym = gym
            service.save()
            
            # Handle Propagation
            if 'propagate_to_gyms' in form.fields and form.cleaned_data.get('propagate_to_gyms'):
                target_gyms = form.cleaned_data['propagate_to_gyms']
                results = FranchisePropagationService.propagate_service(service, target_gyms)
                
                msg = f'Servicio creado. Propagación: {results["created"]} creados, {results["updated"]} actualizados.'
                if results['errors']: msg += f' Warning: {len(results["errors"])} errores.'
                messages.success(request, msg)
            else:
                messages.success(request, 'Servicio creado correctamente.')
            return redirect('service_list')
    else:
        form = ServiceForm(gym=gym, user=request.user)
    
    return render(request, 'backoffice/services/form.html', {
        'form': form,
        'title': 'Nuevo Servicio'
    })

@login_required
@require_gym_permission('services.change_service')
def service_edit(request, pk):
    gym = request.gym
    service = get_object_or_404(Service, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, instance=service, gym=gym, user=request.user)
        if form.is_valid():
            service = form.save()
            
            # Handle Propagation
            if 'propagate_to_gyms' in form.fields and form.cleaned_data.get('propagate_to_gyms'):
                target_gyms = form.cleaned_data['propagate_to_gyms']
                results = FranchisePropagationService.propagate_service(service, target_gyms)
                
                msg = f'Servicio actualizado. Propagación: {results["created"]} creados, {results["updated"]} actualizados.'
                messages.success(request, msg)
            else:
                messages.success(request, 'Servicio actualizado.')
            return redirect('service_list')
    else:
        form = ServiceForm(instance=service, gym=gym, user=request.user)
    
    return render(request, 'backoffice/services/form.html', {
        'form': form,
        'title': f'Editar {service.name}'
    })

# --- Categories ---

@login_required
@require_gym_permission('services.view_servicecategory')
def category_list(request):
    gym = request.gym
    categories = ServiceCategory.objects.filter(gym=gym).select_related('parent')
    return render(request, 'backoffice/services/categories/list.html', {'categories': categories})

@login_required
@require_gym_permission('services.add_servicecategory')
def category_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = ServiceCategoryForm(request.POST, request.FILES, gym=gym)
        if form.is_valid():
            category = form.save(commit=False)
            category.gym = gym
            category.save()
            messages.success(request, 'Categoría creada correctamente.')
            return redirect('service_category_list')
    else:
        form = ServiceCategoryForm(gym=gym)
    
    return render(request, 'backoffice/services/categories/form.html', {
        'form': form,
        'title': 'Nueva Categoría'
    })

@login_required
@require_gym_permission('services.change_servicecategory')
def category_edit(request, pk):
    gym = request.gym
    category = get_object_or_404(ServiceCategory, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = ServiceCategoryForm(request.POST, request.FILES, instance=category, gym=gym)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada.')
            return redirect('service_category_list')
    else:
        form = ServiceCategoryForm(instance=category, gym=gym)
    
    return render(request, 'backoffice/services/categories/form.html', {
        'form': form,
        'title': f'Editar {category.name}'
    })
