from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_gym_permission
from django.contrib import messages
from .models import Product, ProductCategory
from .forms import ProductForm, ProductCategoryForm

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
        form = ProductForm(request.POST, request.FILES, gym=gym)
        if form.is_valid():
            product = form.save(commit=False)
            product.gym = gym
            product.save()
            messages.success(request, 'Producto creado correctamente.')
            return redirect('product_list')
    else:
        form = ProductForm(gym=gym)
    
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
        form = ProductForm(request.POST, request.FILES, instance=product, gym=gym)
        if form.is_valid():
            form.save()
            # Use StockMove logic here if stock changes? For simplicity we allow direct edit for now,
            # but ideally we should block stock edit and use Adjustment view. 
            # We will adhere to user request for "Simple" first.
            messages.success(request, 'Producto actualizado.')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product, gym=gym)
    
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
