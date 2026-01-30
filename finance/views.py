from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import require_gym_permission
from .models import TaxRate, PaymentMethod, FinanceSettings, Supplier, ExpenseCategory, Expense
from .forms import (
    TaxRateForm,
    PaymentMethodForm,
    FinanceSettingsForm,
    GymOpeningHoursForm,
    AppSettingsForm,
    SupplierForm,
    ExpenseCategoryForm,
    ExpenseForm,
    ExpenseQuickPayForm,
)
from datetime import datetime, timedelta, date
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from sales.models import Order
from django.utils import timezone
from django.http import JsonResponse

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


@login_required
@require_gym_permission('finance.view_finance')
def client_app_settings(request):
    gym = request.gym
    finance_settings, _ = FinanceSettings.objects.get_or_create(gym=gym)
    
    # Obtener o crear PublicPortalSettings
    from organizations.models import PublicPortalSettings
    portal_settings, _ = PublicPortalSettings.objects.get_or_create(
        gym=gym,
        defaults={'public_slug': gym.name.lower().replace(' ', '-')[:50]}
    )
    
    # Obtener campos personalizados del cliente
    from clients.models import ClientField
    client_fields = ClientField.objects.filter(gym=gym, is_active=True).order_by('display_order', 'name')

    if request.method == 'POST':
        # Guardar configuración de pasarela y permisos
        form = AppSettingsForm(request.POST, instance=finance_settings)
        if form.is_valid():
            form.save()
        
        # Guardar configuración de registro
        if 'save_registration_settings' in request.POST:
            portal_settings.allow_self_registration = request.POST.get('allow_self_registration') == 'on'
            portal_settings.require_email_verification = request.POST.get('require_email_verification') == 'on'
            portal_settings.require_staff_approval = request.POST.get('require_staff_approval') == 'on'
            portal_settings.save()
            
            # Guardar campos seleccionados para registro
            selected_field_ids = request.POST.getlist('registration_fields')
            for field in client_fields:
                field.show_in_registration = str(field.id) in selected_field_ids
                field.save()
            
            messages.success(request, 'Configuración de registro actualizada.')
        else:
            messages.success(request, 'Ajustes de la app del cliente actualizados.')
        
        return redirect('client_app_settings')
    else:
        form = AppSettingsForm(instance=finance_settings)

    context = {
        'title': 'App del Cliente',
        'form': form,
        'finance_settings': finance_settings,
        'portal_settings': portal_settings,
        'client_fields': client_fields,
    }
    return render(request, 'backoffice/app/settings.html', context)

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

# --- Reports ---

