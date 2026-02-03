"""
Vistas de Backoffice para el sistema de Monedero Virtual.
"""
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.utils import timezone

from accounts.decorators import require_gym_permission
from clients.models import Client
from organizations.models import Gym
from .models import ClientWallet, WalletTransaction, WalletSettings, PaymentMethod
from .wallet_service import WalletService


def get_franchise_gyms(gym):
    """Obtiene todos los gyms de la franquicia si existe."""
    if gym.franchise:
        return list(gym.franchise.gyms.filter(is_active=True))
    return [gym]


def get_gym_filter(request, gym):
    """Obtiene el filtro de gym basado en el parámetro selected_gyms."""
    selected_gym_ids = request.GET.getlist('gym')
    franchise_gyms = get_franchise_gyms(gym)
    
    if selected_gym_ids and 'all' not in selected_gym_ids:
        # Filtrar solo los gyms válidos de la franquicia
        valid_ids = [g.id for g in franchise_gyms]
        selected_ids = [int(gid) for gid in selected_gym_ids if gid.isdigit() and int(gid) in valid_ids]
        if selected_ids:
            return selected_ids
    
    # Si es "all" o no hay selección, retornar solo el gym actual
    if 'all' in selected_gym_ids:
        return [g.id for g in franchise_gyms]
    
    return [gym.id]


# ============================================
# CONFIGURACIÓN DEL MONEDERO
# ============================================

@login_required
@require_gym_permission('finance.settings')
def wallet_settings(request):
    """Configuración del sistema de monedero del gym."""
    gym = request.gym
    settings = WalletService.get_wallet_settings(gym)
    franchise_gyms = get_franchise_gyms(gym)
    
    if request.method == 'POST':
        # Activación
        settings.wallet_enabled = request.POST.get('wallet_enabled') == 'on'
        settings.auto_create_wallet = request.POST.get('auto_create_wallet') == 'on'
        
        # Saldo negativo
        settings.allow_negative_default = request.POST.get('allow_negative_default') == 'on'
        settings.default_negative_limit = Decimal(request.POST.get('default_negative_limit', '0') or '0')
        
        # Bonificación
        settings.topup_bonus_enabled = request.POST.get('topup_bonus_enabled') == 'on'
        settings.topup_bonus_type = request.POST.get('topup_bonus_type', 'PERCENT')
        settings.topup_bonus_percent = Decimal(request.POST.get('topup_bonus_percent', '10') or '10')
        settings.topup_bonus_min_amount = Decimal(request.POST.get('topup_bonus_min_amount', '0') or '0')
        settings.topup_bonus_max_amount = Decimal(request.POST.get('topup_bonus_max_amount', '0') or '0')
        
        # Uso del saldo
        settings.use_wallet_first = request.POST.get('use_wallet_first') == 'on'
        settings.allow_partial_wallet_payment = request.POST.get('allow_partial_wallet_payment') == 'on'
        settings.refunds_to_wallet = request.POST.get('refunds_to_wallet') == 'on'
        
        # Recarga online
        settings.allow_online_topup = request.POST.get('allow_online_topup') == 'on'
        settings.min_topup_amount = Decimal(request.POST.get('min_topup_amount', '10') or '10')
        settings.max_topup_amount = Decimal(request.POST.get('max_topup_amount', '500') or '500')
        
        # Visibilidad
        settings.show_in_client_portal = request.POST.get('show_in_client_portal') == 'on'
        settings.show_in_app = request.POST.get('show_in_app') == 'on'
        
        # Caducidad
        settings.balance_expires = request.POST.get('balance_expires') == 'on'
        settings.balance_expiry_months = int(request.POST.get('balance_expiry_months', '12') or '12')
        
        # Montos predefinidos
        preset_amounts_str = request.POST.get('topup_preset_amounts', '20,50,100,200')
        try:
            preset_amounts = [int(x.strip()) for x in preset_amounts_str.split(',') if x.strip().isdigit()]
            settings.topup_preset_amounts = preset_amounts or [20, 50, 100, 200]
        except:
            settings.topup_preset_amounts = [20, 50, 100, 200]
        
        settings.save()
        
        # Crear método de pago si se activa
        if settings.wallet_enabled:
            WalletService.get_or_create_wallet_payment_method(gym)
        
        messages.success(request, 'Configuración de monedero guardada correctamente')
        return redirect('wallet_settings')
    
    # Estadísticas
    total_wallets = ClientWallet.objects.filter(gym=gym).count()
    total_balance = ClientWallet.objects.filter(gym=gym).aggregate(
        total=Sum('balance')
    )['total'] or Decimal('0.00')
    negative_wallets = ClientWallet.objects.filter(gym=gym, balance__lt=0).count()
    
    context = {
        'title': 'Configuración de Monedero',
        'settings': settings,
        'stats': {
            'total_wallets': total_wallets,
            'total_balance': total_balance,
            'negative_wallets': negative_wallets,
        }
    }
    return render(request, 'backoffice/finance/wallet_settings.html', context)


