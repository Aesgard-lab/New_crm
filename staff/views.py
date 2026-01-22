from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from accounts.decorators import require_gym_permission
from .models import StaffProfile, WorkShift, IncentiveRule, SalaryConfig, RatingIncentive
from .forms import IncentiveRuleForm

def staff_kiosk(request):
    """Renderiza la interfaz del Kiosco (Tablet)"""
    return render(request, "staff/kiosk.html")

@require_POST
def staff_checkin(request):
    """Procesa el fichaje por PIN"""
    pin = request.POST.get("pin")
    
    if not pin:
        return JsonResponse({
            "status": "error", 
            "message": "Por favor, introduce tu PIN"
        }, status=400)

    # Buscar empleado por PIN (y que esté activo)
    # TODO: Filtrar por Gym actual si la tablet está asignada a ubicación
    staff = StaffProfile.objects.select_related('user').filter(
        pin_code=pin, 
        is_active=True
    ).first()
    
    if not staff:
        return JsonResponse({
            "status": "error", 
            "message": "PIN incorrecto. Verifica tu código e intenta nuevamente."
        }, status=404)

    # Obtener nombre del empleado
    staff_name = staff.user.get_full_name() if hasattr(staff.user, 'get_full_name') else f"{staff.user.first_name} {staff.user.last_name}".strip()
    if not staff_name:
        staff_name = staff.user.email.split('@')[0]
    
    # Obtener foto si existe
    staff_photo = staff.photo.url if staff.photo else None

    # Buscar si tiene turno abierto
    open_shift = WorkShift.objects.filter(staff=staff, end_time__isnull=True).first()
    
    if open_shift:
        # Cerrar turno
        open_shift.end_time = timezone.now()
        open_shift.save()
        
        # Calcular duración
        duration = open_shift.duration_hours
        msg = f"¡Hasta luego! Trabajaste {duration}h hoy."
        
        return JsonResponse({
            "status": "success", 
            "action": "checkout", 
            "message": msg, 
            "staff_name": staff_name,
            "staff_photo": staff_photo,
            "duration_hours": duration,
            "shift_start": open_shift.start_time.isoformat()
        })
    else:
        # Abrir turno
        new_shift = WorkShift.objects.create(
            staff=staff,
            start_time=timezone.now(),
            method=WorkShift.Method.TABLET
        )
        
        msg = f"¡Que tengas un gran día de trabajo!"
        
        return JsonResponse({
            "status": "success", 
            "action": "checkin", 
            "message": msg, 
            "staff_name": staff_name,
            "staff_photo": staff_photo,
            "shift_start": new_shift.start_time.isoformat()
        })

# -----------------------------------------------------
# MANAGER VIEWS
# -----------------------------------------------------
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_gym_permission
from django.shortcuts import redirect, render, get_object_or_404
from .forms import StaffUserForm, StaffProfileForm
from .models import StaffProfile, WorkShift, StaffCommission, StaffTask
from django.db import transaction
from django.utils import timezone
from django.db.models import Exists, OuterRef, Sum

@login_required
@require_gym_permission("staff.view_staffprofile")
def staff_list(request):
    gym = request.gym
    
    # Subquery para saber si tiene turno abierto (está online)
    open_shift_exists = WorkShift.objects.filter(
        staff=OuterRef('pk'),
        end_time__isnull=True
    )
    
    # Filter by ID to avoid any object mismatches
    staff_members = StaffProfile.objects.filter(gym_id=gym.id).annotate(
        is_clocked_in=Exists(open_shift_exists)
    ).select_related('user').order_by('role', 'user__first_name')

    print(f"DEBUG: Staff List for Gym {gym.name} (ID: {gym.id}) - Count: {staff_members.count()}") # DEBUG
    if staff_members.count() == 0:
        print(f"DEBUG: No staff found. Checking database for Gym ID {gym.id}...")
        count_db = StaffProfile.objects.filter(gym_id=gym.id).count()
        print(f"DEBUG: Actual count in DB: {count_db}")

    context = {
        "staff_members": staff_members,
    }
    return render(request, "backoffice/staff/list.html", context)