@login_required
@require_gym_permission('finance.view_finance')
def billing_dashboard(request):
    gym = request.gym
    
    # 1. Date Filters
    date_range = request.GET.get('range', 'month') # today, yesterday, week, month, custom
    date_start_str = request.GET.get('start')
    date_end_str = request.GET.get('end')
    
    today = date.today()
    start_date = today.replace(day=1)  # Default to start of current month
    end_date = today # Inclusive
    
    if date_range == 'today':
        start_date = today
        end_date = today
    elif date_range == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = start_date
    elif date_range == 'week':
        start_date = today - timedelta(days=7)
    elif date_range == 'month':
        start_date = today.replace(day=1)
    elif date_range == 'custom' and date_start_str:
        try:
            start_date = datetime.strptime(date_start_str, '%Y-%m-%d').date()
            if date_end_str:
                end_date = datetime.strptime(date_end_str, '%Y-%m-%d').date()
            else:
                end_date = start_date
        except ValueError:
            pass
            
    # Queryset
    # Filter by created_at range (inclusive)
    # created_at is DateTime, so we need (start 00:00, end 23:59)
    orders_qs = Order.objects.filter(
        gym=gym,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).exclude(status='CANCELLED').select_related('client', 'created_by').prefetch_related('payments__payment_method')
    
    # 2. Aggregates (KPIs)
    # Use the base queryset for metrics
    aggregates = orders_qs.aggregate(
        total_income=Sum('total_amount'),
        total_tax=Sum('total_tax'),
        total_base=Sum('total_base'),
        count=Count('id')
    )
    
    # 3. Chart Data - Multiple Granularities
    # Daily data
    daily_data = orders_qs.annotate(day=TruncDate('created_at')).values('day').annotate(total=Sum('total_amount')).order_by('day')
    
    daily_labels = []
    daily_values = []
    for entry in daily_data:
        daily_labels.append(entry['day'].strftime('%d/%m'))
        daily_values.append(float(entry['total']) if entry['total'] else 0)
    
    # Monthly data (for year view)
    monthly_data = orders_qs.annotate(month=TruncMonth('created_at')).values('month').annotate(total=Sum('total_amount')).order_by('month')
    
    monthly_labels = []
    monthly_values = []
    for entry in monthly_data:
        monthly_labels.append(entry['month'].strftime('%b %Y'))
        monthly_values.append(float(entry['total']) if entry['total'] else 0)
        
    # 4. Filters (for dropdowns)
    payment_methods = PaymentMethod.objects.filter(gym=gym, is_active=True)
    
    # 5. Scheduled Payments (Cobros Futuros / Recurrentes)
    from clients.models import ClientMembership
    
    # Filter scheduled payments by date range if provided
    scheduled_range = request.GET.get('scheduled_range', 'month')
    scheduled_start = today  # Always start from today
    # Default: until end of current month
    scheduled_end = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    if scheduled_range == 'today':
        scheduled_end = today
    elif scheduled_range == 'week':
        scheduled_end = today + timedelta(days=7)
    elif scheduled_range == 'month':
        # Until end of current month
        scheduled_end = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # Get scheduled payments - Remove is_recurring filter to get all active memberships
    scheduled_payments = ClientMembership.objects.filter(
        client__gym=gym,
        status='ACTIVE',
        end_date__gte=scheduled_start,  # End date >= today
        end_date__lte=scheduled_end      # End date <= range end
    ).select_related('client').order_by('end_date')
    
    # If no results with these filters, broaden to show more data
    if not scheduled_payments.exists():
        scheduled_payments = ClientMembership.objects.filter(
            client__gym=gym,
            status='ACTIVE'
        ).select_related('client').order_by('-end_date')[:20]  # Show last 20 active memberships

    # 6. Deferred Orders (Ventas Diferidas)
    deferred_orders = Order.objects.filter(
        gym=gym,
        status='DEFERRED',
        scheduled_payment_date__isnull=False
    ).select_related('client', 'created_by').order_by('scheduled_payment_date')
    
    # Filter by scheduled payment date if range filter provided
    if scheduled_range == 'today':
        deferred_orders = deferred_orders.filter(scheduled_payment_date=today)
    elif scheduled_range == 'week':
        deferred_orders = deferred_orders.filter(
            scheduled_payment_date__gte=today,
            scheduled_payment_date__lte=today + timedelta(days=7)
        )
    elif scheduled_range == 'month':
        deferred_orders = deferred_orders.filter(
            scheduled_payment_date__gte=today,
            scheduled_payment_date__lte=scheduled_end
        )

    # 7. Create a dict of client_id -> deferred orders count for quick lookup in template
    all_deferred_for_gym = Order.objects.filter(
        gym=gym,
        status='DEFERRED',
        client__isnull=False
    ).values('client_id').annotate(count=Count('id'))
    
    client_deferred_counts = {item['client_id']: item['count'] for item in all_deferred_for_gym}

    context = {
        'title': 'Informe de Facturación',
        'orders': orders_qs.order_by('-created_at'), # Pass explicit queryset
        'scheduled_payments': scheduled_payments,
        'deferred_orders': deferred_orders,
        'client_deferred_counts': client_deferred_counts,
        'today': today,  # For template date comparisons
        'metrics': {
            'total': aggregates['total_income'] or 0,
            'tax': aggregates['total_tax'] or 0,
            'base': aggregates['total_base'] or 0,
            'count': aggregates['count'] or 0
        },
        'chart': {
            'daily': {
                'labels': daily_labels,
                'values': daily_values
            },
            'monthly': {
                'labels': monthly_labels,
                'values': monthly_values
            }
        },
        'filters': {
            'range': date_range,
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'methods': payment_methods,
            'scheduled_range': scheduled_range
        },
        'debug_start': start_date,
        'debug_end': end_date
    }
    
    return render(request, 'backoffice/finance/billing_dashboard.html', context)
