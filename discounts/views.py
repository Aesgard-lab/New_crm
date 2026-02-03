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
# REFERRAL PROGRAM - CRUD Completo
# ============================================

@login_required
@require_gym_permission('discounts.view')
def referral_program_list(request):
    """Lista de programas de referidos con soporte de franquicia"""
    gym = request.gym
    user = request.user
    
    # Verificar si es owner de franquicia
    is_franchise_owner = hasattr(user, 'franchises_owned') and user.franchises_owned.exists()
    franchise = None
    franchise_gyms = []
    
    if is_franchise_owner:
        franchise = user.franchises_owned.first()
        franchise_gyms = list(franchise.gyms.all())
    
    # Filtro por gimnasio (para owners de franquicia)
    selected_gym_id = request.GET.get('gym', '')
    
    if is_franchise_owner and not selected_gym_id:
        # Mostrar programas de todos los gyms de la franquicia
        programs = ReferralProgram.objects.filter(
            gym__in=franchise_gyms
        ).select_related('gym', 'referrer_discount', 'referred_discount')
    elif selected_gym_id and is_franchise_owner:
        programs = ReferralProgram.objects.filter(
            gym_id=selected_gym_id
        ).select_related('gym', 'referrer_discount', 'referred_discount')
    else:
        programs = ReferralProgram.objects.filter(
            gym=gym
        ).select_related('gym', 'referrer_discount', 'referred_discount')
    
    # Obtener configuración de referidos por gym
    from organizations.models import PublicPortalSettings
    gym_settings = {}
    
    if is_franchise_owner:
        for fg in franchise_gyms:
            try:
                settings = PublicPortalSettings.objects.get(gym=fg)
                gym_settings[fg.id] = {
                    'enabled': settings.referral_program_enabled,
                    'message': settings.referral_share_message,
                }
            except PublicPortalSettings.DoesNotExist:
                gym_settings[fg.id] = {'enabled': False, 'message': ''}
    else:
        try:
            settings = PublicPortalSettings.objects.get(gym=gym)
            gym_settings[gym.id] = {
                'enabled': settings.referral_program_enabled,
                'message': settings.referral_share_message,
            }
        except PublicPortalSettings.DoesNotExist:
            gym_settings[gym.id] = {'enabled': False, 'message': ''}
    
    context = {
        'title': 'Programas de Referidos',
        'programs': programs.order_by('-is_active', '-created_at'),
        'is_franchise_owner': is_franchise_owner,
        'franchise': franchise,
        'franchise_gyms': franchise_gyms,
        'selected_gym_id': selected_gym_id,
        'gym_settings': gym_settings,
        'current_gym': gym,
    }
    return render(request, 'backoffice/discounts/referral_list.html', context)


@login_required
@require_gym_permission('discounts.create')
def referral_program_create(request):
    """Crear programa de referidos con soporte de franquicia"""
    gym = request.gym
    user = request.user
    
    # Verificar franquicia
    is_franchise_owner = hasattr(user, 'franchises_owned') and user.franchises_owned.exists()
    franchise = None
    franchise_gyms = []
    
    if is_franchise_owner:
        franchise = user.franchises_owned.first()
        franchise_gyms = list(franchise.gyms.all())
    
    if request.method == 'POST':
        # Obtener gyms seleccionados
        selected_gym_ids = request.POST.getlist('target_gyms')
        
        form = ReferralProgramForm(
            request.POST, 
            gym=gym if not is_franchise_owner else None,
            gyms=franchise_gyms if is_franchise_owner else None
        )
        
        if form.is_valid():
            if is_franchise_owner and selected_gym_ids:
                # Crear programa para cada gym seleccionado
                from organizations.models import Gym
                for gym_id in selected_gym_ids:
                    target_gym = Gym.objects.get(id=gym_id)
                    program = form.save(commit=False)
                    program.pk = None  # Reset PK para crear nuevo
                    program.gym = target_gym
                    program.save()
                from django.contrib import messages
                messages.success(request, f'Programa creado en {len(selected_gym_ids)} gimnasio(s)')
            else:
                # Crear solo para el gym actual
                program = form.save(commit=False)
                program.gym = gym
                program.save()
                from django.contrib import messages
                messages.success(request, 'Programa de referidos creado exitosamente')
            
            return redirect('referral_program_list')
    else:
        form = ReferralProgramForm(
            gym=gym if not is_franchise_owner else None,
            gyms=franchise_gyms if is_franchise_owner else None
        )
    
    context = {
        'title': 'Nuevo Programa de Referidos',
        'form': form,
        'is_franchise_owner': is_franchise_owner,
        'franchise_gyms': franchise_gyms,
        'current_gym': gym,
    }
    return render(request, 'backoffice/discounts/referral_form.html', context)