# ============================================
# LISTADO DE MONEDEROS
# ============================================

@login_required
@require_gym_permission('clients.view')
def wallet_list(request):
    """Lista todos los monederos de clientes."""
    gym = request.gym
    franchise_gyms = get_franchise_gyms(gym)
    selected_gym_ids = get_gym_filter(request, gym)
    
    wallets = ClientWallet.objects.filter(gym_id__in=selected_gym_ids).select_related('client__user', 'gym')
    
    # Filtros
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    balance_filter = request.GET.get('balance', 'all')
    
    if search:
        wallets = wallets.filter(
            Q(client__first_name__icontains=search) |
            Q(client__last_name__icontains=search) |
            Q(client__email__icontains=search)
        )
    
    if status_filter == 'active':
        wallets = wallets.filter(is_active=True)
    elif status_filter == 'inactive':
        wallets = wallets.filter(is_active=False)
    
    if balance_filter == 'positive':
        wallets = wallets.filter(balance__gt=0)
    elif balance_filter == 'negative':
        wallets = wallets.filter(balance__lt=0)
    elif balance_filter == 'zero':
        wallets = wallets.filter(balance=0)
    
    wallets = wallets.order_by('-balance')
    
    # Paginación
    paginator = Paginator(wallets, 25)
    page = request.GET.get('page', 1)
    wallets = paginator.get_page(page)
    
    # Estadísticas (según gyms seleccionados)
    all_wallets = ClientWallet.objects.filter(gym_id__in=selected_gym_ids)
    stats = {
        'total': all_wallets.count(),
        'with_balance': all_wallets.filter(balance__gt=0).count(),
        'negative': all_wallets.filter(balance__lt=0).count(),
        'total_balance': all_wallets.aggregate(total=Sum('balance'))['total'] or Decimal('0.00'),
    }
    
    # Gyms seleccionados para el template
    selected_gyms = request.GET.getlist('gym') or []
    
    context = {
        'title': 'Monederos de Clientes',
        'wallets': wallets,
        'stats': stats,
        'search': search,
        'status_filter': status_filter,
        'balance_filter': balance_filter,
        # Franquicia
        'franchise_gyms': franchise_gyms if len(franchise_gyms) > 1 else None,
        'selected_gyms': selected_gyms,
        'has_franchise': len(franchise_gyms) > 1,
    }
    return render(request, 'backoffice/finance/wallet_list.html', context)


# ============================================
# DETALLE Y GESTIÓN DE MONEDERO INDIVIDUAL
# ============================================

@login_required
@require_gym_permission('clients.view')
def wallet_detail(request, client_id):
    """Detalle del monedero de un cliente."""
    gym = request.gym
    client = get_object_or_404(Client, pk=client_id, gym=gym)
    
    wallet, created = WalletService.get_or_create_wallet(client, gym)
    
    # Obtener historial
    transactions = wallet.transactions.select_related(
        'order', 'payment', 'created_by', 'topup_method'
    )[:50]
    
    # Resumen
    summary = WalletService.get_summary(wallet)
    
    # Métodos de pago para recarga
    payment_methods = PaymentMethod.objects.filter(
        gym=gym, 
        is_active=True
    ).exclude(provider_code='WALLET')
    
    context = {
        'title': f'Monedero de {client.get_full_name()}',
        'client': client,
        'wallet': wallet,
        'transactions': transactions,
        'summary': summary,
        'payment_methods': payment_methods,
    }
    return render(request, 'backoffice/finance/wallet_detail.html', context)


