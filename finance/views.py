from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import require_gym_permission
from .models import TaxRate, PaymentMethod, FinanceSettings, Supplier, ExpenseCategory, Expense
from providers.models import Provider
from .forms import (
    TaxRateForm,
    PaymentMethodForm,
    FinanceSettingsForm,
    GymOpeningHoursForm,
    AppSettingsForm,
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
    
    # Obtener o crear GamificationSettings
    from gamification.models import GamificationSettings
    gamification_settings, _ = GamificationSettings.objects.get_or_create(gym=gym)
    
    # Obtener campos personalizados del cliente
    from clients.models import ClientField
    client_fields = ClientField.objects.filter(gym=gym, is_active=True).order_by('display_order', 'name')

    if request.method == 'POST':
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
        
        # Guardar configuración de pasarela, permisos y gamificación
        elif 'save_app_settings' in request.POST:
            form = AppSettingsForm(request.POST, instance=finance_settings)
            if form.is_valid():
                form.save()
            
            # Guardar configuración de gamificación (tabla de clasificación)
            gamification_settings.hide_leaderboard_names = request.POST.get('hide_leaderboard_names') == 'on'
            gamification_settings.save()
            
            # Guardar configuración de gestión de cuotas
            # Nota: block_duplicate_membership es lo opuesto a allow_duplicate_membership_purchase
            portal_settings.allow_duplicate_membership_purchase = request.POST.get('block_duplicate_membership') != 'on'
            portal_settings.duplicate_membership_message = request.POST.get('duplicate_membership_message', '').strip()
            portal_settings.allow_membership_change_at_renewal = request.POST.get('allow_membership_change_at_renewal') == 'on'
            portal_settings.save()
            
            messages.success(request, 'Ajustes de la app del cliente actualizados.')
        
        return redirect('client_app_settings')
    else:
        form = AppSettingsForm(instance=finance_settings)

    context = {
        'title': 'App del Cliente',
        'form': form,
        'finance_settings': finance_settings,
        'portal_settings': portal_settings,
        'gamification_settings': gamification_settings,
        'client_fields': client_fields,
    }
    return render(request, 'backoffice/app/settings.html', context)

# --- Tax Rates ---

@login_required
@require_gym_permission('finance.change_taxrate')
def tax_create(request):
    gym = request.gym
    user = request.user
    
    # Check if user is franchise owner
    is_franchise_owner = gym.franchise and (user.is_superuser or user in gym.franchise.owners.all())
    
    if request.method == 'POST':
        form = TaxRateForm(request.POST, gym=gym, user=user)
        if form.is_valid():
            tax = form.save(commit=False)
            tax.gym = gym
            tax.save()
            
            # Handle franchise propagation
            if is_franchise_owner and 'propagate_to_gyms' in form.cleaned_data:
                target_gyms = form.cleaned_data['propagate_to_gyms']
                if target_gyms:
                    from services.franchise_service import FranchisePropagationService
                    results = FranchisePropagationService.propagate_tax_rate(tax, target_gyms)
                    if results['created'] or results['updated']:
                        messages.success(request, f'Impuesto propagado: {results["created"]} creados, {results["updated"]} actualizados.')
                    if results['errors']:
                        for error in results['errors']:
                            messages.warning(request, error)
            
            messages.success(request, 'Impuesto creado correctamente.')
            return redirect('finance_settings')
    else:
        form = TaxRateForm(gym=gym, user=user)
    
    return render(request, 'backoffice/finance/tax_form.html', {
        'title': 'Nuevo Impuesto',
        'form': form,
        'back_url': 'finance_settings',
        'is_franchise_owner': is_franchise_owner,
    })

@login_required
@require_gym_permission('finance.change_taxrate')
def tax_edit(request, pk):
    gym = request.gym
    user = request.user
    tax = get_object_or_404(TaxRate, pk=pk, gym=gym)
    
    # Check if user is franchise owner
    is_franchise_owner = gym.franchise and (user.is_superuser or user in gym.franchise.owners.all())
    
    if request.method == 'POST':
        form = TaxRateForm(request.POST, instance=tax, gym=gym, user=user)
        if form.is_valid():
            form.save()
            
            # Handle franchise propagation
            if is_franchise_owner and 'propagate_to_gyms' in form.cleaned_data:
                target_gyms = form.cleaned_data['propagate_to_gyms']
                if target_gyms:
                    from services.franchise_service import FranchisePropagationService
                    results = FranchisePropagationService.propagate_tax_rate(tax, target_gyms)
                    if results['created'] or results['updated']:
                        messages.success(request, f'Impuesto propagado: {results["created"]} creados, {results["updated"]} actualizados.')
                    if results['errors']:
                        for error in results['errors']:
                            messages.warning(request, error)
            
            messages.success(request, 'Impuesto actualizado correctamente.')
            return redirect('finance_settings')
    else:
        form = TaxRateForm(instance=tax, gym=gym, user=user)
    
    return render(request, 'backoffice/finance/tax_form.html', {
        'title': f'Editar Impuesto: {tax.name}',
        'form': form,
        'back_url': 'finance_settings',
        'is_franchise_owner': is_franchise_owner,
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
    expenses = Expense.objects.filter(gym=gym).select_related('provider', 'category', 'payment_method', 'created_by')
    
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
    provider_id = request.GET.get('provider')
    category_id = request.GET.get('category')
    status = request.GET.get('status')
    is_recurring = request.GET.get('is_recurring')
    
    if provider_id:
        expenses = expenses.filter(provider_id=provider_id)
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
    
    # Para los filtros - usar Provider
    providers = Provider.objects.filter(gym=gym, is_active=True)
    categories = ExpenseCategory.objects.filter(gym=gym, is_active=True)
    
    context = {
        'title': 'Gestión de Gastos',
        'expenses': expenses.order_by('-issue_date'),
        'stats': stats,
        'pending_count': pending_count,
        'overdue_count': overdue_count,
        'providers': providers,
        'categories': categories,
        'STATUS_CHOICES': Expense.STATUS_CHOICES,
        # Mantener filtros en el contexto
        'filter_date_from': date_from,
        'filter_date_to': date_to,
        'filter_provider': provider_id,
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


# ============================================
# STRIPE MIGRATION - Importar clientes con tarjetas
# ============================================

@login_required
@require_gym_permission('finance.change_finance')
def stripe_migration(request):
    """Vista para migrar clientes desde otro software que usa Stripe"""
    gym = request.gym
    finance_settings = FinanceSettings.objects.filter(gym=gym).first()
    
    # Verificar que Stripe está configurado
    stripe_configured = finance_settings and finance_settings.stripe_secret_key
    
    context = {
        'title': 'Migración desde Stripe',
        'stripe_configured': stripe_configured,
        'results': None,
    }
    
    if request.method == 'POST' and 'import_csv' in request.POST:
        if not stripe_configured:
            messages.error(request, 'Debes configurar las claves de Stripe primero.')
            return redirect('stripe_migration')
        
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Selecciona un archivo CSV.')
            return redirect('stripe_migration')
        
        import csv
        import io
        import stripe
        
        # Configurar Stripe
        stripe.api_key = finance_settings.stripe_secret_key
        
        # Leer CSV - detectar delimitador automáticamente
        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
            
            # Detectar delimitador (Stripe usa coma, nuestro formato usa punto y coma)
            first_line = decoded_file.split('\n')[0]
            delimiter = ',' if ',' in first_line and ';' not in first_line else ';'
            
            reader = csv.DictReader(io.StringIO(decoded_file), delimiter=delimiter)
            
            # Detectar formato: Stripe nativo tiene 'id' como columna, nuestro formato tiene 'stripe_customer_id'
            fieldnames = reader.fieldnames or []
            is_stripe_native = 'id' in fieldnames and 'stripe_customer_id' not in fieldnames
            
            results = {
                'total': 0,
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'errors': [],
                'details': [],
                'format': 'Stripe Nativo' if is_stripe_native else 'Personalizado'
            }
            
            from clients.models import Client
            
            for row in reader:
                results['total'] += 1
                
                # Mapear campos según el formato detectado
                if is_stripe_native:
                    # Formato nativo de Stripe: id, email, name, phone, created, etc.
                    stripe_customer_id = row.get('id', '').strip()
                    email = row.get('email', '').strip()
                    full_name = row.get('name', '').strip()
                    phone = row.get('phone', '').strip()
                    
                    # Separar nombre completo
                    name_parts = full_name.split() if full_name else []
                    first_name = name_parts[0] if name_parts else ''
                    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                else:
                    # Formato personalizado
                    email = row.get('email', '').strip()
                    first_name = row.get('nombre', row.get('first_name', '')).strip()
                    last_name = row.get('apellidos', row.get('last_name', '')).strip()
                    stripe_customer_id = row.get('stripe_customer_id', row.get('stripe_id', row.get('id', ''))).strip()
                    phone = row.get('telefono', row.get('phone', '')).strip()
                
                if not email:
                    results['errors'].append(f"Fila {results['total']}: Email vacío")
                    results['skipped'] += 1
                    continue
                
                if not stripe_customer_id:
                    results['errors'].append(f"Fila {results['total']} ({email}): stripe_customer_id vacío")
                    results['skipped'] += 1
                    continue
                
                # Validar que el customer existe en Stripe
                try:
                    stripe_customer = stripe.Customer.retrieve(stripe_customer_id)
                    if stripe_customer.get('deleted'):
                        results['errors'].append(f"{email}: Cliente eliminado en Stripe")
                        results['skipped'] += 1
                        continue
                except stripe.error.InvalidRequestError:
                    results['errors'].append(f"{email}: stripe_customer_id '{stripe_customer_id}' no existe en Stripe")
                    results['skipped'] += 1
                    continue
                except Exception as e:
                    results['errors'].append(f"{email}: Error validando Stripe - {str(e)}")
                    results['skipped'] += 1
                    continue
                
                # Buscar o crear cliente
                client, created = Client.objects.get_or_create(
                    gym=gym,
                    email=email,
                    defaults={
                        'first_name': first_name or stripe_customer.get('name', '').split()[0] if stripe_customer.get('name') else 'Sin nombre',
                        'last_name': last_name or ' '.join(stripe_customer.get('name', '').split()[1:]) if stripe_customer.get('name') else '',
                        'phone': phone or stripe_customer.get('phone', ''),
                        'stripe_customer_id': stripe_customer_id,
                        'preferred_gateway': 'STRIPE',
                        'status': Client.Status.ACTIVE,
                    }
                )
                
                if created:
                    results['created'] += 1
                    results['details'].append(f"✅ Creado: {email} → {stripe_customer_id}")
                else:
                    # Actualizar stripe_customer_id si no lo tiene
                    if not client.stripe_customer_id:
                        client.stripe_customer_id = stripe_customer_id
                        client.preferred_gateway = 'STRIPE'
                        client.save()
                        results['updated'] += 1
                        results['details'].append(f"🔄 Actualizado: {email} → {stripe_customer_id}")
                    elif client.stripe_customer_id == stripe_customer_id:
                        results['details'].append(f"⏭️ Ya existe: {email}")
                        results['skipped'] += 1
                    else:
                        results['errors'].append(f"{email}: Ya tiene otro stripe_customer_id ({client.stripe_customer_id})")
                        results['skipped'] += 1
            
            context['results'] = results
            
            if results['created'] > 0 or results['updated'] > 0:
                messages.success(request, f"Importación completada: {results['created']} creados, {results['updated']} actualizados.")
            else:
                messages.info(request, "No se realizaron cambios.")
                
        except Exception as e:
            messages.error(request, f'Error procesando CSV: {str(e)}')
    
    return render(request, 'backoffice/finance/stripe_migration.html', context)


@login_required
@require_gym_permission('finance.view_finance')
def stripe_migration_template(request):
    """Descarga plantilla CSV para migración de Stripe"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="plantilla_migracion_stripe.csv"'
    response.write('\ufeff')  # BOM for Excel
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['email', 'nombre', 'apellidos', 'telefono', 'stripe_customer_id'])
    writer.writerow(['cliente@ejemplo.com', 'Juan', 'García López', '612345678', 'cus_ABC123xyz'])
    writer.writerow(['otro@ejemplo.com', 'María', 'Pérez', '698765432', 'cus_DEF456abc'])
    
    return response