@login_required
@require_gym_permission('discounts.view')
def referral_program_detail(request, pk):
    """Detalle de un programa de referidos"""
    gym = request.gym
    user = request.user
    
    # Verificar permisos
    is_franchise_owner = hasattr(user, 'franchises_owned') and user.franchises_owned.exists()
    
    if is_franchise_owner:
        franchise = user.franchises_owned.first()
        program = get_object_or_404(ReferralProgram, pk=pk, gym__in=franchise.gyms.all())
    else:
        program = get_object_or_404(ReferralProgram, pk=pk, gym=gym)
    
    # Estadísticas del programa
    referrals = Referral.objects.filter(program=program)
    stats = {
        'total': referrals.count(),
        'pending': referrals.filter(status=Referral.Status.PENDING).count(),
        'registered': referrals.filter(status=Referral.Status.REGISTERED).count(),
        'completed': referrals.filter(status=Referral.Status.COMPLETED).count(),
        'rewarded': referrals.filter(status=Referral.Status.REWARDED).count(),
        'total_credit_given': referrals.aggregate(
            total=Sum('referrer_credit_given')
        )['total'] or Decimal('0.00'),
    }
    
    # Últimos referidos
    recent_referrals = referrals.select_related('referrer', 'referred').order_by('-created_at')[:20]
    
    context = {
        'title': f'Programa: {program.name}',
        'program': program,
        'stats': stats,
        'referrals': recent_referrals,
    }
    return render(request, 'backoffice/discounts/referral_detail.html', context)


@login_required
@require_gym_permission('discounts.edit')
def referral_program_edit(request, pk):
    """Editar programa de referidos"""
    gym = request.gym
    user = request.user
    
    is_franchise_owner = hasattr(user, 'franchises_owned') and user.franchises_owned.exists()
    
    if is_franchise_owner:
        franchise = user.franchises_owned.first()
        program = get_object_or_404(ReferralProgram, pk=pk, gym__in=franchise.gyms.all())
        franchise_gyms = list(franchise.gyms.all())
    else:
        program = get_object_or_404(ReferralProgram, pk=pk, gym=gym)
        franchise_gyms = []
    
    if request.method == 'POST':
        form = ReferralProgramForm(
            request.POST, 
            instance=program,
            gym=program.gym if not is_franchise_owner else None,
            gyms=franchise_gyms if is_franchise_owner else None
        )
        if form.is_valid():
            form.save()
            from django.contrib import messages
            messages.success(request, 'Programa actualizado exitosamente')
            return redirect('referral_program_list')
    else:
        form = ReferralProgramForm(
            instance=program,
            gym=program.gym if not is_franchise_owner else None,
            gyms=franchise_gyms if is_franchise_owner else None
        )
    
    context = {
        'title': f'Editar: {program.name}',
        'form': form,
        'program': program,
        'is_edit': True,
    }
    return render(request, 'backoffice/discounts/referral_form.html', context)


