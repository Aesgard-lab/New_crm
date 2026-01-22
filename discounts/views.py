from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Sum, Q
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from accounts.decorators import require_gym_permission
from .models import Discount, DiscountUsage, ReferralProgram, Referral
from .forms import DiscountForm, ReferralProgramForm


# ============================================
# DISCOUNT CRUD
# ============================================

@login_required
@require_gym_permission('discounts.view')
def discount_list(request):
    """Lista de todos los descuentos del gimnasio"""
    gym = request.gym
    
    # Filtros
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')
    search = request.GET.get('search', '').strip()
    
    discounts = Discount.objects.filter(gym=gym).select_related('created_by')
    
    # Aplicar filtros
    if status_filter == 'active':
        discounts = discounts.filter(is_active=True)
    elif status_filter == 'inactive':
        discounts = discounts.filter(is_active=False)
    elif status_filter == 'expired':
        discounts = discounts.filter(valid_until__lt=timezone.now())
    
    if type_filter != 'all':
        discounts = discounts.filter(discount_type=type_filter)
    
    if search:
        discounts = discounts.filter(
            Q(name__icontains=search) | 
            Q(code__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Estadísticas
    stats = {
        'total': Discount.objects.filter(gym=gym).count(),
        'active': Discount.objects.filter(gym=gym, is_active=True).count(),
        'with_code': Discount.objects.filter(gym=gym, code__isnull=False).exclude(code='').count(),
        'expired': Discount.objects.filter(gym=gym, valid_until__lt=timezone.now()).count(),
    }
    
    context = {
        'title': 'Descuentos y Promociones',
        'discounts': discounts,
        'stats': stats,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'search': search,
    }
    return render(request, 'discounts/list.html', context)


@login_required
@require_gym_permission('discounts.create')
def discount_create(request):
    """Crear nuevo descuento"""
    gym = request.gym
    
    if request.method == 'POST':
        form = DiscountForm(request.POST, gym=gym)
        if form.is_valid():
            discount = form.save(commit=False)
            discount.gym = gym
            discount.created_by = request.user
            discount.save()
            form.save_m2m()  # Para ManyToMany fields
            return redirect('discount_detail', pk=discount.id)
    else:
        form = DiscountForm(gym=gym)
    
    context = {
        'title': 'Nuevo Descuento',
        'form': form,
        'is_edit': False,
    }
    return render(request, 'discounts/form.html', context)


@login_required
@require_gym_permission('discounts.view')
def discount_detail(request, pk):
    """Detalle de un descuento con analytics"""
    gym = request.gym
    discount = get_object_or_404(Discount, pk=pk, gym=gym)
    
    # Estadísticas de uso
    total_uses = discount.usages.count()
    total_discount_amount = discount.usages.aggregate(
        total=Sum('discount_amount')
    )['total'] or Decimal('0.00')
    
    total_revenue = discount.usages.aggregate(
        total=Sum('final_amount')
    )['total'] or Decimal('0.00')
    
    # Usos recientes
    recent_uses = discount.usages.select_related('client', 'applied_by').order_by('-created_at')[:10]
    
    # Clientes únicos que lo han usado
    unique_clients = discount.usages.values('client').distinct().count()
    
    # Gráfico de usos por día (últimos 30 días)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_uses = discount.usages.filter(
        created_at__gte=thirty_days_ago
    ).extra(
        select={'day': 'DATE(created_at)'}
    ).values('day').annotate(count=Count('id')).order_by('day')
    
    context = {
        'title': f'Descuento: {discount.name}',
        'discount': discount,
        'total_uses': total_uses,
        'total_discount_amount': total_discount_amount,
        'total_revenue': total_revenue,
        'recent_uses': recent_uses,
        'unique_clients': unique_clients,
        'daily_uses': list(daily_uses),
    }
    return render(request, 'discounts/detail.html', context)


@login_required
@require_gym_permission('discounts.edit')
def discount_edit(request, pk):
    """Editar descuento existente"""
    gym = request.gym
    discount = get_object_or_404(Discount, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = DiscountForm(request.POST, instance=discount, gym=gym)
        if form.is_valid():
            form.save()
            return redirect('discount_detail', pk=discount.id)
    else:
        form = DiscountForm(instance=discount, gym=gym)
    
    context = {
        'title': f'Editar: {discount.name}',
        'form': form,
        'discount': discount,
        'is_edit': True,
    }
    return render(request, 'discounts/form.html', context)


@login_required
@require_gym_permission('discounts.delete')
@require_POST
def discount_delete(request, pk):
    """Eliminar descuento"""
    gym = request.gym
    discount = get_object_or_404(Discount, pk=pk, gym=gym)
    discount.delete()
    return redirect('discount_list')


@login_required
@require_gym_permission('discounts.edit')
@require_POST
def discount_toggle_active(request, pk):
    """Activar/desactivar descuento"""
    gym = request.gym
    discount = get_object_or_404(Discount, pk=pk, gym=gym)
    discount.is_active = not discount.is_active
    discount.save()
    return redirect('discount_detail', pk=pk)


# ============================================
# DISCOUNT VALIDATION & APPLICATION (AJAX)
# ============================================

@login_required
@require_gym_permission('discounts.apply')
def validate_discount_code(request):
    """Validar código de descuento (AJAX para TPV)"""
    gym = request.gym
    code = request.GET.get('code', '').strip()
    client_id = request.GET.get('client_id')
    subtotal = request.GET.get('subtotal', 0)
    
    try:
        subtotal = Decimal(subtotal)
    except:
        return JsonResponse({'error': 'Subtotal inválido'}, status=400)
    
    if not code:
        return JsonResponse({'error': 'Código vacío'}, status=400)
    
    # Buscar descuento
    try:
        if code.isdigit():
            # Si es un ID numérico, buscar por ID
            discount = Discount.objects.get(id=int(code), gym=gym)
        else:
            # Buscar por código
            discount = Discount.objects.get(
                Q(code__iexact=code) if not discount.code_case_sensitive else Q(code=code),
                gym=gym
            )
    except Discount.DoesNotExist:
        return JsonResponse({'error': 'Código no encontrado'}, status=404)
    
    # Validar si está activo
    if not discount.is_valid_now():
        return JsonResponse({'error': 'Descuento no disponible'}, status=400)
    
    # Validar cliente si se proporcionó
    if client_id:
        from clients.models import Client
        try:
            client = Client.objects.get(id=client_id, gym=gym)
            if not discount.can_be_used_by_client(client):
                return JsonResponse({'error': 'Este descuento no está disponible para este cliente'}, status=400)
        except Client.DoesNotExist:
            pass
    
    # Calcular descuento
    discount_amount = discount.calculate_discount_amount(subtotal)
    final_amount = subtotal - discount_amount
    
    return JsonResponse({
        'success': True,
        'discount': {
            'id': discount.id,
            'name': discount.name,
            'description': discount.description,
            'type': discount.get_discount_type_display(),
            'value': str(discount.value),
            'discount_amount': str(discount_amount),
            'final_amount': str(final_amount),
            'savings_percentage': str((discount_amount / subtotal * 100).quantize(Decimal('0.1'))) if subtotal > 0 else '0',
        }
    })


@login_required
@require_gym_permission('discounts.view')
def available_discounts_for_client(request, client_id):
    """Lista de descuentos disponibles para un cliente específico (AJAX)"""
    gym = request.gym
    
    from clients.models import Client
    client = get_object_or_404(Client, id=client_id, gym=gym)
    
    # Obtener descuentos aplicables
    all_discounts = Discount.objects.filter(gym=gym, is_active=True)
    
    available = []
    for discount in all_discounts:
        if discount.can_be_used_by_client(client):
            available.append({
                'id': discount.id,
                'name': discount.name,
                'description': discount.description,
                'display_value': discount.get_display_value(),
                'code': discount.code or '',
                'valid_until': discount.valid_until.isoformat() if discount.valid_until else None,
            })
    
    return JsonResponse({'discounts': available})


# ============================================
# REFERRAL PROGRAM
# ============================================

@login_required
@require_gym_permission('discounts.view')
def referral_program_list(request):
    """Lista de programas de referidos"""
    gym = request.gym
    programs = ReferralProgram.objects.filter(gym=gym).select_related(
        'referrer_discount', 'referred_discount', 'bonus_discount'
    )
    
    context = {
        'title': 'Programas de Referidos',
        'programs': programs,
    }
    return render(request, 'backoffice/discounts/list.html', context)


@login_required
@require_gym_permission('discounts.create')
def referral_program_create(request):
    """Crear programa de referidos"""
    gym = request.gym
    
    if request.method == 'POST':
        form = ReferralProgramForm(request.POST, gym=gym)
        if form.is_valid():
            program = form.save(commit=False)
            program.gym = gym
            program.save()
            return redirect('referral_program_list')
    else:
        form = ReferralProgramForm(gym=gym)
    
    context = {
        'title': 'Nuevo Programa de Referidos',
        'form': form,
    }
    return render(request, 'backoffice/discounts/referral_form.html', context)


@login_required
@require_gym_permission('discounts.view')
def referral_tracking(request):
    """Tracking de referidos del gimnasio"""
    gym = request.gym
    
    referrals = Referral.objects.filter(
        program__gym=gym
    ).select_related('referrer', 'referred', 'program').order_by('-created_at')
    
    # Estadísticas
    stats = {
        'total': referrals.count(),
        'pending': referrals.filter(status=Referral.Status.PENDING).count(),
        'completed': referrals.filter(status=Referral.Status.COMPLETED).count(),
        'rewarded': referrals.filter(status=Referral.Status.REWARDED).count(),
    }
    
    context = {
        'title': 'Tracking de Referidos',
        'referrals': referrals[:100],  # Limitar a 100
        'stats': stats,
    }
    return render(request, 'backoffice/discounts/list.html', context)


# ============================================
# ANALYTICS DASHBOARD
# ============================================

@login_required
@require_gym_permission('discounts.view')
def discount_analytics(request):
    """Dashboard de analytics de descuentos"""
    gym = request.gym
    
    # Período
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Estadísticas generales
    total_discounts = Discount.objects.filter(gym=gym).count()
    active_discounts = Discount.objects.filter(gym=gym, is_active=True).count()
    
    # Usos en el período
    period_uses = DiscountUsage.objects.filter(
        discount__gym=gym,
        created_at__gte=start_date
    )
    
    total_uses = period_uses.count()
    total_discount_amount = period_uses.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0.00')
    total_revenue = period_uses.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
    
    # Top descuentos más usados
    top_discounts = Discount.objects.filter(gym=gym).annotate(
        usage_count=Count('usages')
    ).order_by('-usage_count')[:10]
    
    # Descuentos por tipo
    by_type = DiscountUsage.objects.filter(
        discount__gym=gym,
        created_at__gte=start_date
    ).values('discount__discount_type').annotate(
        count=Count('id'),
        total_amount=Sum('discount_amount')
    )
    
    # Tendencia diaria
    daily_stats = period_uses.extra(
        select={'day': 'DATE(discounts_discountusage.created_at)'}
    ).values('day').annotate(
        uses=Count('id'),
        amount=Sum('discount_amount')
    ).order_by('day')
    
    context = {
        'title': 'Analytics de Descuentos',
        'days': days,
        'total_discounts': total_discounts,
        'active_discounts': active_discounts,
        'total_uses': total_uses,
        'total_discount_amount': total_discount_amount,
        'total_revenue': total_revenue,
        'top_discounts': top_discounts,
        'by_type': list(by_type),
        'daily_stats': list(daily_stats),
    }
    return render(request, 'discounts/analytics.html', context)