@login_required
@require_gym_permission('finance.manage')
@require_POST
def wallet_topup(request, client_id):
    """Recargar monedero desde el backoffice."""
    gym = request.gym
    client = get_object_or_404(Client, pk=client_id, gym=gym)
    
    wallet, _ = WalletService.get_or_create_wallet(client, gym)
    
    try:
        amount = Decimal(request.POST.get('amount', '0'))
        payment_method_id = request.POST.get('payment_method')
        notes = request.POST.get('notes', '')
        
        payment_method = None
        if payment_method_id:
            payment_method = PaymentMethod.objects.get(pk=payment_method_id, gym=gym)
        
        topup_tx, bonus_tx = WalletService.topup(
            wallet=wallet,
            amount=amount,
            payment_method=payment_method,
            created_by=request.user,
            notes=notes,
        )
        
        msg = f'Recarga de {amount}€ realizada correctamente'
        if bonus_tx:
            msg += f' (+{bonus_tx.amount}€ de bonificación)'
        
        messages.success(request, msg)
        
    except Exception as e:
        messages.error(request, f'Error al recargar: {str(e)}')
    
    return redirect('wallet_detail', client_id=client_id)


@login_required
@require_gym_permission('finance.manage')
@require_POST
def wallet_adjust(request, client_id):
    """Ajuste manual del saldo."""
    gym = request.gym
    client = get_object_or_404(Client, pk=client_id, gym=gym)
    
    wallet, _ = WalletService.get_or_create_wallet(client, gym)
    
    try:
        amount = Decimal(request.POST.get('amount', '0'))
        reason = request.POST.get('reason', '')
        notes = request.POST.get('notes', '')
        
        WalletService.adjust(
            wallet=wallet,
            amount=amount,
            reason=reason,
            created_by=request.user,
            notes=notes,
        )
        
        action = "añadido" if amount > 0 else "descontado"
        messages.success(request, f'Se ha {action} {abs(amount)}€ del saldo')
        
    except Exception as e:
        messages.error(request, f'Error en ajuste: {str(e)}')
    
    return redirect('wallet_detail', client_id=client_id)


@login_required
@require_gym_permission('finance.manage')
@require_POST
def wallet_toggle(request, client_id):
    """Activar/desactivar monedero del cliente."""
    gym = request.gym
    client = get_object_or_404(Client, pk=client_id, gym=gym)
    
    wallet, _ = WalletService.get_or_create_wallet(client, gym)
    wallet.is_active = not wallet.is_active
    wallet.save()
    
    status = "activado" if wallet.is_active else "desactivado"
    messages.success(request, f'Monedero {status}')
    
    return redirect('wallet_detail', client_id=client_id)


@login_required
@require_gym_permission('finance.manage')
@require_POST
def wallet_update_limits(request, client_id):
    """Actualizar límites del monedero (fiado, auto-recarga)."""
    gym = request.gym
    client = get_object_or_404(Client, pk=client_id, gym=gym)
    
    wallet, _ = WalletService.get_or_create_wallet(client, gym)
    
    wallet.allow_negative = request.POST.get('allow_negative') == 'on'
    wallet.negative_limit = Decimal(request.POST.get('negative_limit', '0') or '0')
    wallet.auto_topup_enabled = request.POST.get('auto_topup_enabled') == 'on'
    wallet.auto_topup_threshold = Decimal(request.POST.get('auto_topup_threshold', '10') or '10')
    wallet.auto_topup_amount = Decimal(request.POST.get('auto_topup_amount', '50') or '50')
    wallet.save()
    
    messages.success(request, 'Configuración del monedero actualizada')
    
    return redirect('wallet_detail', client_id=client_id)


# ============================================
# AJAX ENDPOINTS
# ============================================