@login_required
@require_gym_permission('finance.change_financesettings')
def hardware_settings(request):
    """
    Manage POS Hardware (Terminals, Printers).
    """
    from .models import PosDevice
    gym = request.gym
    devices = PosDevice.objects.filter(gym=gym).order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            name = request.POST.get('name')
            device_type = request.POST.get('device_type')
            identifier = request.POST.get('identifier')
            if name and device_type:
                PosDevice.objects.create(gym=gym, name=name, device_type=device_type, identifier=identifier)
                messages.success(request, 'Dispositivo añadido correctamente')
            else:
                messages.error(request, 'Faltan datos obligatorios')
                
        elif action == 'delete':
            device_id = request.POST.get('device_id')
            PosDevice.objects.filter(gym=gym, id=device_id).delete()
            messages.success(request, 'Dispositivo eliminado')
            
        return redirect('hardware_settings')
            
    return render(request, 'backoffice/settings/system/hardware.html', {
        'devices': devices,
        'device_types': PosDevice.msg_types
    })


# --- Gym Opening Hours ---

@login_required
@require_gym_permission('finance.view_finance')
def gym_opening_hours(request):
    """Vista para editar horarios de apertura del gym"""
    from organizations.models import GymOpeningHours
    
    gym = request.gym
    
    # Obtener o crear horarios (OneToOne relation)
    opening_hours, created = GymOpeningHours.objects.get_or_create(gym=gym)
    
    if request.method == 'POST':
        form = GymOpeningHoursForm(request.POST, instance=opening_hours)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Horarios de apertura actualizados correctamente')
            return redirect('gym_opening_hours')
    else:
        form = GymOpeningHoursForm(instance=opening_hours)
    
    context = {
        'title': 'Horarios de Apertura',
        'form': form,
        'gym': gym,
        'opening_hours': opening_hours,
    }
    return render(request, 'backoffice/finance/opening_hours.html', context)


# ==================== EXPENSE MANAGEMENT ====================

