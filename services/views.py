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


# ==========================================
# EXPORT FUNCTIONS
# ==========================================
from django.http import HttpResponse
from django.utils import timezone
from core.export_service import GenericExportService, ExportConfig


@login_required
@require_gym_permission('services.view_service')
def service_export_excel(request):
    """Exporta listado de servicios a Excel"""
    gym = request.gym
    services = Service.objects.filter(gym=gym).select_related('category')
    
    config = ExportConfig(
        title="Listado de Servicios",
        headers=['ID', 'Nombre', 'Categoría', 'Precio', 'Duración', 'Visible Online', 'Estado'],
        data_extractor=lambda s: [
            s.id,
            s.name,
            s.category.name if s.category else '-',
            s.price,
            f"{s.duration} min" if hasattr(s, 'duration') and s.duration else '-',
            'Sí' if s.is_visible_online else 'No',
            'Activo' if s.is_active else 'Inactivo',
        ],
        column_widths=[8, 28, 18, 12, 12, 14, 10]
    )
    
    excel_file = GenericExportService.export_to_excel(services.order_by('name'), config, gym.name)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="servicios_{gym.name}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
@require_gym_permission('services.view_service')
def service_export_pdf(request):
    """Exporta listado de servicios a PDF"""
    gym = request.gym
    services = Service.objects.filter(gym=gym).select_related('category')
    
    config = ExportConfig(
        title="Listado de Servicios",
        headers=['Nombre', 'Categoría', 'Precio', 'Duración', 'Visible', 'Estado'],
        data_extractor=lambda s: [
            s.name,
            s.category.name if s.category else '-',
            s.price,
            f"{s.duration} min" if hasattr(s, 'duration') and s.duration else '-',
            'Sí' if s.is_visible_online else 'No',
            'Activo' if s.is_active else 'Inactivo',
        ],
        column_widths=[28, 18, 12, 12, 10, 10]
    )
    
    pdf_file = GenericExportService.export_to_pdf(services.order_by('name'), config, gym.name)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="servicios_{gym.name}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response