@login_required
@require_gym_permission('discounts.delete')
def referral_program_delete(request, pk):
    """Eliminar programa de referidos"""
    gym = request.gym
    user = request.user
    
    is_franchise_owner = hasattr(user, 'franchises_owned') and user.franchises_owned.exists()
    
    if is_franchise_owner:
        franchise = user.franchises_owned.first()
        program = get_object_or_404(ReferralProgram, pk=pk, gym__in=franchise.gyms.all())
    else:
        program = get_object_or_404(ReferralProgram, pk=pk, gym=gym)
    
    if request.method == 'POST':
        program.delete()
        from django.contrib import messages
        messages.success(request, 'Programa eliminado')
        return redirect('referral_program_list')
    
    context = {
        'title': f'Eliminar: {program.name}',
        'program': program,
    }
    return render(request, 'backoffice/discounts/referral_delete.html', context)


@login_required
@require_gym_permission('discounts.edit')
def referral_program_toggle(request, pk):
    """Activar/desactivar programa de referidos"""
    gym = request.gym
    user = request.user
    
    is_franchise_owner = hasattr(user, 'franchises_owned') and user.franchises_owned.exists()
    
    if is_franchise_owner:
        franchise = user.franchises_owned.first()
        program = get_object_or_404(ReferralProgram, pk=pk, gym__in=franchise.gyms.all())
    else:
        program = get_object_or_404(ReferralProgram, pk=pk, gym=gym)
    
    program.is_active = not program.is_active
    program.save(update_fields=['is_active'])
    
    from django.contrib import messages
    status = 'activado' if program.is_active else 'desactivado'
    messages.success(request, f'Programa {status}')
    
    return redirect('referral_program_list')


@login_required
@require_gym_permission('discounts.create')
def referral_program_duplicate(request, pk):
    """Duplicar programa de referidos (útil para franquicias)"""
    gym = request.gym
    user = request.user
    
    is_franchise_owner = hasattr(user, 'franchises_owned') and user.franchises_owned.exists()
    
    if is_franchise_owner:
        franchise = user.franchises_owned.first()
        program = get_object_or_404(ReferralProgram, pk=pk, gym__in=franchise.gyms.all())
        franchise_gyms = list(franchise.gyms.all())
    else:
        program = get_object_or_404(ReferralProgram, pk=pk, gym=gym)
        franchise_gyms = []
    
    if request.method == 'POST':
        target_gym_ids = request.POST.getlist('target_gyms')
        
        if target_gym_ids:
            from organizations.models import Gym
            count = 0
            for gym_id in target_gym_ids:
                # No duplicar en el mismo gym
                if int(gym_id) == program.gym_id:
                    continue
                    
                target_gym = Gym.objects.get(id=gym_id)
                
                # Crear copia
                new_program = ReferralProgram.objects.create(
                    gym=target_gym,
                    name=f"{program.name}",
                    description=program.description,
                    reward_type=program.reward_type,
                    referrer_credit_amount=program.referrer_credit_amount,
                    referrer_free_days=program.referrer_free_days,
                    referred_credit_amount=program.referred_credit_amount,
                    referred_free_days=program.referred_free_days,
                    require_membership_purchase=program.require_membership_purchase,
                    min_membership_value=program.min_membership_value,
                    min_referrals_for_bonus=program.min_referrals_for_bonus,
                    bonus_credit_amount=program.bonus_credit_amount,
                    max_referrals_per_client=program.max_referrals_per_client,
                    max_total_referrals=program.max_total_referrals,
                    valid_from=program.valid_from,
                    valid_until=program.valid_until,
                    is_active=program.is_active,
                )
                count += 1
            
            from django.contrib import messages
            messages.success(request, f'Programa duplicado a {count} gimnasio(s)')
        
        return redirect('referral_program_list')
    
    context = {
        'title': f'Duplicar: {program.name}',
        'program': program,
        'franchise_gyms': franchise_gyms,
        'is_franchise_owner': is_franchise_owner,
    }
    return render(request, 'backoffice/discounts/referral_duplicate.html', context)