@login_required
@require_gym_permission('finance.view_finance')
def expense_list(request):
    """Listado de gastos con filtros avanzados"""
    gym = request.gym
    expenses = Expense.objects.filter(gym=gym).select_related('supplier', 'category', 'payment_method', 'created_by')
    
    # Filtros rápidos de fecha
    date_filter = request.GET.get('date_filter')
    today = timezone.now().date()
    
    if date_filter == 'today':
        date_from = date_to = today
        expenses = expenses.filter(issue_date=today)
    elif date_filter == 'week':
        date_from = today - timedelta(days=today.weekday())  # Lunes de esta semana
        date_to = date_from + timedelta(days=6)  # Domingo
        expenses = expenses.filter(issue_date__range=[date_from, date_to])
    elif date_filter == 'month':
        date_from = today.replace(day=1)
        # Último día del mes
        if today.month == 12:
            date_to = today.replace(month=12, day=31)
        else:
            date_to = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        expenses = expenses.filter(issue_date__range=[date_from, date_to])
    elif date_filter == 'quarter':
        quarter = (today.month - 1) // 3
        date_from = today.replace(month=quarter * 3 + 1, day=1)
        if quarter == 3:
            date_to = today.replace(month=12, day=31)
        else:
            date_to = (today.replace(month=(quarter + 1) * 3 + 1, day=1) - timedelta(days=1))
        expenses = expenses.filter(issue_date__range=[date_from, date_to])
    else:
        # Filtros personalizados
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if date_from:
            expenses = expenses.filter(issue_date__gte=date_from)
        if date_to:
            expenses = expenses.filter(issue_date__lte=date_to)
    
    # Otros filtros
    supplier_id = request.GET.get('supplier')
    category_id = request.GET.get('category')
    status = request.GET.get('status')
    is_recurring = request.GET.get('is_recurring')
    
    if supplier_id:
        expenses = expenses.filter(supplier_id=supplier_id)
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    if status:
        expenses = expenses.filter(status=status)
    if is_recurring:
        expenses = expenses.filter(is_recurring=is_recurring == 'yes')
    
    # Estadísticas
    stats = expenses.aggregate(
        total_base=Sum('base_amount'),
        total_tax=Sum('tax_amount'),
        total=Sum('total_amount'),
        total_paid=Sum('paid_amount'),
        count=Count('id')
    )
    
    # Gastos pendientes y vencidos
    pending_count = expenses.filter(status='PENDING').count()
    overdue_count = expenses.filter(status='OVERDUE').count()
    
    # Para los filtros
    suppliers = Supplier.objects.filter(gym=gym, is_active=True)
    categories = ExpenseCategory.objects.filter(gym=gym, is_active=True)
    
    context = {
        'title': 'Gestión de Gastos',
        'expenses': expenses.order_by('-issue_date'),
        'stats': stats,
        'pending_count': pending_count,
        'overdue_count': overdue_count,
        'suppliers': suppliers,
        'categories': categories,
        'STATUS_CHOICES': Expense.STATUS_CHOICES,
        # Mantener filtros en el contexto
        'filter_date_from': date_from,
        'filter_date_to': date_to,
        'filter_supplier': supplier_id,
        'filter_category': category_id,
        'filter_status': status,
        'filter_is_recurring': is_recurring,
    }
    return render(request, 'backoffice/finance/expense_list.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def expense_create(request):
    """Crear nuevo gasto"""
    gym = request.gym
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, gym=gym)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.gym = gym
            expense.created_by = request.user
            expense.save()
            form.save_m2m()  # Guardar productos relacionados
            
            messages.success(request, f'✅ Gasto "{expense.concept}" creado correctamente')
            return redirect('expense_list')
    else:
        form = ExpenseForm(gym=gym)
    
    context = {
        'title': 'Nuevo Gasto',
        'form': form,
        'is_edit': False,
    }
    return render(request, 'backoffice/finance/expense_form.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def expense_edit(request, pk):
    """Editar gasto existente"""
    gym = request.gym
    expense = get_object_or_404(Expense, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense, gym=gym)
        if form.is_valid():
            expense = form.save()
            messages.success(request, f'✅ Gasto "{expense.concept}" actualizado correctamente')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense, gym=gym)
    
    context = {
        'title': f'Editar: {expense.concept}',
        'form': form,
        'expense': expense,
        'is_edit': True,
    }
    return render(request, 'backoffice/finance/expense_form.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def expense_delete(request, pk):
    """Eliminar gasto"""
    gym = request.gym
    expense = get_object_or_404(Expense, pk=pk, gym=gym)
    
    if request.method == 'POST':
        concept = expense.concept
        expense.delete()
        messages.success(request, f'✅ Gasto "{concept}" eliminado correctamente')
        return redirect('expense_list')
    
    context = {
        'title': 'Confirmar Eliminación',
        'expense': expense,
    }
    return render(request, 'backoffice/finance/expense_confirm_delete.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def expense_mark_paid(request, pk):
    """Marcar gasto como pagado (quick action)"""
    gym = request.gym
    expense = get_object_or_404(Expense, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = ExpenseQuickPayForm(request.POST, gym=gym)
        if form.is_valid():
            payment_date = form.cleaned_data.get('payment_date') or timezone.now().date()
            payment_method = form.cleaned_data.get('payment_method')
            
            expense.mark_as_paid(payment_date=payment_date, payment_method=payment_method)
            messages.success(request, f'✅ Gasto "{expense.concept}" marcado como pagado')
            return redirect('expense_list')
    else:
        form = ExpenseQuickPayForm(gym=gym)
    
    context = {
        'expense': expense,
        'form': form,
    }
    return render(request, 'backoffice/finance/expense_mark_paid_modal.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def expense_generate_recurring(request):
    """Generar gastos recurrentes pendientes (cron job o manual)"""
    gym = request.gym
    generated_count = 0
    
    # Buscar gastos recurrentes que necesitan generar nueva ocurrencia
    recurring_expenses = Expense.objects.filter(
        gym=gym,
        is_recurring=True,
        is_active_recurrence=True,
        next_generation_date__lte=timezone.now().date()
    )
    
    for expense in recurring_expenses:
        new_expense = expense.generate_next_occurrence()
        if new_expense:
            generated_count += 1
    
    if generated_count > 0:
        messages.success(request, f'✅ Se generaron {generated_count} gasto(s) recurrente(s)')
    else:
        messages.info(request, 'No hay gastos recurrentes pendientes de generar')
    
    return redirect('expense_list')


# ==================== SUPPLIER MANAGEMENT ====================

@login_required
@require_gym_permission('finance.view_finance')
def supplier_list(request):
    """Listado de proveedores"""
    gym = request.gym
    suppliers = Supplier.objects.filter(gym=gym).order_by('name')
    
    context = {
        'title': 'Proveedores',
        'suppliers': suppliers,
    }
    return render(request, 'backoffice/finance/supplier_list.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def supplier_create(request):
    """Crear nuevo proveedor"""
    gym = request.gym
    
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.gym = gym
            supplier.save()
            messages.success(request, f'✅ Proveedor "{supplier.name}" creado correctamente')
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    
    context = {
        'title': 'Nuevo Proveedor',
        'form': form,
    }
    return render(request, 'backoffice/finance/supplier_form.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def supplier_edit(request, pk):
    """Editar proveedor"""
    gym = request.gym
    supplier = get_object_or_404(Supplier, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'✅ Proveedor "{supplier.name}" actualizado correctamente')
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    
    context = {
        'title': f'Editar: {supplier.name}',
        'form': form,
        'supplier': supplier,
    }
    return render(request, 'backoffice/finance/supplier_form.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def supplier_delete(request, pk):
    """Eliminar proveedor (soft delete)"""
    gym = request.gym
    supplier = get_object_or_404(Supplier, pk=pk, gym=gym)
    
    if request.method == 'POST':
        supplier.is_active = False
        supplier.save()
        messages.success(request, f'✅ Proveedor "{supplier.name}" desactivado')
        return redirect('supplier_list')
    
    context = {
        'title': 'Confirmar Desactivación',
        'supplier': supplier,
    }
    return render(request, 'backoffice/finance/supplier_confirm_delete.html', context)


# ==================== CATEGORY MANAGEMENT ====================

@login_required
@require_gym_permission('finance.view_finance')
def category_list(request):
    """Listado de categorías de gastos"""
    gym = request.gym
    categories = ExpenseCategory.objects.filter(gym=gym).order_by('name')
    
    context = {
        'title': 'Categorías de Gastos',
        'categories': categories,
    }
    return render(request, 'backoffice/finance/category_list.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def category_create(request):
    """Crear nueva categoría"""
    gym = request.gym
    
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.gym = gym
            category.save()
            messages.success(request, f'✅ Categoría "{category.name}" creada correctamente')
            return redirect('category_list')
    else:
        form = ExpenseCategoryForm()
    
    context = {
        'title': 'Nueva Categoría',
        'form': form,
    }
    return render(request, 'backoffice/finance/category_form.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def category_edit(request, pk):
    """Editar categoría"""
    gym = request.gym
    category = get_object_or_404(ExpenseCategory, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'✅ Categoría "{category.name}" actualizada correctamente')
            return redirect('category_list')
    else:
        form = ExpenseCategoryForm(instance=category)
    
    context = {
        'title': f'Editar: {category.name}',
        'form': form,
        'category': category,
    }
    return render(request, 'backoffice/finance/category_form.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def category_delete(request, pk):
    """Eliminar categoría (soft delete)"""
    gym = request.gym
    category = get_object_or_404(ExpenseCategory, pk=pk, gym=gym)
    
    if request.method == 'POST':
        category.is_active = False
        category.save()
        messages.success(request, f'✅ Categoría "{category.name}" desactivada')
        return redirect('category_list')
    
    context = {
        'title': 'Confirmar Desactivación',
        'category': category,
    }
    return render(request, 'backoffice/finance/category_confirm_delete.html', context)


# ==========================================
# EXPORT FUNCTIONS
# ==========================================
from core.export_service import GenericExportService, ExportConfig


@login_required
@require_gym_permission('finance.view_finance')
def expense_export_excel(request):
    """Exporta listado de gastos a Excel"""
    gym = request.gym
    expenses = Expense.objects.filter(gym=gym).select_related('supplier', 'category')
    
    # Aplicar filtros si existen
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    
    if date_from:
        expenses = expenses.filter(issue_date__gte=date_from)
    if date_to:
        expenses = expenses.filter(issue_date__lte=date_to)
    if status:
        expenses = expenses.filter(status=status)
    
    # Calcular totales
    totals = expenses.aggregate(
        total_base=Sum('base_amount'),
        total_tax=Sum('tax_amount'),
        total=Sum('total_amount')
    )
    
    config = ExportConfig(
        title="Listado de Gastos",
        headers=['ID', 'Fecha', 'Proveedor', 'Concepto', 'Categoría', 'Base', 'IVA', 'Total', 'Estado'],
        data_extractor=lambda e: [
            e.id,
            e.issue_date,
            e.supplier.name if e.supplier else '-',
            e.concept[:40] + '...' if len(e.concept) > 40 else e.concept,
            e.category.name if e.category else '-',
            e.base_amount,
            e.tax_amount,
            e.total_amount,
            e.get_status_display(),
        ],
        column_widths=[8, 12, 18, 25, 15, 12, 10, 12, 12],
        landscape_mode=True,
        footer_text=f"TOTALES: Base: {totals['total_base'] or 0:.2f}€ | IVA: {totals['total_tax'] or 0:.2f}€ | Total: {totals['total'] or 0:.2f}€"
    )
    
    excel_file = GenericExportService.export_to_excel(expenses.order_by('-issue_date'), config, gym.name)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="gastos_{gym.name}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
@require_gym_permission('finance.view_finance')
def expense_export_pdf(request):
    """Exporta listado de gastos a PDF"""
    gym = request.gym
    expenses = Expense.objects.filter(gym=gym).select_related('supplier', 'category')
    
    # Aplicar filtros si existen
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    
    if date_from:
        expenses = expenses.filter(issue_date__gte=date_from)
    if date_to:
        expenses = expenses.filter(issue_date__lte=date_to)
    if status:
        expenses = expenses.filter(status=status)
    
    # Calcular totales
    totals = expenses.aggregate(
        total_base=Sum('base_amount'),
        total_tax=Sum('tax_amount'),
        total=Sum('total_amount')
    )
    
    config = ExportConfig(
        title="Listado de Gastos",
        headers=['Fecha', 'Proveedor', 'Concepto', 'Base', 'IVA', 'Total', 'Estado'],
        data_extractor=lambda e: [
            e.issue_date,
            e.supplier.name if e.supplier else '-',
            e.concept[:30] + '...' if len(e.concept) > 30 else e.concept,
            e.base_amount,
            e.tax_amount,
            e.total_amount,
            e.get_status_display(),
        ],
        column_widths=[12, 18, 25, 12, 10, 12, 12],
        landscape_mode=True,
        footer_text=f"TOTALES: Base: {totals['total_base'] or 0:.2f}€ | IVA: {totals['total_tax'] or 0:.2f}€ | Total: {totals['total'] or 0:.2f}€"
    )
    
    pdf_file = GenericExportService.export_to_pdf(expenses.order_by('-issue_date'), config, gym.name)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="gastos_{gym.name}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response


@login_required
@require_gym_permission('finance.view_finance')
def supplier_export_excel(request):
    """Exporta listado de proveedores a Excel"""
    gym = request.gym
    suppliers = Supplier.objects.filter(gym=gym)
    
    config = ExportConfig(
        title="Listado de Proveedores",
        headers=['ID', 'Nombre', 'CIF/NIF', 'Email', 'Teléfono', 'Dirección', 'Estado'],
        data_extractor=lambda s: [
            s.id,
            s.name,
            s.tax_id or '-',
            s.email or '-',
            s.phone or '-',
            s.address or '-',
            'Activo' if s.is_active else 'Inactivo',
        ],
        column_widths=[8, 20, 15, 25, 15, 30, 10]
    )
    
    excel_file = GenericExportService.export_to_excel(suppliers.order_by('name'), config, gym.name)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="proveedores_{gym.name}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
@require_gym_permission('finance.view_finance')
def supplier_export_pdf(request):
    """Exporta listado de proveedores a PDF"""
    gym = request.gym
    suppliers = Supplier.objects.filter(gym=gym)
    
    config = ExportConfig(
        title="Listado de Proveedores",
        headers=['Nombre', 'CIF/NIF', 'Email', 'Teléfono', 'Estado'],
        data_extractor=lambda s: [
            s.name,
            s.tax_id or '-',
            s.email or '-',
            s.phone or '-',
            'Activo' if s.is_active else 'Inactivo',
        ],
        column_widths=[25, 15, 25, 15, 10]
    )
    
    pdf_file = GenericExportService.export_to_pdf(suppliers.order_by('name'), config, gym.name)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="proveedores_{gym.name}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response