@login_required
@require_gym_permission("staff.add_staffprofile")
def staff_create(request):
    gym = request.gym
    if request.method == "POST":
        user_form = StaffUserForm(request.POST)
        profile_form = StaffProfileForm(request.POST, request.FILES)
        
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                # 1. Create User
                user = user_form.save(commit=False)
                
                # Password handling
                password = user_form.cleaned_data.get('password')
                if password:
                    user.set_password(password)
                else:
                    user.set_password("1234") # Default if empty
                
                user.save()
                
                # 2. Create Profile
                profile = profile_form.save(commit=False)
                profile.user = user
                profile.gym = gym
                profile.save()
                
                # Handle Group Assignment
                group = profile_form.cleaned_data.get('assigned_role')
                if group:
                    user.groups.set([group])
                else:
                    user.groups.clear()
                
                # 3. Create Default Salary Config
                from .models import SalaryConfig
                SalaryConfig.objects.create(staff=profile, base_amount=0)
                
            return redirect("staff_list")
    else:
        user_form = StaffUserForm()
        profile_form = StaffProfileForm()

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "title": "Nuevo Empleado"
    }
    return render(request, "backoffice/staff/form.html", context)

@login_required
@require_gym_permission("staff.change_staffprofile")
def staff_edit(request, pk):
    profile = get_object_or_404(StaffProfile, pk=pk, gym=request.gym)
    user = profile.user
    
    if request.method == "POST":
        user_form = StaffUserForm(request.POST, instance=user)
        profile_form = StaffProfileForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user = user_form.save(commit=False)
                
                # Password handling (only update if provided)
                password = user_form.cleaned_data.get('password')
                if password:
                    user.set_password(password)
                    
                user.save()
                profile_form.save()
                
                # Handle Group Assignment
                group = profile_form.cleaned_data.get('assigned_role')
                if group:
                    user.groups.set([group])
                else:
                    user.groups.clear()
                
                # Handle Individual Permissions
                selected_perms = request.POST.getlist("permissions")
                managed_codenames = get_all_managed_permissions()
                perms_to_add = Permission.objects.filter(codename__in=selected_perms)
                managed_perm_ids = Permission.objects.filter(codename__in=managed_codenames).values_list('id', flat=True)
                
                # Remove all managed permissions and add back the selected ones
                user.user_permissions.remove(*managed_perm_ids)
                user.user_permissions.add(*perms_to_add)
                    
            return redirect("staff_list")
    else:
        user_form = StaffUserForm(instance=user)
        profile_form = StaffProfileForm(instance=profile)

    # Prepare permission structure for display
    current_user_perms = set(user.user_permissions.values_list('codename', flat=True))
    
    structured_perms = {}
    for module, actions in PERMISSION_STRUCTURE.items():
        structured_perms[module] = []
        for codename, label in actions:
            structured_perms[module].append({
                "codename": codename,
                "label": label,
                "is_active": codename in current_user_perms
            })

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "structured_permissions": structured_perms,
        "title": f"Editar {user.first_name}"
    }
    return render(request, "backoffice/staff/form.html", context)

