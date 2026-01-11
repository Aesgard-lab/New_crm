from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import require_gym_permission
from .models import TaxRate, PaymentMethod, FinanceSettings
from .forms import TaxRateForm, PaymentMethodForm, FinanceSettingsForm

@login_required
@require_gym_permission('finance.view_finance') 
def settings_view(request):
    gym = request.gym
    tax_rates = TaxRate.objects.filter(gym=gym)
    payment_methods = PaymentMethod.objects.filter(gym=gym)
    
    # Get or create finance settings
    finance_settings, created = FinanceSettings.objects.get_or_create(gym=gym)
    
    if request.method == 'POST' and 'save_settings' in request.POST:
        settings_form = FinanceSettingsForm(request.POST, instance=finance_settings)
        if settings_form.is_valid():
            s = settings_form.save(commit=False)
            
            # Validate Stripe Keys if present
            if s.stripe_public_key and s.stripe_secret_key:
                from .stripe_utils import validate_keys
                try:
                    validate_keys(s.stripe_public_key, s.stripe_secret_key)
                    messages.success(request, 'Configuración actualizada y conexión a Stripe correcta ✅')
                except Exception as e:
                    messages.warning(request, f'Configuración guardada, pero error en Stripe: {str(e)}')
            else:
                 messages.success(request, 'Configuración financiera actualizada.')
            
            s.save()
            return redirect('finance_settings')
    else:
        settings_form = FinanceSettingsForm(instance=finance_settings)
    
    context = {
        'title': 'Ajustes de Finanzas',
        'tax_rates': tax_rates,
        'payment_methods': payment_methods,
        'settings_form': settings_form,
    }
    return render(request, 'backoffice/finance/settings.html', context)

# --- Tax Rates ---

@login_required
@require_gym_permission('finance.change_taxrate')
def tax_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = TaxRateForm(request.POST)
        if form.is_valid():
            tax = form.save(commit=False)
            tax.gym = gym
            tax.save()
            messages.success(request, 'Impuesto creado correctamente.')
            return redirect('finance_settings')
    else:
        form = TaxRateForm()
    
    return render(request, 'backoffice/finance/form.html', {
        'title': 'Nuevo Impuesto',
        'form': form,
        'back_url': 'finance_settings'
    })

@login_required
@require_gym_permission('finance.change_taxrate')
def tax_edit(request, pk):
    gym = request.gym
    tax = get_object_or_404(TaxRate, pk=pk, gym=gym)
    if request.method == 'POST':
        form = TaxRateForm(request.POST, instance=tax)
        if form.is_valid():
            form.save()
            messages.success(request, 'Impuesto actualizado correctamente.')
            return redirect('finance_settings')
    else:
        form = TaxRateForm(instance=tax)
    
    return render(request, 'backoffice/finance/form.html', {
        'title': f'Editar Impuesto: {tax.name}',
        'form': form,
        'back_url': 'finance_settings'
    })

@login_required
@require_gym_permission('finance.delete_taxrate')
def tax_delete(request, pk):
    gym = request.gym
    tax = get_object_or_404(TaxRate, pk=pk, gym=gym)
    if request.method == 'POST':
        tax.delete()
        messages.success(request, 'Impuesto eliminado.')
        return redirect('finance_settings')
    return render(request, 'backoffice/confirm_delete.html', {
        'title': 'Eliminar Impuesto',
        'object': tax,
        'back_url': 'finance_settings'
    })

# --- Payment Methods ---

@login_required
@require_gym_permission('finance.change_paymentmethod')
def method_create(request):
    gym = request.gym
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            pm = form.save(commit=False)
            pm.gym = gym
            pm.save()
            messages.success(request, 'Método de pago creado correctamente.')
            return redirect('finance_settings')
    else:
        form = PaymentMethodForm()
    
    return render(request, 'backoffice/finance/form.html', {
        'title': 'Nuevo Método de Pago',
        'form': form,
        'back_url': 'finance_settings'
    })

@login_required
@require_gym_permission('finance.change_paymentmethod')
def method_edit(request, pk):
    gym = request.gym
    pm = get_object_or_404(PaymentMethod, pk=pk, gym=gym)
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=pm)
        if form.is_valid():
            form.save()
            messages.success(request, 'Método de pago actualizado.')
            return redirect('finance_settings')
    else:
        form = PaymentMethodForm(instance=pm)
    
    return render(request, 'backoffice/finance/form.html', {
        'title': f'Editar Método: {pm.name}',
        'form': form,
        'back_url': 'finance_settings'
    })

@login_required
@require_gym_permission('finance.delete_paymentmethod')
def method_delete(request, pk):
    gym = request.gym
    pm = get_object_or_404(PaymentMethod, pk=pk, gym=gym)
    if request.method == 'POST':
        pm.delete()
        messages.success(request, 'Método de pago eliminado.')
        return redirect('finance_settings')
    return render(request, 'backoffice/confirm_delete.html', {
        'title': 'Eliminar Método de Pago',
        'object': pm,
        'back_url': 'finance_settings'
    })