@login_required
@require_gym_permission('discounts.view')
def referral_tracking(request):
    """Tracking de referidos del gimnasio con soporte de franquicia"""
    gym = request.gym
    user = request.user
    
    is_franchise_owner = hasattr(user, 'franchises_owned') and user.franchises_owned.exists()
    franchise = None
    franchise_gyms = []
    
    if is_franchise_owner:
        franchise = user.franchises_owned.first()
        franchise_gyms = list(franchise.gyms.all())
    
    # Filtros
    selected_gym_id = request.GET.get('gym', '')
    status_filter = request.GET.get('status', '')
    program_filter = request.GET.get('program', '')
    
    # Base query
    if is_franchise_owner and not selected_gym_id:
        referrals = Referral.objects.filter(program__gym__in=franchise_gyms)
    elif selected_gym_id:
        referrals = Referral.objects.filter(program__gym_id=selected_gym_id)
    else:
        referrals = Referral.objects.filter(program__gym=gym)
    
    # Aplicar filtros
    if status_filter:
        referrals = referrals.filter(status=status_filter)
    if program_filter:
        referrals = referrals.filter(program_id=program_filter)
    
    referrals = referrals.select_related(
        'referrer', 'referred', 'program', 'program__gym'
    ).order_by('-created_at')
    
    # Estadísticas
    all_referrals = referrals
    stats = {
        'total': all_referrals.count(),
        'pending': all_referrals.filter(status=Referral.Status.PENDING).count(),
        'registered': all_referrals.filter(status=Referral.Status.REGISTERED).count(),
        'completed': all_referrals.filter(status=Referral.Status.COMPLETED).count(),
        'rewarded': all_referrals.filter(status=Referral.Status.REWARDED).count(),
        'total_credit': all_referrals.aggregate(
            total=Sum('referrer_credit_given')
        )['total'] or Decimal('0.00'),
    }
    
    # Programas para filtro
    if is_franchise_owner:
        programs = ReferralProgram.objects.filter(gym__in=franchise_gyms)
    else:
        programs = ReferralProgram.objects.filter(gym=gym)
    
    context = {
        'title': 'Tracking de Referidos',
        'referrals': referrals[:200],
        'stats': stats,
        'is_franchise_owner': is_franchise_owner,
        'franchise': franchise,
        'franchise_gyms': franchise_gyms,
        'selected_gym_id': selected_gym_id,
        'status_filter': status_filter,
        'program_filter': program_filter,
        'programs': programs,
        'status_choices': Referral.Status.choices,
    }
    return render(request, 'backoffice/discounts/referral_tracking.html', context)


@login_required
@require_gym_permission('discounts.edit')
def referral_settings(request):
    """Configuración de referidos (activar/desactivar) para el gym actual"""
    gym = request.gym
    
    from organizations.models import PublicPortalSettings
    settings, _ = PublicPortalSettings.objects.get_or_create(gym=gym)
    
    if request.method == 'POST':
        settings.referral_program_enabled = request.POST.get('referral_program_enabled') == 'on'
        settings.referral_share_message = request.POST.get('referral_share_message', '')
        settings.save()
        
        from django.contrib import messages
        messages.success(request, 'Configuración guardada')
        return redirect('referral_program_list')
    
    context = {
        'title': 'Configuración de Referidos',
        'settings': settings,
        'gym': gym,
    }
    return render(request, 'backoffice/discounts/referral_settings.html', context)