@login_required
@require_gym_permission("staff.view_staffprofile")
def staff_detail(request, pk):
    profile = get_object_or_404(StaffProfile, pk=pk, gym=request.gym)
    
    # KPIs Mensuales
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Horas trabajadas este mes
    shifts_this_month = WorkShift.objects.filter(staff=profile, start_time__gte=month_start)
    total_hours = sum(s.duration_hours for s in shifts_this_month)
    
    # Comisiones este mes
    from django.db.models import Sum, Avg
    commissions_this_month_total = StaffCommission.objects.filter(staff=profile, date__gte=month_start).aggregate(total=Sum('amount'))['total'] or 0
    
    # Detalle de comisiones recientes (últimas 10)
    recent_commissions = StaffCommission.objects.filter(
        staff=profile, 
        date__gte=month_start
    ).select_related('rule').order_by('-date')[:10]
    
    # Calcular bono por rating
    from activities.models import ClassReview
    rating_bonus = 0
    rating_info = None
    
    # Obtener reviews del período configurado (usamos el más amplio de todos los incentivos activos)
    rating_incentives = RatingIncentive.objects.filter(
        gym=request.gym,
        is_active=True
    ).filter(
        models.Q(staff__isnull=True) | models.Q(staff=profile)
    ).order_by('-period_days').first()
    
    if rating_incentives:
        period_start = now - timezone.timedelta(days=rating_incentives.period_days)
        
        # Obtener reviews del instructor en el período
        reviews = ClassReview.objects.filter(
            session__staff=profile,
            session__gym=request.gym,
            created_at__gte=period_start
        )
        
        review_count = reviews.count()
        if review_count > 0:
            avg_rating = reviews.aggregate(avg=Avg('instructor_rating'))['avg'] or 0
            
            # Buscar todas las reglas que apliquen
            applicable_rules = RatingIncentive.objects.filter(
                gym=request.gym,
                is_active=True,
                min_rating__lte=avg_rating,
                min_reviews__lte=review_count
            ).filter(
                models.Q(staff__isnull=True) | models.Q(staff=profile)
            ).order_by('-min_rating')
            
            # Aplicar la regla con el rating mínimo más alto que cumpla
            best_rule = applicable_rules.first()
            if best_rule:
                # Calcular el salario base para el bono
                base_salary = SalaryConfig.objects.filter(staff=profile).first()
                if base_salary:
                    base_amount = base_salary.base_amount or 0
                    if base_salary.mode == 'HOURLY':
                        base_amount = base_amount * total_hours
                    
                    rating_bonus = best_rule.calculate_bonus(base_amount, avg_rating, review_count)
                    rating_info = {
                        'avg_rating': round(avg_rating, 2),
                        'review_count': review_count,
                        'rule_name': str(best_rule),
                        'level': best_rule.level,
                        'min_rating': float(best_rule.min_rating),
                        'bonus': rating_bonus,
                    }
    
    # Datos recientes
    recent_shifts = profile.shifts.order_by('-start_time')[:5]
    recent_tasks = profile.assigned_tasks.order_by('-created_at')[:5]
    
    is_clocked_in = profile.shifts.filter(end_time__isnull=True).exists()

    from .models import SalaryConfig
    salary_config, _ = SalaryConfig.objects.get_or_create(staff=profile)
    from .forms import StaffSalaryForm, StaffTaskForm
    
    # Calcular salario estimado del mes
    base_salary = salary_config.base_amount or 0
    estimated_salary = 0
    
    if salary_config and salary_config.mode:
        if salary_config.mode == 'MONTHLY':
            estimated_salary = base_salary
        elif salary_config.mode == 'HOURLY':
            estimated_salary = base_salary * total_hours
    
    # Total a cobrar = Salario + Comisiones + Bono por Rating
    total_to_earn = estimated_salary + commissions_this_month_total + rating_bonus
    
    context = {
        "profile": profile,
        "total_hours": round(total_hours, 1),
        "total_commissions": commissions_this_month_total,
        "recent_commissions": recent_commissions,
        "rating_bonus": rating_bonus,
        "rating_info": rating_info,
        "recent_shifts": recent_shifts,
        "recent_tasks": recent_tasks,
        "is_clocked_in": is_clocked_in,
        "salary_form": StaffSalaryForm(instance=salary_config),
        "task_form": StaffTaskForm(),
        "salary_config": salary_config,
        "estimated_salary": estimated_salary,
        "total_to_earn": total_to_earn,
    }
    return render(request, "backoffice/staff/detail.html", context)

