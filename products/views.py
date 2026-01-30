from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_gym_permission
from django.contrib import messages
from .models import Product, ProductCategory
from .forms import ProductForm, ProductCategoryForm
from services.franchise_service import FranchisePropagationService

# --- Products ---

@login_required
@require_gym_permission('products.view_product')
def product_list(request):
    gym = request.gym
    products = Product.objects.filter(gym=gym).select_related('category')
    return render(request, 'backoffice/products/list.html', {'products': products})

@login_required
@require_gym_permission('products.add_product')
def product_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, gym=gym, user=request.user)
        if form.is_valid():
            product = form.save(commit=False)
            product.gym = gym
            product.save()
            
            # Handle Propagation
            if 'propagate_to_gyms' in form.fields and form.cleaned_data.get('propagate_to_gyms'):
                target_gyms = form.cleaned_data['propagate_to_gyms']
                results = FranchisePropagationService.propagate_product(product, target_gyms)
                
                msg = f'Producto creado. Propagación: {results["created"]} creados, {results["updated"]} actualizados.'
                if results['errors']: msg += f' Warning: {len(results["errors"])} errores.'
                messages.success(request, msg)
            else:
                messages.success(request, 'Producto creado correctamente.')
            return redirect('product_list')
    else:
        form = ProductForm(gym=gym, user=request.user)
    
    return render(request, 'backoffice/products/form.html', {
        'form': form,
        'title': 'Nuevo Producto'
    })

@login_required
@require_gym_permission('products.change_product')
def product_edit(request, pk):
    gym = request.gym
    product = get_object_or_404(Product, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, gym=gym, user=request.user)
        if form.is_valid():
            product = form.save()
            
            # Handle Propagation
            if 'propagate_to_gyms' in form.fields and form.cleaned_data.get('propagate_to_gyms'):
                target_gyms = form.cleaned_data['propagate_to_gyms']
                results = FranchisePropagationService.propagate_product(product, target_gyms)
                
                msg = f'Producto actualizado. Propagación: {results["created"]} creados, {results["updated"]} actualizados.'
                messages.success(request, msg)
            else:
                messages.success(request, 'Producto actualizado.')

            return redirect('product_list')
    else:
        form = ProductForm(instance=product, gym=gym, user=request.user)
    
    return render(request, 'backoffice/products/form.html', {
        'form': form,
        'title': f'Editar {product.name}'
    })

# --- Categories ---

@login_required
@require_gym_permission('products.view_productcategory')
def category_list(request):
    gym = request.gym
    categories = ProductCategory.objects.filter(gym=gym).select_related('parent')
    return render(request, 'backoffice/products/categories/list.html', {'categories': categories})

@login_required
@require_gym_permission('products.add_productcategory')
def category_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = ProductCategoryForm(request.POST, request.FILES, gym=gym)
        if form.is_valid():
            category = form.save(commit=False)
            category.gym = gym
            category.save()
            messages.success(request, 'Categoría creada correctamente.')
            return redirect('product_category_list')
    else:
        form = ProductCategoryForm(gym=gym)
    
    return render(request, 'backoffice/products/categories/form.html', {
        'form': form,
        'title': 'Nueva Categoría'
    })

@login_required
@require_gym_permission('products.change_productcategory')
def category_edit(request, pk):
    gym = request.gym
    category = get_object_or_404(ProductCategory, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = ProductCategoryForm(request.POST, request.FILES, instance=category, gym=gym)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada.')
            return redirect('product_category_list')
    else:
        form = ProductCategoryForm(instance=category, gym=gym)
    
    return render(request, 'backoffice/products/categories/form.html', {
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
@require_gym_permission('products.view_product')
def product_export_excel(request):
    """Exporta listado de productos a Excel"""
    gym = request.gym
    products = Product.objects.filter(gym=gym).select_related('category')
    
    config = ExportConfig(
        title="Listado de Productos",
        headers=['ID', 'Código', 'Nombre', 'Categoría', 'Precio', 'Stock', 'Estado'],
        data_extractor=lambda p: [
            p.id,
            p.sku or '-',
            p.name,
            p.category.name if p.category else '-',
            p.price,
            p.stock if hasattr(p, 'stock') else '-',
            'Activo' if p.is_active else 'Inactivo',
        ],
        column_widths=[8, 12, 28, 18, 12, 10, 10]
    )
    
    excel_file = GenericExportService.export_to_excel(products.order_by('name'), config, gym.name)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="productos_{gym.name}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
@require_gym_permission('products.view_product')
def product_export_pdf(request):
    """Exporta listado de productos a PDF"""
    gym = request.gym
    products = Product.objects.filter(gym=gym).select_related('category')
    
    config = ExportConfig(
        title="Listado de Productos",
        headers=['Código', 'Nombre', 'Categoría', 'Precio', 'Stock', 'Estado'],
        data_extractor=lambda p: [
            p.sku or '-',
            p.name,
            p.category.name if p.category else '-',
            p.price,
            p.stock if hasattr(p, 'stock') else '-',
            'Activo' if p.is_active else 'Inactivo',
        ],
        column_widths=[12, 28, 18, 12, 10, 10]
    )
    
    pdf_file = GenericExportService.export_to_pdf(products.order_by('name'), config, gym.name)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="productos_{gym.name}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response