@login_required
@require_GET
def wallet_balance_api(request, client_id):
    """API para obtener saldo del cliente (usado en POS)."""
    gym = request.gym
    
    try:
        client = Client.objects.get(pk=client_id, gym=gym)
        
        # Verificar si el monedero está habilitado
        if not WalletService.is_wallet_enabled(gym):
            return JsonResponse({
                'enabled': False,
                'balance': 0,
                'available': 0,
            })
        
        wallet = get_client_wallet(client, gym, create=False)
        
        if not wallet or not wallet.is_active:
            return JsonResponse({
                'enabled': True,
                'balance': 0,
                'available': 0,
                'has_wallet': False,
            })
        
        return JsonResponse({
            'enabled': True,
            'has_wallet': True,
            'balance': float(wallet.balance),
            'available': float(wallet.available_balance),
            'is_negative': wallet.is_negative,
            'allow_negative': wallet.allow_negative,
            'negative_limit': float(wallet.negative_limit),
        })
        
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)


@login_required
@require_POST
def wallet_quick_pay_api(request):
    """API para pago rápido con monedero (usado en POS)."""
    gym = request.gym
    
    try:
        client_id = request.POST.get('client_id')
        amount = Decimal(request.POST.get('amount', '0'))
        order_id = request.POST.get('order_id')
        
        client = Client.objects.get(pk=client_id, gym=gym)
        wallet, _ = WalletService.get_or_create_wallet(client, gym)
        
        # Verificar saldo
        if not wallet.can_pay(amount):
            return JsonResponse({
                'success': False,
                'error': f'Saldo insuficiente. Disponible: {wallet.available_balance}€'
            })
        
        # Procesar pago
        from .models import Order
        order = None
        if order_id:
            order = Order.objects.get(pk=order_id, gym=gym)
        
        tx = WalletService.pay(
            wallet=wallet,
            amount=amount,
            order=order,
            created_by=request.user,
        )
        
        return JsonResponse({
            'success': True,
            'transaction_id': tx.pk,
            'new_balance': float(wallet.balance),
            'amount_paid': float(amount),
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================
# REPORTES
# ============================================

@login_required
@require_gym_permission('finance.reports')
def wallet_report(request):
    """Reporte de monederos."""
    gym = request.gym
    franchise_gyms = get_franchise_gyms(gym)
    selected_gym_ids = get_gym_filter(request, gym)
    
    # Filtros de fecha
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    transactions = WalletTransaction.objects.filter(
        wallet__gym_id__in=selected_gym_ids
    ).select_related('wallet__client', 'wallet__gym', 'created_by')
    
    if from_date:
        transactions = transactions.filter(created_at__date__gte=from_date)
    if to_date:
        transactions = transactions.filter(created_at__date__lte=to_date)
    
    # Totales por tipo
    totals_by_type = transactions.values('transaction_type').annotate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    # Resumen general (según gyms seleccionados)
    all_wallets = ClientWallet.objects.filter(gym_id__in=selected_gym_ids)
    summary = {
        'total_wallets': all_wallets.count(),
        'total_balance': all_wallets.aggregate(total=Sum('balance'))['total'] or Decimal('0.00'),
        'total_topups': all_wallets.aggregate(total=Sum('total_topups'))['total'] or Decimal('0.00'),
        'total_spent': all_wallets.aggregate(total=Sum('total_spent'))['total'] or Decimal('0.00'),
        'negative_count': all_wallets.filter(balance__lt=0).count(),
        'negative_total': abs(all_wallets.filter(balance__lt=0).aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0.00')),
    }
    
    # Gyms seleccionados para el template
    selected_gyms = request.GET.getlist('gym') or []
    
    context = {
        'title': 'Reporte de Monederos',
        'totals_by_type': totals_by_type,
        'summary': summary,
        'transactions': transactions[:100],
        'from_date': from_date,
        'to_date': to_date,
        # Franquicia
        'franchise_gyms': franchise_gyms if len(franchise_gyms) > 1 else None,
        'selected_gyms': selected_gyms,
        'has_franchise': len(franchise_gyms) > 1,
    }
    return render(request, 'backoffice/finance/wallet_report.html', context)


# Helper function (importar si no está disponible)
def get_client_wallet(client, gym, create=True):
    """Atajo para obtener el monedero de un cliente."""
    if create:
        wallet, _ = WalletService.get_or_create_wallet(client, gym)
        return wallet
    else:
        try:
            return ClientWallet.objects.get(client=client, gym=gym)
        except ClientWallet.DoesNotExist:
            return None