@login_required
@require_gym_permission("staff.change_staffprofile")
def staff_detail_salary(request, pk):
    """Updates Salary Configuration"""
    profile = get_object_or_404(StaffProfile, pk=pk, gym=request.gym)
    salary_config, created = SalaryConfig.objects.get_or_create(staff=profile)
    
    if request.method == "POST":
        from .forms import StaffSalaryForm
        form = StaffSalaryForm(request.POST, instance=salary_config)
        if form.is_valid():
            form.save()
            return redirect("staff_detail", pk=pk)
        else:
            print("SALARY FORM ERRORS:", form.errors) # DEBUG
    
    return redirect("staff_detail", pk=pk)

@login_required
@require_gym_permission("staff.change_staffprofile")
def staff_toggle_shift(request, pk):
    """Manually toggles staff shift state (Manager Override)"""
    profile = get_object_or_404(StaffProfile, pk=pk, gym=request.gym)
    
    # Check if currently clocked in
    open_shift = WorkShift.objects.filter(staff=profile, end_time__isnull=True).first()
    
    if open_shift:
        # Clock OUT
        open_shift.end_time = timezone.now()
        open_shift.save()
    else:
        # Clock IN
        WorkShift.objects.create(
            staff=profile,
            start_time=timezone.now(),
            method=WorkShift.Method.MANUAL # You might need to add this choice to model
        )
        
    return redirect("staff_detail", pk=pk)

@login_required
@require_gym_permission("staff.change_staffprofile")
def staff_task_add(request, pk):
    """Assigns a new task to staff"""
    profile = get_object_or_404(StaffProfile, pk=pk, gym=request.gym)
    
    if request.method == "POST":
        from .forms import StaffTaskForm
        form = StaffTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.assigned_to = profile
            task.created_by = request.user
            task.gym = request.gym
            task.save()
            return redirect("staff_detail", pk=pk)
            
    return redirect("staff_detail", pk=pk)


# -----------------------------------------------------
# ROLE & PERMISSIONS MANAGEMENT
# -----------------------------------------------------
from django.contrib.auth.models import Group, Permission
from .perms import PERMISSION_STRUCTURE, get_all_managed_permissions

@login_required
@require_gym_permission("staff.manage_roles")
def role_list(request):
    """Lists all available Role Groups"""
    # In a real multi-tenant app, Groups might need to be filtered by Gym or have a Gym prefix.
    # For now, we assume global groups or shared ones. 
    # To support per-gym roles, we would need a GymGroup model or naming convention "GymID_RoleName".
    # We will stick to simple Global Groups for this MVP (e.g. "Manager", "Trainer") shared across the app,
    # OR we filter by names that are relevant.
    
    roles = Group.objects.all().order_by('name')
    
    context = {
        "roles": roles,
        "title": "Roles y Permisos"
    }
    return render(request, "backoffice/settings/staff/role_list.html", context)

@login_required
@require_gym_permission("staff.manage_roles")
def role_edit(request, role_id):
    """Matrix UI to edit permissions for a specific Group"""
    role = get_object_or_404(Group, pk=role_id)
    
    if request.method == "POST":
        # Process Matrix
        selected_perms = request.POST.getlist("permissions") # List of codenames
        
        # 1. Clear current managed permissions
        managed_codenames = get_all_managed_permissions()
        
        # We need to find Permission objects for these codenames
        # Note: This is a bit loose because codenames might duplicate across apps, 
        # but usually unique enough for this context.
        perms_to_add = Permission.objects.filter(codename__in=selected_perms)
        
        # Update Group (set works if we want to replace ALL, but we only want to touch managed ones)
        # Safer strategy: remove all managed, add back selected.
        
        # Get IDs of all permissions that are "managed" by our system
        managed_perm_ids = Permission.objects.filter(codename__in=managed_codenames).values_list('id', flat=True)
        
        # Remove managed perms from this group
        role.permissions.remove(*managed_perm_ids)
        
        # Add new selected perms
        role.permissions.add(*perms_to_add)
        
        return redirect("role_list")

    # Prepare View Data
    # We need to mark which ones are active
    current_perms = set(role.permissions.values_list('codename', flat=True))
    
    structured_perms = {}
    for module, actions in PERMISSION_STRUCTURE.items():
        structured_perms[module] = []
        for codename, label in actions:
            structured_perms[module].append({
                "codename": codename,
                "label": label,
                "is_active": codename in current_perms
            })

    context = {
        "role": role,
        "structured_permissions": structured_perms,
        "title": f"Editar Rol: {role.name}"
    }
    return render(request, "backoffice/settings/staff/role_edit.html", context)