@login_required
@require_gym_permission('discounts.edit')
def referral_settings_bulk(request):
    """Configuración masiva de referidos para franquicia"""
    user = request.user
    
    if not (hasattr(user, 'franchises_owned') and user.franchises_owned.exists()):
        from django.contrib import messages
        messages.error(request, 'Esta función solo está disponible para owners de franquicia')
        return redirect('referral_program_list')
    
    franchise = user.franchises_owned.first()
    franchise_gyms = list(franchise.gyms.all())
    
    from organizations.models import PublicPortalSettings
    
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_gym_ids = request.POST.getlist('selected_gyms')
        share_message = request.POST.get('referral_share_message', '')
        
        updated = 0
        for gym in franchise_gyms:
            if str(gym.id) in selected_gym_ids:
                settings, _ = PublicPortalSettings.objects.get_or_create(gym=gym)
                
                if action == 'enable':
                    settings.referral_program_enabled = True
                elif action == 'disable':
                    settings.referral_program_enabled = False
                
                if share_message:
                    settings.referral_share_message = share_message
                
                settings.save()
                updated += 1
        
        from django.contrib import messages
        messages.success(request, f'Configuración actualizada en {updated} gimnasio(s)')
        return redirect('referral_program_list')
    
    # Obtener estado actual de cada gym
    gym_states = []
    for gym in franchise_gyms:
        try:
            settings = PublicPortalSettings.objects.get(gym=gym)
            enabled = settings.referral_program_enabled
            message = settings.referral_share_message
        except PublicPortalSettings.DoesNotExist:
            enabled = False
            message = ''
        
        # Contar programas activos
        active_programs = ReferralProgram.objects.filter(gym=gym, is_active=True).count()
        
        gym_states.append({
            'gym': gym,
            'enabled': enabled,
            'message': message,
            'active_programs': active_programs,
        })
    
    context = {
        'title': 'Configuración Masiva de Referidos',
        'franchise': franchise,
        'gym_states': gym_states,
    }
    return render(request, 'backoffice/discounts/referral_settings_bulk.html', context)


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


# ==========================================
# EXPORT FUNCTIONS
# ==========================================
from django.http import HttpResponse
from core.export_service import GenericExportService, ExportConfig


@login_required
@require_gym_permission('discounts.view')
def discount_export_excel(request):
    """Exporta listado de descuentos a Excel"""
    gym = request.gym
    discounts = Discount.objects.filter(gym=gym).select_related('created_by')
    
    def format_discount_value(d):
        if d.discount_type == 'percentage':
            return f"{d.value}%"
        else:
            return f"€{d.value}"
    
    config = ExportConfig(
        title="Listado de Descuentos",
        headers=['ID', 'Nombre', 'Código', 'Tipo', 'Valor', 'Usos Máx.', 'Válido Desde', 'Válido Hasta', 'Estado'],
        data_extractor=lambda d: [
            d.id,
            d.name,
            d.code or '-',
            d.get_discount_type_display(),
            format_discount_value(d),
            d.max_uses if d.max_uses else 'Ilimitado',
            d.valid_from.strftime('%d/%m/%Y') if d.valid_from else '-',
            d.valid_until.strftime('%d/%m/%Y') if d.valid_until else '-',
            'Activo' if d.is_active else 'Inactivo',
        ],
        column_widths=[8, 25, 15, 14, 12, 12, 14, 14, 10]
    )
    
    excel_file = GenericExportService.export_to_excel(discounts.order_by('name'), config, gym.name)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="descuentos_{gym.name}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
@require_gym_permission('discounts.view')
def discount_export_pdf(request):
    """Exporta listado de descuentos a PDF"""
    gym = request.gym
    discounts = Discount.objects.filter(gym=gym).select_related('created_by')
    
    def format_discount_value(d):
        if d.discount_type == 'percentage':
            return f"{d.value}%"
        else:
            return f"€{d.value}"
    
    config = ExportConfig(
        title="Listado de Descuentos",
        headers=['Nombre', 'Código', 'Tipo', 'Valor', 'Válido Hasta', 'Estado'],
        data_extractor=lambda d: [
            d.name,
            d.code or '-',
            d.get_discount_type_display(),
            format_discount_value(d),
            d.valid_until.strftime('%d/%m/%Y') if d.valid_until else '-',
            'Activo' if d.is_active else 'Inactivo',
        ],
        column_widths=[25, 15, 14, 12, 14, 10]
    )
    
    pdf_file = GenericExportService.export_to_pdf(discounts.order_by('name'), config, gym.name)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="descuentos_{gym.name}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response
