"""
Superadmin panel views.
Dashboard, gym/franchise management, subscription plans, billing config, audit logs.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal

from .decorators import superuser_required, log_superadmin_action
from .forms import FranchiseForm, GymCreationForm
from organizations.models import Gym, Franchise
from saas_billing.models import (
    SubscriptionPlan, GymSubscription, FranchiseSubscription,
    Invoice, BillingConfig, AuditLog
)
from saas_billing.migration_service import MigrationService
from saas_billing.health import health_monitor
from clients.models import Client


@superuser_required
def dashboard(request):
    """
    Superadmin dashboard with KPIs and overview.
    """
    # Calculate KPIs
    total_gyms = Gym.objects.count()
    active_gyms = GymSubscription.objects.filter(status='ACTIVE').count()
    suspended_gyms = GymSubscription.objects.filter(status='SUSPENDED').count()
    past_due_gyms = GymSubscription.objects.filter(status='PAST_DUE').count()
    
    # Revenue metrics
    current_month_start = date.today().replace(day=1)
    monthly_revenue = Invoice.objects.filter(
        status='PAID',
        paid_date__gte=current_month_start
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # MRR (Monthly Recurring Revenue) - sum of all active monthly subscriptions
    mrr = GymSubscription.objects.filter(
        status='ACTIVE',
        billing_frequency='MONTHLY'
    ).select_related('plan').aggregate(
        total=Sum('plan__price_monthly')
    )['total'] or Decimal('0.00')
    
    # ARR (Annual Recurring Revenue)
    arr = mrr * 12
    
    # Churn rate (gyms cancelled this month)
    cancelled_this_month = GymSubscription.objects.filter(
        status='CANCELLED',
        updated_at__gte=current_month_start
    ).count()
    churn_rate = (cancelled_this_month / total_gyms * 100) if total_gyms > 0 else 0
    
    # System health status
    health_status = health_monitor._calculate_overall_status()
    
    # Recent activity
    recent_gyms = Gym.objects.order_by('-created_at')[:5]
    recent_invoices = Invoice.objects.select_related('gym', 'franchise').order_by('-created_at')[:10]
    recent_logs = AuditLog.objects.select_related('superadmin', 'target_gym').order_by('-created_at')[:15]
    
    # Subscription plan distribution
    plan_distribution = GymSubscription.objects.values('plan__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'total_gyms': total_gyms,
        'active_gyms': active_gyms,
        'suspended_gyms': suspended_gyms,
        'past_due_gyms': past_due_gyms,
        'monthly_revenue': f"{monthly_revenue:.2f}",
        'mrr': f"{mrr:.2f}",
        'arr': f"{arr:.2f}",
        'churn_rate': f"{churn_rate:.1f}",
        'health_status': health_status,
        'recent_gyms': recent_gyms,
        'recent_invoices': recent_invoices,
        'recent_logs': recent_logs,
        'plan_distribution': plan_distribution,
    }
    
    return render(request, 'superadmin/dashboard.html', context)


@superuser_required
def gym_create(request):
    """
    Create a new gym.
    """
    if request.method == 'POST':
        form = GymCreationForm(request.POST)
        if form.is_valid():
            gym = form.save()
            messages.success(request, f"Gimnasio '{gym.name}' creado exitosamente")
            return redirect('superadmin:gym_detail', gym_id=gym.id)
    else:
        form = GymCreationForm()
    
    return render(request, 'superadmin/gyms/form.html', {'form': form})


@superuser_required
def gym_list(request):
    """
    List all gyms with search and filters.
    """
    gyms = Gym.objects.select_related('franchise', 'subscription__plan').all()
    
    # Search
    search = request.GET.get('search', '')
    if search:
        gyms = gyms.filter(
            Q(name__icontains=search) |
            Q(commercial_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    # Filter by subscription status
    status_filter = request.GET.get('status', '')
    if status_filter:
        gyms = gyms.filter(subscription__status=status_filter)
    
    # Filter by plan
    plan_filter = request.GET.get('plan', '')
    if plan_filter:
        gyms = gyms.filter(subscription__plan_id=plan_filter)
    
    # Get all plans for filter dropdown
    plans = SubscriptionPlan.objects.filter(is_active=True)
    
    context = {
        'gyms': gyms,
        'plans': plans,
        'search': search,
        'status_filter': status_filter,
        'plan_filter': plan_filter,
        'status_choices': GymSubscription.STATUS_CHOICES,
    }
    
    return render(request, 'superadmin/gyms/list.html', context)


@superuser_required
def gym_detail(request, gym_id):
    """
    View gym details including subscription, usage, invoices.
    """
    gym = get_object_or_404(Gym, id=gym_id)
    
    # Get subscription if exists
    subscription = None
    try:
        subscription = gym.subscription
    except GymSubscription.DoesNotExist:
        pass
    
    # Usage stats
    total_members = Client.objects.filter(gym=gym, status='ACTIVE').count()
    total_staff = gym.staff.count()
    
    # Invoices
    invoices = Invoice.objects.filter(gym=gym).order_by('-created_at')[:10]
    
    # Audit logs for this gym
    logs = AuditLog.objects.filter(target_gym=gym).order_by('-created_at')[:20]
    
    context = {
        'gym': gym,
        'subscription': subscription,
        'total_members': total_members,
        'total_staff': total_staff,
        'invoices': invoices,
        'logs': logs,
    }
    
    return render(request, 'superadmin/gyms/detail.html', context)


@superuser_required
@log_superadmin_action('GOD_MODE_LOGIN', 'Accesed gym as regular admin')
def gym_login_as_admin(request, gym_id):
    """
    God Mode: Login as the gym owner/admin to inspect their dashboard.
    Sets session variables to impersonate the gym environment.
    """
    gym = get_object_or_404(Gym, id=gym_id)
    
    # Set session for gym context
    request.session['current_gym_id'] = gym.id
    request.session['is_god_mode'] = True
    request.session['original_admin_id'] = request.user.id
    
    messages.warning(request, f"⚡ MODO DIOS ACTIVO: Has accedido como administrador de {gym.name}")
    return redirect('backoffice:dashboard')


@superuser_required
@log_superadmin_action('CHANGE_PLAN', 'Changed gym subscription plan')
def gym_change_plan(request, gym_id):
    """
    Change a gym's subscription plan.
    """
    gym = get_object_or_404(Gym, id=gym_id)
    
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        billing_mode = request.POST.get('billing_mode', 'AUTO')
        
        if not plan_id:
            messages.error(request, "Debes seleccionar un plan")
            return redirect('superadmin:gym_change_plan', gym_id=gym.id)
        
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)
        
        # Get or create subscription
        subscription, created = GymSubscription.objects.get_or_create(
            gym=gym,
            defaults={
                'plan': plan,
                'status': 'ACTIVE',
                'billing_mode': billing_mode,
                'current_period_start': date.today(),
                'current_period_end': date.today() + timedelta(days=30)
            }
        )
        
        if not created:
            subscription.plan = plan
            subscription.billing_mode = billing_mode
            subscription.save()
        
        billing_label = "manual (sin tarjeta)" if billing_mode == 'MANUAL' else "automático"
        messages.success(request, f"Plan actualizado a {plan.name} con cobro {billing_label}")
        return redirect('superadmin:gym_detail', gym_id=gym.id)
    
    plans = SubscriptionPlan.objects.filter(is_active=True)
    
    # Get current subscription if exists
    try:
        current_subscription = gym.subscription
    except GymSubscription.DoesNotExist:
        current_subscription = None
    
    context = {
        'gym': gym, 
        'plans': plans,
        'current_subscription': current_subscription,
        'billing_mode_choices': GymSubscription.BILLING_MODE_CHOICES
    }
    return render(request, 'superadmin/gyms/change_plan.html', context)


@superuser_required
@log_superadmin_action('CHANGE_BILLING_MODE', 'Changed gym billing mode')
def gym_change_billing_mode(request, gym_id):
    """
    Change a gym's billing mode (AUTO/MANUAL).
    """
    gym = get_object_or_404(Gym, id=gym_id)
    
    if request.method == 'POST':
        billing_mode = request.POST.get('billing_mode', 'AUTO')
        
        try:
            subscription = gym.subscription
            subscription.billing_mode = billing_mode
            subscription.save()
            
            billing_label = "manual (sin tarjeta)" if billing_mode == 'MANUAL' else "automático (tarjeta)"
            messages.success(request, f"Modo de facturación cambiado a {billing_label}")
        except GymSubscription.DoesNotExist:
            messages.error(request, "Este gimnasio no tiene suscripción activa")
        
    return redirect('superadmin:gym_detail', gym_id=gym.id)


@superuser_required
def franchise_create(request):
    """
    Create a new franchise.
    """
    if request.method == 'POST':
        form = FranchiseForm(request.POST)
        if form.is_valid():
            franchise = form.save()
            messages.success(request, f"Franquicia '{franchise.name}' creada exitosamente")
            return redirect('superadmin:franchise_list')
    else:
        form = FranchiseForm()
    
    return render(request, 'superadmin/franchises/form.html', {'form': form})


@superuser_required
def franchise_edit(request, franchise_id):
    """
    Edit an existing franchise.
    """
    franchise = get_object_or_404(Franchise, id=franchise_id)
    
    if request.method == 'POST':
        form = FranchiseForm(request.POST, instance=franchise)
        if form.is_valid():
            franchise = form.save()
            messages.success(request, f"Franquicia '{franchise.name}' actualizada exitosamente")
            return redirect('superadmin:franchise_list')
    else:
        form = FranchiseForm(instance=franchise)
    
    context = {'form': form, 'franchise': franchise, 'editing': True}
    return render(request, 'superadmin/franchises/form.html', context)


@superuser_required
def franchise_list(request):
    """
    List all franchises.
    """
    franchises = Franchise.objects.annotate(
        gym_count=Count('gyms')
    ).all()
    
    context = {'franchises': franchises}
    return render(request, 'superadmin/franchises/list.html', context)


@superuser_required
def plan_list(request):
    """
    List all subscription plans.
    """
    plans = SubscriptionPlan.objects.annotate(
        gym_count=Count('gym_subscriptions')
    ).all()
    
    context = {'plans': plans}
    return render(request, 'superadmin/plans/list.html', context)


@superuser_required
def plan_create(request):
    """
    Create a new subscription plan.
    """
    if request.method == 'POST':
        # Extract form data
        plan = SubscriptionPlan.objects.create(
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            price_monthly=Decimal(request.POST.get('price_monthly', '0')),
            price_yearly=Decimal(request.POST.get('price_yearly', '0')) if request.POST.get('price_yearly') else None,
            
            # Modules
            module_pos=request.POST.get('module_pos') == 'on',
            module_calendar=request.POST.get('module_calendar') == 'on',
            module_marketing=request.POST.get('module_marketing') == 'on',
            module_reporting=request.POST.get('module_reporting') == 'on',
            module_client_portal=request.POST.get('module_client_portal') == 'on',
            module_public_portal=request.POST.get('module_public_portal') == 'on',
            module_automations=request.POST.get('module_automations') == 'on',
            module_routines=request.POST.get('module_routines') == 'on',
            module_gamification=request.POST.get('module_gamification') == 'on',
            module_verifactu=request.POST.get('module_verifactu') == 'on',
            
            # Limits
            max_members=int(request.POST.get('max_members')) if request.POST.get('max_members') else None,
            max_staff=int(request.POST.get('max_staff')) if request.POST.get('max_staff') else None,
            max_locations=int(request.POST.get('max_locations')) if request.POST.get('max_locations') else None,
            
            # Transaction Fees
            transaction_fee_type=request.POST.get('transaction_fee_type', 'NONE'),
            transaction_fee_percent=Decimal(request.POST.get('transaction_fee_percent', '0') or '0'),
            transaction_fee_fixed=Decimal(request.POST.get('transaction_fee_fixed', '0') or '0'),
            transaction_fee_apply_to_online=request.POST.get('transaction_fee_apply_to_online') == 'on',
            transaction_fee_apply_to_pos=request.POST.get('transaction_fee_apply_to_pos') == 'on',
            transaction_fee_apply_to_recurring=request.POST.get('transaction_fee_apply_to_recurring') == 'on',
            transaction_fee_exclude_cash=request.POST.get('transaction_fee_exclude_cash') == 'on',
            
            # Flags
            is_demo=request.POST.get('is_demo') == 'on',
            is_active=True,
            display_order=int(request.POST.get('display_order', 0))
        )
        
        messages.success(request, f"Plan '{plan.name}' creado exitosamente")
        return redirect('superadmin:plan_list')
    
    return render(request, 'superadmin/plans/form.html', {'is_create': True})


@superuser_required
def plan_edit(request, plan_id):
    """
    Edit an existing subscription plan.
    """
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    
    if request.method == 'POST':
        plan.name = request.POST.get('name')
        plan.description = request.POST.get('description', '')
        plan.price_monthly = Decimal(request.POST.get('price_monthly', '0'))
        plan.price_yearly = Decimal(request.POST.get('price_yearly', '0')) if request.POST.get('price_yearly') else None
        
        # Modules
        plan.module_pos = request.POST.get('module_pos') == 'on'
        plan.module_calendar = request.POST.get('module_calendar') == 'on'
        plan.module_marketing = request.POST.get('module_marketing') == 'on'
        plan.module_reporting = request.POST.get('module_reporting') == 'on'
        plan.module_client_portal = request.POST.get('module_client_portal') == 'on'
        plan.module_public_portal = request.POST.get('module_public_portal') == 'on'
        plan.module_automations = request.POST.get('module_automations') == 'on'
        plan.module_routines = request.POST.get('module_routines') == 'on'
        plan.module_gamification = request.POST.get('module_gamification') == 'on'
        plan.module_verifactu = request.POST.get('module_verifactu') == 'on'
        
        # Limits
        plan.max_members = int(request.POST.get('max_members')) if request.POST.get('max_members') else None
        plan.max_staff = int(request.POST.get('max_staff')) if request.POST.get('max_staff') else None
        plan.max_locations = int(request.POST.get('max_locations')) if request.POST.get('max_locations') else None
        
        # Transaction Fees
        plan.transaction_fee_type = request.POST.get('transaction_fee_type', 'NONE')
        plan.transaction_fee_percent = Decimal(request.POST.get('transaction_fee_percent', '0') or '0')
        plan.transaction_fee_fixed = Decimal(request.POST.get('transaction_fee_fixed', '0') or '0')
        plan.transaction_fee_apply_to_online = request.POST.get('transaction_fee_apply_to_online') == 'on'
        plan.transaction_fee_apply_to_pos = request.POST.get('transaction_fee_apply_to_pos') == 'on'
        plan.transaction_fee_apply_to_recurring = request.POST.get('transaction_fee_apply_to_recurring') == 'on'
        plan.transaction_fee_exclude_cash = request.POST.get('transaction_fee_exclude_cash') == 'on'
        
        # Flags
        plan.is_demo = request.POST.get('is_demo') == 'on'
        plan.is_active = request.POST.get('is_active') == 'on'
        plan.display_order = int(request.POST.get('display_order', 0))
        
        plan.save()
        
        messages.success(request, f"Plan '{plan.name}' actualizado")
        return redirect('superadmin:plan_list')
    
    context = {'plan': plan, 'is_create': False}
    return render(request, 'superadmin/plans/form.html', context)


@superuser_required
def billing_config(request):
    """
    View/edit billing configuration (Stripe keys, company info).
    """
    config = BillingConfig.get_config()
    
    if request.method == 'POST':
        # Company country and related fields
        config.company_country = request.POST.get('company_country', 'ES')
        config.company_state = request.POST.get('company_state', '')
        
        config.company_name = request.POST.get('company_name')
        config.company_tax_id = request.POST.get('company_tax_id')
        config.company_address = request.POST.get('company_address')
        config.company_email = request.POST.get('company_email')
        config.company_phone = request.POST.get('company_phone', '')
        
        # Update tax_id_label based on country
        country = config.company_country
        if country == 'US':
            config.company_tax_id_label = 'EIN'
        elif country == 'ES':
            config.company_tax_id_label = 'CIF/NIF'
        else:
            config.company_tax_id_label = 'Tax ID'
        
        # System branding (white label)
        config.system_name = request.POST.get('system_name', 'New CRM')
        if 'system_logo' in request.FILES:
            config.system_logo = request.FILES['system_logo']
        
        # Stripe keys (only update if provided)
        if request.POST.get('stripe_publishable_key'):
            config.stripe_publishable_key = request.POST.get('stripe_publishable_key')
        if request.POST.get('stripe_secret_key'):
            config.stripe_secret_key = request.POST.get('stripe_secret_key')
        if request.POST.get('stripe_webhook_secret'):
            config.stripe_webhook_secret = request.POST.get('stripe_webhook_secret')
        
        config.grace_period_days = int(request.POST.get('grace_period_days', 15))
        config.enable_auto_suspension = request.POST.get('enable_auto_suspension') == 'on'
        
        config.save()
        
        # Log this action
        from saas_billing.models import AuditLog
        from .decorators import get_client_ip
        AuditLog.objects.create(
            superadmin=request.user,
            action='UPDATE_BILLING_CONFIG',
            description='Updated billing configuration',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        messages.success(request, "Configuración actualizada")
        return redirect('superadmin:billing_config')
    
    context = {'config': config}
    return render(request, 'superadmin/billing_config.html', context)


@superuser_required
def verifactu_developer_config(request):
    """
    Configuración del desarrollador del software para Verifactu.
    Estos datos se aplican a TODOS los gimnasios que usen Verifactu.
    """
    from saas_billing.models import VerifactuDeveloperConfig
    
    config = VerifactuDeveloperConfig.get_config()
    
    if request.method == 'POST':
        config.software_name = request.POST.get('software_name', 'GymCRM')
        config.software_version = request.POST.get('software_version', '1.0.0')
        config.developer_country = request.POST.get('developer_country', 'ES')
        config.developer_tax_id = request.POST.get('developer_tax_id', '')
        config.developer_name = request.POST.get('developer_name', '')
        config.save()
        
        # Log this action
        from saas_billing.models import AuditLog
        from .decorators import get_client_ip
        AuditLog.objects.create(
            superadmin=request.user,
            action='UPDATE_BILLING_CONFIG',
            description='Updated Verifactu developer configuration',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        messages.success(request, "Configuración de Verifactu actualizada correctamente")
        return redirect('superadmin:verifactu_developer_config')
    
    context = {
        'config': config,
        'country_choices': VerifactuDeveloperConfig.DEVELOPER_COUNTRY_CHOICES,
    }
    return render(request, 'superadmin/verifactu_config.html', context)


@superuser_required
def audit_logs(request):
    """
    View audit logs of all superadmin actions.
    """
    logs = AuditLog.objects.select_related(
        'superadmin', 'target_gym', 'target_franchise'
    ).order_by('-created_at')
    
    # Filter by action type
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    # Filter by superadmin
    admin_filter = request.GET.get('admin', '')
    if admin_filter:
        logs = logs.filter(superadmin_id=admin_filter)
    
    # Pagination (show 50 per page)
    logs = logs[:50]
    
    # Get distinct action types and superadmins for filters
    from accounts.models import User
    action_types = AuditLog.ACTION_CHOICES
    superadmins = User.objects.filter(is_superuser=True)
    
    context = {
        'logs': logs,
        'action_types': action_types,
        'superadmins': superadmins,
        'action_filter': action_filter,
        'admin_filter': admin_filter,
    }
    
    return render(request, 'superadmin/audit_logs.html', context)


@superuser_required
def system_status(request):
    """
    Shows migration status and system health.
    """
    status = MigrationService.get_system_status()
    orphan_gyms = MigrationService.get_orphan_gyms()
    
    context = {
        'status': status,
        'orphan_gyms': orphan_gyms,
        'debug': True # or settings.DEBUG
    }
    return render(request, 'superadmin/system/status.html', context)

@superuser_required
@log_superadmin_action('INIT_SYSTEM', 'Inicializó planes por defecto')
def system_initialize_plans(request):
    if request.method == 'POST':
        try:
            created_plans = MigrationService.initialize_default_plans()
            if created_plans:
                messages.success(request, f"Planes creados: {', '.join(created_plans)}")
            else:
                messages.info(request, "Los planes por defecto ya existen.")
        except Exception as e:
            messages.error(request, f"Error al inicializar: {str(e)}")
    return redirect('superadmin:system_status')

@superuser_required
@log_superadmin_action('MIGRATE_ORPHANS', 'Migración masiva de gimnasios huérfanos')
def system_migrate_orphans(request):
    if request.method == 'POST':
        try:
            count = MigrationService.migrate_orphan_gyms()
            messages.success(request, f"Se han migrado exitosamente {count} gimnasios al plan Trial.")
        except Exception as e:
            messages.error(request, f"Error en migración: {str(e)}")
    return redirect('superadmin:system_status')


@superuser_required
def health_dashboard(request):
    """
    System health dashboard showing webhook status, payment health, and subscription metrics.
    """
    health_data = health_monitor.get_health_dashboard()
    invoice_analytics = health_monitor.get_invoice_analytics(days=30)
    
    # Parse webhook last_received for template
    webhook_data = health_data.get('webhook', {})
    if webhook_data.get('last_received'):
        try:
            webhook_data['last_received'] = datetime.fromisoformat(
                webhook_data['last_received'].replace('Z', '+00:00')
            ) if isinstance(webhook_data['last_received'], str) else webhook_data['last_received']
        except (ValueError, AttributeError):
            pass
    
    context = {
        'health': health_data,
        'webhook': webhook_data,
        'payments': health_data.get('payments', {}),
        'subscriptions': health_data.get('subscriptions', {}),
        'overall_status': health_data.get('overall_status', 'unknown'),
        'invoice_analytics': invoice_analytics,
    }
    
    return render(request, 'superadmin/health_dashboard.html', context)


@superuser_required
def health_api(request):
    """
    API endpoint for health dashboard (AJAX refresh).
    """
    from django.http import JsonResponse
    health_data = health_monitor.get_health_dashboard()
    return JsonResponse(health_data)