@login_required
@require_gym_permission("staff.manage_roles")
def role_create(request):
    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            Group.objects.create(name=name)
        return redirect("role_list")
    return redirect("role_list")


# -----------------------------------------------------
# AUDIT LOGS
# -----------------------------------------------------
@login_required
@require_gym_permission("staff.view_staffprofile") # Or a specific permission
def audit_log_list(request):
    """Lists system audit logs"""
    from .models import AuditLog
    
    gym = request.gym
    logs = AuditLog.objects.filter(gym=gym).select_related('user').order_by('-timestamp')[:100] # Last 100
    
    context = {
        "logs": logs,
        "title": "Registro de Auditoría"
    }
    return render(request, "backoffice/settings/system/audit_logs.html", context)


# --- Incentive Rules CRUD ---

@login_required
@require_gym_permission('staff.view_incentiverule')
@login_required
def incentive_list(request):
    """Lista todas las reglas de incentivos del gym"""
    gym = request.gym
    user = request.user
    
    # Verificar permisos
    can_view_all = user.has_perm('staff.view_all_incentives')
    can_view_own = user.has_perm('staff.view_own_incentives')
    
    if can_view_all:
        # Ver todos los incentivos del gym
        incentives = IncentiveRule.objects.filter(gym=gym).select_related('staff__user').order_by('-created_at')
    elif can_view_own and hasattr(user, 'staff_profile'):
        # Ver solo incentivos propios (globales del gym + específicos del empleado)
        incentives = IncentiveRule.objects.filter(
            gym=gym
        ).filter(
            models.Q(staff__isnull=True) | models.Q(staff=user.staff_profile)
        ).select_related('staff__user').order_by('-created_at')
    else:
        # Sin permisos
        messages.warning(request, '⚠️ No tienes permisos para ver incentivos')
        return redirect('staff_dashboard')
    
    context = {
        'title': 'Configurar Incentivos',
        'incentives': incentives,
        'can_view_all': can_view_all,
        'can_view_own': can_view_own,
    }
    return render(request, 'backoffice/staff/incentive_list.html', context)


@login_required
@require_gym_permission('staff.add_incentiverule')
def incentive_create(request):
    """Crear nueva regla de incentivo"""
    gym = request.gym
    
    if request.method == 'POST':
        form = IncentiveRuleForm(request.POST, gym=gym)
        if form.is_valid():
            incentive = form.save(commit=False)
            incentive.gym = gym
            incentive.save()
            messages.success(request, f'✅ Incentivo "{incentive.name}" creado correctamente')
            return redirect('incentive_list')
    else:
        form = IncentiveRuleForm(gym=gym)
    
    context = {
        'title': 'Crear Incentivo',
        'form': form,
        'is_create': True,
    }
    return render(request, 'backoffice/staff/incentive_form.html', context)


@login_required
@require_gym_permission('staff.change_incentiverule')
def incentive_edit(request, pk):
    """Editar regla de incentivo"""
    gym = request.gym
    incentive = get_object_or_404(IncentiveRule, pk=pk, gym=gym)
    
    if request.method == 'POST':
        form = IncentiveRuleForm(request.POST, instance=incentive, gym=gym)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Incentivo "{incentive.name}" actualizado')
            return redirect('incentive_list')
    else:
        form = IncentiveRuleForm(instance=incentive, gym=gym)
    
    context = {
        'title': f'Editar: {incentive.name}',
        'form': form,
        'incentive': incentive,
        'is_create': False,
    }
    return render(request, 'backoffice/staff/incentive_form.html', context)


@login_required
@require_gym_permission('staff.delete_incentiverule')
def incentive_delete(request, pk):
    """Eliminar regla de incentivo"""
    gym = request.gym
    incentive = get_object_or_404(IncentiveRule, pk=pk, gym=gym)
    
    if request.method == 'POST':
        name = incentive.name
        incentive.delete()
        messages.success(request, f'✅ Incentivo "{name}" eliminado')
        return redirect('incentive_list')
    
    context = {
        'title': f'Eliminar: {incentive.name}',
        'incentive': incentive,
    }
    return render(request, 'backoffice/staff/incentive_confirm_delete.html', context)


# -----------------------------------------------------
# RATING INCENTIVES (Class Reviews)
# -----------------------------------------------------

@login_required
@require_gym_permission('staff.view_ratingincentive')
def rating_incentive_list(request):
    """View all rating-based incentive rules"""
    from .models import RatingIncentive
    gym = request.gym
    
    incentives = RatingIncentive.objects.filter(
        gym=gym
    ).select_related('staff__user').order_by('-min_rating')
    
    context = {
        'title': 'Incentivos por Rating',
        'incentives': incentives,
    }
    return render(request, 'backoffice/staff/rating_incentive_list.html', context)


@login_required
@require_gym_permission('staff.add_ratingincentive')
def rating_incentive_create(request):
    """Create new rating incentive rule"""
    from .models import RatingIncentive
    gym = request.gym
    
    if request.method == 'POST':
        # Manual form processing
        staff_id = request.POST.get('staff')
        min_rating = request.POST.get('min_rating')
        bonus_type = request.POST.get('bonus_type')
        bonus_value = request.POST.get('bonus_value')
        level = request.POST.get('level')
        min_reviews = request.POST.get('min_reviews', 10)
        period_days = request.POST.get('period_days', 30)
        
        incentive = RatingIncentive.objects.create(
            gym=gym,
            staff_id=staff_id if staff_id else None,
            min_rating=min_rating,
            bonus_type=bonus_type,
            bonus_value=bonus_value,
            level=level if level else None,
            min_reviews=min_reviews,
            period_days=period_days,
            is_active=True
        )
        
        messages.success(request, f'✅ Incentivo por rating creado correctamente')
        return redirect('rating_incentive_list')
    
    # Get active staff
    staff_members = StaffProfile.objects.filter(gym=gym, is_active=True).select_related('user')
    
    context = {
        'title': 'Crear Incentivo por Rating',
        'staff_members': staff_members,
        'is_create': True,
    }
    return render(request, 'backoffice/staff/rating_incentive_form.html', context)


@login_required
@require_gym_permission('staff.change_ratingincentive')
def rating_incentive_edit(request, pk):
    """Edit rating incentive rule"""
    from .models import RatingIncentive
    gym = request.gym
    incentive = get_object_or_404(RatingIncentive, pk=pk, gym=gym)
    
    if request.method == 'POST':
        staff_id = request.POST.get('staff')
        incentive.staff_id = staff_id if staff_id else None
        incentive.min_rating = request.POST.get('min_rating')
        incentive.bonus_type = request.POST.get('bonus_type')
        incentive.bonus_value = request.POST.get('bonus_value')
        incentive.level = request.POST.get('level') or None
        incentive.min_reviews = request.POST.get('min_reviews', 10)
        incentive.period_days = request.POST.get('period_days', 30)
        incentive.is_active = request.POST.get('is_active') == 'on'
        incentive.save()
        
        messages.success(request, f'✅ Incentivo actualizado correctamente')
        return redirect('rating_incentive_list')
    
    staff_members = StaffProfile.objects.filter(gym=gym, is_active=True).select_related('user')
    
    context = {
        'title': 'Editar Incentivo por Rating',
        'incentive': incentive,
        'staff_members': staff_members,
        'is_create': False,
    }
    return render(request, 'backoffice/staff/rating_incentive_form.html', context)


@login_required
@require_gym_permission('staff.delete_ratingincentive')
def rating_incentive_delete(request, pk):
    """Delete rating incentive rule"""
    from .models import RatingIncentive
    gym = request.gym
    incentive = get_object_or_404(RatingIncentive, pk=pk, gym=gym)
    
    if request.method == 'POST':
        incentive.delete()
        messages.success(request, f'✅ Incentivo por rating eliminado')
        return redirect('rating_incentive_list')
    
    context = {
        'title': 'Eliminar Incentivo',
        'incentive': incentive,
    }
    return render(request, 'backoffice/staff/rating_incentive_confirm_delete.html', context)


@login_required
@require_gym_permission('staff.view_staffprofile')
def staff_rating_performance(request):
    """
    Dashboard showing staff performance based on class reviews
    Shows current month ratings, bonuses, and performance levels
    """
    from activities.models import ClassReview
    from .models import RatingIncentive, SalaryConfig
    from django.db.models import Avg, Count
    from datetime import timedelta
    
    gym = request.gym
    now = timezone.now()
    
    # Get period from request (default 30 days)
    period_days = int(request.GET.get('period', 30))
    start_date = now - timedelta(days=period_days)
    
    # Get all active instructors
    instructors = StaffProfile.objects.filter(
        gym=gym,
        is_active=True,
        role=StaffProfile.Role.TRAINER
    ).select_related('user')
    
    performance_data = []
    
    for instructor in instructors:
        # Get reviews for this instructor in period
        reviews = ClassReview.objects.filter(
            session__staff=instructor,
            session__gym=gym,
            created_at__gte=start_date
        )
        
        total_reviews = reviews.count()
        
        if total_reviews > 0:
            avg_instructor_rating = reviews.aggregate(avg=Avg('instructor_rating'))['avg']
            avg_class_rating = reviews.aggregate(avg=Avg('class_rating'))['avg']
        else:
            avg_instructor_rating = 0
            avg_class_rating = 0
        
        # Calculate applicable bonuses
        applicable_incentives = RatingIncentive.objects.filter(
            gym=gym,
            is_active=True,
            period_days=period_days
        ).filter(
            models.Q(staff=instructor) | models.Q(staff__isnull=True)
        ).filter(
            min_rating__lte=avg_instructor_rating,
            min_reviews__lte=total_reviews
        ).order_by('-min_rating')
        
        # Get highest applicable incentive
        best_incentive = applicable_incentives.first()
        
        # Calculate bonus amount
        bonus_amount = 0
        level = None
        
        if best_incentive:
            try:
                salary_config = SalaryConfig.objects.get(staff=instructor)
                base_salary = float(salary_config.base_amount)
            except SalaryConfig.DoesNotExist:
                base_salary = 0
            
            bonus_amount = best_incentive.calculate_bonus(
                base_salary,
                avg_instructor_rating,
                total_reviews
            )
            level = best_incentive.level
        
        performance_data.append({
            'instructor': instructor,
            'total_reviews': total_reviews,
            'avg_instructor_rating': round(avg_instructor_rating, 2) if avg_instructor_rating else 0,
            'avg_class_rating': round(avg_class_rating, 2) if avg_class_rating else 0,
            'bonus_amount': round(bonus_amount, 2),
            'level': level,
            'best_incentive': best_incentive
        })
    
    # Sort by avg_instructor_rating descending
    performance_data.sort(key=lambda x: x['avg_instructor_rating'], reverse=True)
    
    context = {
        'title': 'Rendimiento por Ratings',
        'performance_data': performance_data,
        'period_days': period_days,
    }
    return render(request, 'backoffice/staff/rating_performance.html', context)


@login_required
def my_commissions(request):
    """Vista para que el staff vea sus propias comisiones"""
    try:
        staff_profile = request.user.staff_profile
    except StaffProfile.DoesNotExist:
        return render(request, 'backoffice/staff/my_commissions.html', {
            'error': 'No tienes un perfil de empleado asociado.'
        })
    
    # Periodo actual (mes actual)
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Obtener comisiones del mes actual
    from django.db.models import Sum
    commissions_this_month = StaffCommission.objects.filter(
        staff=staff_profile,
        date__gte=month_start
    ).select_related('rule').order_by('-date')
    
    total_month = commissions_this_month.aggregate(total=Sum('amount'))['total'] or 0
    
    # Obtener todas las comisiones (últimas 30)
    all_commissions = StaffCommission.objects.filter(
        staff=staff_profile
    ).select_related('rule').order_by('-date')[:30]
    
    total_all_time = StaffCommission.objects.filter(
        staff=staff_profile
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Información de salario
    try:
        salary_config = SalaryConfig.objects.get(staff=staff_profile)
    except SalaryConfig.DoesNotExist:
        salary_config = None
    
    # Horas trabajadas este mes
    shifts_this_month = WorkShift.objects.filter(
        staff=staff_profile,
        start_time__gte=month_start
    )
    total_hours = sum(s.duration_hours for s in shifts_this_month)
    
    # Calcular salario estimado
    estimated_salary = 0
    if salary_config:
        if salary_config.mode == 'MONTHLY':
            estimated_salary = salary_config.base_amount or 0
        elif salary_config.mode == 'HOURLY':
            estimated_salary = (salary_config.base_amount or 0) * total_hours
    
    # Calcular bono por rating
    from django.db.models import Avg
    from activities.models import ClassReview
    rating_bonus = 0
    rating_info = None
    
    # Obtener el incentivo por rating más amplio
    rating_incentives = RatingIncentive.objects.filter(
        gym=staff_profile.gym,
        is_active=True
    ).filter(
        models.Q(staff__isnull=True) | models.Q(staff=staff_profile)
    ).order_by('-period_days').first()
    
    if rating_incentives:
        period_start = now - timezone.timedelta(days=rating_incentives.period_days)
        
        # Obtener reviews del instructor
        reviews = ClassReview.objects.filter(
            session__staff=staff_profile,
            session__gym=staff_profile.gym,
            created_at__gte=period_start
        )
        
        review_count = reviews.count()
        if review_count > 0:
            avg_rating = reviews.aggregate(avg=Avg('instructor_rating'))['avg'] or 0
            
            # Buscar reglas aplicables
            applicable_rules = RatingIncentive.objects.filter(
                gym=staff_profile.gym,
                is_active=True,
                min_rating__lte=avg_rating,
                min_reviews__lte=review_count
            ).filter(
                models.Q(staff__isnull=True) | models.Q(staff=staff_profile)
            ).order_by('-min_rating')
            
            best_rule = applicable_rules.first()
            if best_rule:
                rating_bonus = best_rule.calculate_bonus(estimated_salary, avg_rating, review_count)
                rating_info = {
                    'avg_rating': round(avg_rating, 2),
                    'review_count': review_count,
                    'rule_name': str(best_rule),
                    'level': best_rule.level,
                    'min_rating': float(best_rule.min_rating),
                    'bonus': rating_bonus,
                }
    
    total_to_earn = estimated_salary + total_month + rating_bonus
    
    context = {
        'title': 'Mis Comisiones',
        'staff_profile': staff_profile,
        'commissions_this_month': commissions_this_month,
        'all_commissions': all_commissions,
        'total_month': total_month,
        'total_all_time': total_all_time,
        'salary_config': salary_config,
        'total_hours': round(total_hours, 1),
        'estimated_salary': estimated_salary,
        'rating_bonus': rating_bonus,
        'rating_info': rating_info,
        'total_to_earn': total_to_earn,
    }
    return render(request, 'backoffice/staff/my_commissions.html', context)

