from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from accounts.decorators import require_gym_permission
from core.audit_decorators import log_action
from .models import StaffProfile, WorkShift, IncentiveRule, SalaryConfig, RatingIncentive
from .forms import IncentiveRuleForm

def staff_kiosk(request, gym_slug=None):
    """Renderiza la interfaz del Kiosco (Tablet)
    
    El kiosco puede identificar el gimnasio de varias formas:
    1. Por slug en la URL: /staff/kiosk/mi-gimnasio/
    2. Por parámetro GET: /staff/kiosk/?gym=1
    3. Por sesión del usuario autenticado
    """
    from organizations.models import Gym
    
    gym = None
    
    # Opción 1: Por slug en URL
    if gym_slug:
        gym = Gym.objects.filter(slug=gym_slug).first()
    
    # Opción 2: Por parámetro GET
    if not gym:
        gym_id = request.GET.get('gym')
        if gym_id:
            gym = Gym.objects.filter(id=gym_id).first()
    
    # Opción 3: Por sesión del usuario autenticado
    if not gym and hasattr(request, 'gym'):
        gym = request.gym
    
    context = {
        'gym': gym,
        'gym_id': gym.id if gym else None,
        'gym_name': gym.name if gym else 'Gimnasio',
    }
    
    return render(request, "staff/kiosk.html", context)

@require_POST
def staff_check_status(request):
    """Verifica el estado del empleado sin fichar (para mostrar confirmación)"""
    from organizations.models import Gym
    
    pin = request.POST.get("pin")
    gym_id = request.POST.get("gym_id")
    
    if not pin:
        return JsonResponse({"status": "error", "message": "PIN requerido"}, status=400)
    
    # Obtener gimnasio
    gym = None
    if gym_id:
        gym = Gym.objects.filter(id=gym_id).first()
    if not gym and hasattr(request, 'gym'):
        gym = request.gym
    
    # Buscar empleado
    staff_query = StaffProfile.objects.select_related('user', 'gym').filter(pin_code=pin, is_active=True)
    if gym:
        staff_query = staff_query.filter(gym=gym)
    staff = staff_query.first()
    
    if not staff:
        return JsonResponse({"status": "error", "message": "PIN incorrecto"}, status=404)
    
    staff_name = staff.user.get_full_name() or staff.user.email.split('@')[0]
    staff_photo = staff.photo.url if staff.photo else None
    
    # Determinar método de fichaje requerido
    checkin_method = staff.checkin_method  # ANY, PIN, FACIAL, GEO, PHOTO
    require_photo = (
        checkin_method in ['FACIAL', 'PHOTO'] or 
        (gym and gym.require_checkin_photo)
    )
    require_geo = (
        checkin_method == 'GEO' or 
        (gym and gym.require_checkin_geolocation)
    )
    
    # Verificar turno abierto
    open_shift = WorkShift.objects.filter(staff=staff, end_time__isnull=True).first()
    
    base_response = {
        "status": "success",
        "staff_name": staff_name,
        "staff_photo": staff_photo,
        "checkin_method": checkin_method,
        "require_photo": require_photo,
        "require_geo": require_geo,
    }
    
    if open_shift:
        duration = open_shift.duration_hours
        hours = int(duration)
        minutes = int((duration - hours) * 60)
        return JsonResponse({
            **base_response,
            "action": "checkout",
            "message": f"Llevas {hours}h {minutes}min trabajando",
            "shift_start": open_shift.start_time.isoformat(),
            "duration_hours": duration
        })
    else:
        return JsonResponse({
            **base_response,
            "action": "checkin",
            "message": "Vas a iniciar tu jornada"
        })


@require_POST
def staff_checkin(request):
    """Procesa el fichaje por PIN
    
    El gimnasio se identifica por:
    1. Parámetro gym_id en el POST
    2. Sesión del usuario autenticado (request.gym)
    
    IMPORTANTE: El PIN solo es válido dentro del gimnasio especificado
    para evitar colisiones entre gimnasios.
    
    Parámetros adicionales opcionales:
    - photo: base64 de la foto capturada
    - latitude, longitude: coordenadas GPS
    """
    from organizations.models import Gym
    from django.core.files.base import ContentFile
    import base64
    import math
    
    pin = request.POST.get("pin")
    gym_id = request.POST.get("gym_id")
    photo_data = request.POST.get("photo")  # base64
    latitude = request.POST.get("latitude")
    longitude = request.POST.get("longitude")
    
    if not pin:
        return JsonResponse({
            "status": "error", 
            "message": "Por favor, introduce tu PIN"
        }, status=400)
    
    # Obtener el gimnasio actual
    gym = None
    
    # Opción 1: gym_id en POST
    if gym_id:
        gym = Gym.objects.filter(id=gym_id).first()
    
    # Opción 2: Desde la sesión del usuario
    if not gym and hasattr(request, 'gym'):
        gym = request.gym
    
    # Construir query base
    staff_query = StaffProfile.objects.select_related('user', 'gym').filter(
        pin_code=pin, 
        is_active=True
    )
    
    # Filtrar por gimnasio si está disponible (RECOMENDADO)
    if gym:
        staff_query = staff_query.filter(gym=gym)
    
    staff = staff_query.first()
    
    if not staff:
        return JsonResponse({
            "status": "error", 
            "message": "PIN incorrecto. Verifica tu código e intenta nuevamente."
        }, status=404)
    
    # Validar geolocalización si es requerida
    if gym and gym.require_checkin_geolocation:
        if not latitude or not longitude:
            return JsonResponse({
                "status": "error",
                "message": "Se requiere ubicación GPS para fichar"
            }, status=400)
        
        if gym.latitude and gym.longitude:
            # Calcular distancia con fórmula Haversine
            distance = _calculate_distance(
                float(gym.latitude), float(gym.longitude),
                float(latitude), float(longitude)
            )
            
            if distance > gym.geofence_radius:
                return JsonResponse({
                    "status": "error",
                    "message": f"Debes estar en el gimnasio para fichar (distancia: {int(distance)}m)"
                }, status=400)
    
    # Validar foto si es requerida
    if gym and gym.require_checkin_photo:
        if not photo_data:
            return JsonResponse({
                "status": "error",
                "message": "Se requiere foto para fichar"
            }, status=400)

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
        
        # Guardar foto de checkout si se proporcionó
        if photo_data:
            open_shift.checkout_photo = _decode_base64_photo(photo_data, f"checkout_{staff.id}")
        
        # Guardar ubicación de checkout
        if latitude and longitude:
            open_shift.checkout_latitude = latitude
            open_shift.checkout_longitude = longitude
        
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
        # Determinar método basado en lo que se envió
        method = WorkShift.Method.TABLET
        if photo_data:
            method = WorkShift.Method.FACIAL
        elif latitude and longitude:
            method = WorkShift.Method.MOBILE
        
        # Abrir turno
        new_shift = WorkShift.objects.create(
            staff=staff,
            start_time=timezone.now(),
            method=method,
            checkin_latitude=latitude if latitude else None,
            checkin_longitude=longitude if longitude else None,
        )
        
        # Guardar foto de checkin si se proporcionó
        if photo_data:
            new_shift.checkin_photo = _decode_base64_photo(photo_data, f"checkin_{staff.id}")
            new_shift.save()
        
        msg = f"¡Que tengas un gran día de trabajo!"
        
        return JsonResponse({
            "status": "success", 
            "action": "checkin", 
            "message": msg, 
            "staff_name": staff_name,
            "staff_photo": staff_photo,
            "shift_start": new_shift.start_time.isoformat()
        })


def _calculate_distance(lat1, lon1, lat2, lon2):
    """Calcula distancia en metros entre dos coordenadas usando Haversine"""
    import math
    R = 6371000  # Radio de la Tierra en metros
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def _decode_base64_photo(base64_data, filename_prefix):
    """Decodifica una imagen base64 y retorna un ContentFile"""
    from django.core.files.base import ContentFile
    import base64
    import uuid
    
    # Remover header del data URL si existe
    if ',' in base64_data:
        base64_data = base64_data.split(',')[1]
    
    try:
        image_data = base64.b64decode(base64_data)
        filename = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.jpg"
        return ContentFile(image_data, name=filename)
    except Exception:
        return None

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
    # Optimizado: prefetch_related para roles y grupos del usuario
    staff_members = StaffProfile.objects.filter(gym_id=gym.id).annotate(
        is_clocked_in=Exists(open_shift_exists)
    ).select_related('user').prefetch_related(
        'user__groups'
    ).order_by('role', 'user__first_name')

    context = {
        "staff_members": staff_members,
    }
    return render(request, "backoffice/staff/list.html", context)

@login_required
@require_gym_permission("staff.add_staffprofile")
@log_action("CREATE", "Empleados")
def staff_create(request):
    gym = request.gym
    if request.method == "POST":
        user_form = StaffUserForm(request.POST)
        profile_form = StaffProfileForm(request.POST, request.FILES, gym=gym)
        
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
        profile_form = StaffProfileForm(gym=gym)

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "title": "Nuevo Empleado"
    }
    return render(request, "backoffice/staff/form.html", context)

@login_required
@require_gym_permission("staff.change_staffprofile")
@log_action("UPDATE", "Empleados", get_target=lambda req, args, kwargs: f"Staff #{kwargs.get('pk')}")
def staff_edit(request, pk):
    profile = get_object_or_404(StaffProfile, pk=pk, gym=request.gym)
    user = profile.user
    gym = request.gym
    
    if request.method == "POST":
        user_form = StaffUserForm(request.POST, instance=user)
        profile_form = StaffProfileForm(request.POST, request.FILES, instance=profile, gym=gym)
        
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
        profile_form = StaffProfileForm(instance=profile, gym=gym)

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
def staff_toggle_active(request, pk):
    """Activa/desactiva un empleado"""
    profile = get_object_or_404(StaffProfile, pk=pk, gym=request.gym)
    
    if request.method == "POST":
        profile.is_active = not profile.is_active
        profile.save()
        
        status = "activado" if profile.is_active else "desactivado"
        messages.success(request, f"Empleado {profile.user.get_full_name()} {status}.")
    
    return redirect("staff_list")


@login_required
@require_gym_permission("staff.delete_staffprofile")
def staff_delete(request, pk):
    """Elimina un empleado (soft delete: desactiva)"""
    profile = get_object_or_404(StaffProfile, pk=pk, gym=request.gym)
    
    if request.method == "POST":
        # Soft delete - desactivar
        force_delete = request.POST.get('force_delete') == '1'
        
        if force_delete:
            # Hard delete - eliminar completamente
            name = profile.user.get_full_name()
            user = profile.user
            profile.delete()
            # Verificar si el usuario tiene otros perfiles antes de eliminarlo
            if not StaffProfile.objects.filter(user=user).exists():
                user.is_active = False
                user.save()
            messages.success(request, f"Empleado {name} eliminado permanentemente.")
        else:
            # Soft delete - solo desactivar
            profile.is_active = False
            profile.save()
            messages.success(request, f"Empleado {profile.user.get_full_name()} desactivado.")
    
    return redirect("staff_list")


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
@require_gym_permission("staff.view_auditlog")
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


# =====================================================
# VACATION & ABSENCE MANAGEMENT VIEWS
# =====================================================
from .models import (
    VacationPolicy, StaffVacationBalance, VacationRequest, 
    AbsenceType, BlockedVacationPeriod
)
from .forms import VacationRequestForm, VacationPolicyForm, BlockedPeriodForm, BalanceAdjustForm
import json
from datetime import datetime, timedelta
from django.db.models import Q
from calendar import monthrange


@login_required
@require_gym_permission("staff.view_vacation")
def vacation_calendar(request):
    """Vista de calendario de vacaciones del equipo"""
    gym = request.gym
    
    # Obtener mes/año actual o del parámetro
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    # Rango del mes
    first_day = timezone.datetime(year, month, 1).date()
    last_day = timezone.datetime(year, month, monthrange(year, month)[1]).date()
    
    # Obtener todas las solicitudes aprobadas del mes
    requests = VacationRequest.objects.filter(
        staff__gym=gym,
        status=VacationRequest.Status.APPROVED,
        start_date__lte=last_day,
        end_date__gte=first_day
    ).select_related('staff__user', 'absence_type')
    
    # Obtener periodos bloqueados
    blocked_periods = BlockedVacationPeriod.objects.filter(
        gym=gym,
        start_date__lte=last_day,
        end_date__gte=first_day
    )
    
    # Pendientes de aprobar (para managers)
    pending_count = VacationRequest.objects.filter(
        staff__gym=gym,
        status=VacationRequest.Status.PENDING
    ).count()
    
    context = {
        'title': 'Calendario de Vacaciones',
        'requests': requests,
        'blocked_periods': blocked_periods,
        'pending_count': pending_count,
        'year': year,
        'month': month,
        'month_name': first_day.strftime('%B %Y'),
        'prev_month': (first_day - timedelta(days=1)).replace(day=1),
        'next_month': (last_day + timedelta(days=1)),
    }
    return render(request, 'backoffice/staff/vacation_calendar.html', context)


@login_required
@require_gym_permission("staff.view_vacation")
def vacation_calendar_data(request):
    """API para datos del calendario (JSON para FullCalendar)"""
    gym = request.gym
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    
    try:
        start_date = datetime.strptime(start[:10], '%Y-%m-%d').date()
        end_date = datetime.strptime(end[:10], '%Y-%m-%d').date()
    except (ValueError, IndexError):
        start_date = timezone.now().date().replace(day=1)
        end_date = start_date + timedelta(days=31)
    
    events = []
    
    # Solicitudes aprobadas
    requests = VacationRequest.objects.filter(
        staff__gym=gym,
        status=VacationRequest.Status.APPROVED,
        start_date__lte=end_date,
        end_date__gte=start_date
    ).select_related('staff__user', 'absence_type')
    
    for req in requests:
        staff_name = req.staff.user.get_full_name() or req.staff.user.email
        events.append({
            'id': f'vacation_{req.id}',
            'title': f'{staff_name} - {req.absence_type.name}',
            'start': req.start_date.isoformat(),
            'end': (req.end_date + timedelta(days=1)).isoformat(),  # FullCalendar exclusive end
            'color': req.absence_type.color or '#3788d8',
            'allDay': True,
            'extendedProps': {
                'type': 'vacation',
                'staff_id': req.staff.id,
                'absence_type': req.absence_type.name,
                'days': req.working_days,
            }
        })
    
    # Periodos bloqueados
    blocked = BlockedVacationPeriod.objects.filter(
        gym=gym,
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    
    for block in blocked:
        events.append({
            'id': f'blocked_{block.id}',
            'title': f'🚫 {block.name}',
            'start': block.start_date.isoformat(),
            'end': (block.end_date + timedelta(days=1)).isoformat(),
            'color': '#dc3545',
            'allDay': True,
            'display': 'background',
            'extendedProps': {
                'type': 'blocked',
                'reason': block.reason,
            }
        })
    
    return JsonResponse(events, safe=False)


@login_required
def my_vacations(request):
    """Vista de mis vacaciones (empleado)"""
    user = request.user
    
    # Obtener perfil de staff
    staff = StaffProfile.objects.filter(user=user, is_active=True).first()
    if not staff:
        messages.error(request, "No tienes un perfil de empleado activo.")
        return redirect('vacation_calendar')
    
    gym = staff.gym
    current_year = timezone.now().year
    
    # Obtener o crear balance
    balance, created = StaffVacationBalance.objects.get_or_create(
        staff=staff,
        year=current_year,
        defaults={'days_allocated': 22}  # Valor por defecto
    )
    
    # Aplicar política si existe
    if created:
        policy = VacationPolicy.objects.filter(gym=gym).first()
        if policy:
            balance.days_allocated = policy.calculate_days_for_staff(staff)
            balance.save()
    
    # Mis solicitudes
    my_requests = VacationRequest.objects.filter(
        staff=staff
    ).select_related('absence_type', 'approved_by').order_by('-created_at')
    
    # Solicitudes del año actual
    year_requests = my_requests.filter(start_date__year=current_year)
    
    # Tipos de ausencia disponibles
    absence_types = AbsenceType.objects.filter(
        gym=gym,
        is_active=True
    )
    
    context = {
        'title': 'Mis Vacaciones',
        'staff': staff,
        'balance': balance,
        'my_requests': my_requests[:20],
        'year_requests': year_requests,
        'absence_types': absence_types,
        'current_year': current_year,
    }
    return render(request, 'backoffice/staff/my_vacations.html', context)


@login_required
def vacation_request_create(request):
    """Crear nueva solicitud de vacaciones"""
    user = request.user
    
    staff = StaffProfile.objects.filter(user=user, is_active=True).first()
    if not staff:
        messages.error(request, "No tienes un perfil de empleado activo.")
        return redirect('vacation_calendar')
    
    gym = staff.gym
    
    if request.method == 'POST':
        form = VacationRequestForm(request.POST, gym=gym)
        if form.is_valid():
            vacation = form.save(commit=False)
            vacation.staff = staff
            
            # Calcular días laborables (usa la política del gym internamente)
            vacation.working_days = vacation.calculate_working_days()
            
            # Obtener política para cálculos de balance
            policy = VacationPolicy.objects.filter(gym=gym).first()
            
            # Validar días disponibles si es tipo que afecta balance
            if vacation.absence_type.deducts_from_balance:
                current_year = vacation.start_date.year
                balance, _ = StaffVacationBalance.objects.get_or_create(
                    staff=staff,
                    year=current_year,
                    defaults={'days_allocated': policy.calculate_days_for_staff(staff) if policy else 22}
                )
                
                if vacation.working_days > balance.days_available:
                    messages.error(request, 
                        f"No tienes suficientes días disponibles. Solicitados: {vacation.working_days}, Disponibles: {balance.days_available}")
                    return render(request, 'backoffice/staff/vacation_request_form.html', {
                        'form': form,
                        'title': 'Nueva Solicitud de Vacaciones'
                    })
            
            # Verificar periodo bloqueado
            blocked = BlockedVacationPeriod.objects.filter(
                gym=gym,
                start_date__lte=vacation.end_date,
                end_date__gte=vacation.start_date
            ).first()
            
            if blocked and blocked.affects_role(staff.role):
                messages.error(request, 
                    f"No puedes solicitar vacaciones en este periodo: {blocked.name}")
                return render(request, 'backoffice/staff/vacation_request_form.html', {
                    'form': form,
                    'title': 'Nueva Solicitud de Vacaciones'
                })
            
            # Auto-aprobar si no requiere aprobación
            if not vacation.absence_type.requires_approval:
                vacation.status = VacationRequest.Status.APPROVED
                vacation.approved_at = timezone.now()
            
            vacation.save()
            
            # Actualizar balance pendiente si está pendiente
            if vacation.status == VacationRequest.Status.PENDING and vacation.absence_type.deducts_from_balance:
                balance.days_pending += vacation.working_days
                balance.save()
            
            messages.success(request, "Solicitud creada correctamente.")
            return redirect('my_vacations')
    else:
        form = VacationRequestForm(gym=gym)
    
    context = {
        'title': 'Nueva Solicitud de Vacaciones',
        'form': form,
    }
    return render(request, 'backoffice/staff/vacation_request_form.html', context)


@login_required
def vacation_request_cancel(request, pk):
    """Cancelar solicitud de vacaciones"""
    vacation = get_object_or_404(VacationRequest, pk=pk)
    
    # Verificar que sea el dueño o manager
    if vacation.staff.user != request.user:
        if hasattr(request, 'gym') and vacation.staff.gym != request.gym:
            messages.error(request, "No tienes permiso para cancelar esta solicitud.")
            return redirect('my_vacations')
    
    if request.method == 'POST':
        try:
            vacation.cancel()
            messages.success(request, "Solicitud cancelada correctamente.")
        except ValueError as e:
            messages.error(request, str(e))
    
    return redirect('my_vacations')


@login_required
@require_gym_permission("staff.approve_vacation")
def vacation_pending_list(request):
    """Lista de solicitudes pendientes de aprobar"""
    gym = request.gym
    
    pending = VacationRequest.objects.filter(
        staff__gym=gym,
        status=VacationRequest.Status.PENDING
    ).select_related('staff__user', 'absence_type').order_by('start_date')
    
    context = {
        'title': 'Solicitudes Pendientes',
        'pending_requests': pending,
    }
    return render(request, 'backoffice/staff/vacation_pending.html', context)


@login_required
@require_gym_permission("staff.approve_vacation")
def vacation_request_approve(request, pk):
    """Aprobar solicitud de vacaciones"""
    vacation = get_object_or_404(VacationRequest, pk=pk, staff__gym=request.gym)
    
    if request.method == 'POST':
        try:
            vacation.approve(request.user)
            messages.success(request, f"Solicitud de {vacation.staff.user.get_full_name()} aprobada.")
        except ValueError as e:
            messages.error(request, str(e))
    
    return redirect('vacation_pending_list')


@login_required
@require_gym_permission("staff.approve_vacation")
def vacation_request_reject(request, pk):
    """Rechazar solicitud de vacaciones"""
    vacation = get_object_or_404(VacationRequest, pk=pk, staff__gym=request.gym)
    
    reason = request.POST.get('reason', '')
    
    if request.method == 'POST':
        try:
            vacation.reject(request.user, reason)
            messages.success(request, f"Solicitud de {vacation.staff.user.get_full_name()} rechazada.")
        except ValueError as e:
            messages.error(request, str(e))
    
    return redirect('vacation_pending_list')


@login_required
@require_gym_permission("staff.view_vacation_balance")
def vacation_balances(request):
    """Vista de balances de todos los empleados"""
    gym = request.gym
    current_year = int(request.GET.get('year', timezone.now().year))
    
    # Obtener todos los staff activos
    staff_list = StaffProfile.objects.filter(gym=gym, is_active=True).select_related('user')
    
    # Obtener balances
    balances = []
    for staff in staff_list:
        balance, created = StaffVacationBalance.objects.get_or_create(
            staff=staff,
            year=current_year,
            defaults={'days_allocated': 22}
        )
        balances.append({
            'staff': staff,
            'balance': balance,
        })
    
    context = {
        'title': 'Balances de Vacaciones',
        'balances': balances,
        'current_year': current_year,
        'years': range(current_year - 2, current_year + 2),
    }
    return render(request, 'backoffice/staff/vacation_balances.html', context)


@login_required
@require_gym_permission("staff.change_vacation_balance")
def vacation_balance_adjust(request, pk):
    """Ajustar balance de un empleado"""
    balance = get_object_or_404(StaffVacationBalance, pk=pk, staff__gym=request.gym)
    
    if request.method == 'POST':
        form = BalanceAdjustForm(request.POST, instance=balance)
        if form.is_valid():
            form.save()
            messages.success(request, "Balance actualizado correctamente.")
            return redirect('vacation_balances')
    else:
        form = BalanceAdjustForm(instance=balance)
    
    context = {
        'title': f'Ajustar Balance - {balance.staff.user.get_full_name()}',
        'form': form,
        'balance': balance,
    }
    return render(request, 'backoffice/staff/vacation_balance_adjust.html', context)


@login_required
@require_gym_permission("staff.manage_blocked_periods")
def vacation_settings(request):
    """Configuración de política de vacaciones"""
    gym = request.gym
    
    policy, created = VacationPolicy.objects.get_or_create(
        gym=gym,
        defaults={
            'base_days_per_year': 22,
            'extra_days_per_year_worked': 1,
            'max_seniority_days': 5,
        }
    )
    
    if request.method == 'POST':
        form = VacationPolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, "Política de vacaciones actualizada.")
            return redirect('vacation_settings')
    else:
        form = VacationPolicyForm(instance=policy)
    
    # Tipos de ausencia
    absence_types = AbsenceType.objects.filter(
        gym=gym,
        is_active=True
    )
    
    context = {
        'title': 'Configuración de Vacaciones',
        'form': form,
        'policy': policy,
        'absence_types': absence_types,
    }
    return render(request, 'backoffice/staff/vacation_settings.html', context)


@login_required
@require_gym_permission("staff.manage_blocked_periods")
def blocked_periods_list(request):
    """Lista de periodos bloqueados"""
    gym = request.gym
    
    periods = BlockedVacationPeriod.objects.filter(gym=gym).order_by('-start_date')
    
    context = {
        'title': 'Periodos Bloqueados',
        'periods': periods,
    }
    return render(request, 'backoffice/staff/blocked_periods.html', context)


@login_required
@require_gym_permission("staff.manage_blocked_periods")
def blocked_period_create(request):
    """Crear periodo bloqueado"""
    gym = request.gym
    
    if request.method == 'POST':
        form = BlockedPeriodForm(request.POST)
        if form.is_valid():
            period = form.save(commit=False)
            period.gym = gym
            period.save()
            messages.success(request, "Periodo bloqueado creado.")
            return redirect('blocked_periods_list')
    else:
        form = BlockedPeriodForm()
    
    context = {
        'title': 'Nuevo Periodo Bloqueado',
        'form': form,
    }
    return render(request, 'backoffice/staff/blocked_period_form.html', context)


@login_required
@require_gym_permission("staff.manage_blocked_periods")
def blocked_period_delete(request, pk):
    """Eliminar periodo bloqueado"""
    period = get_object_or_404(BlockedVacationPeriod, pk=pk, gym=request.gym)
    
    if request.method == 'POST':
        period.delete()
        messages.success(request, "Periodo bloqueado eliminado.")
    
    return redirect('blocked_periods_list')


# ==========================================
# SHIFT REPORTS & ALERTS (Informe de Fichajes)
# ==========================================
from datetime import date, datetime, timedelta, time
from .models import StaffExpectedSchedule, MissingCheckinAlert


@login_required
@require_gym_permission("staff.view_shift_report")
def shift_report(request):
    """Vista principal del informe de fichajes con alertas"""
    gym = request.gym
    
    # Filtros
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    staff_id = request.GET.get('staff')
    show_alerts_only = request.GET.get('alerts_only') == '1'
    
    # Fechas por defecto: último mes
    today = timezone.now().date()
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
    else:
        end_date = today
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = end_date - timedelta(days=30)
    else:
        start_date = end_date - timedelta(days=30)
    
    # Staff del gimnasio
    staff_members = StaffProfile.objects.filter(gym=gym, is_active=True).select_related('user')
    
    # Filtro de empleado específico
    if staff_id:
        staff_filter = StaffProfile.objects.filter(pk=staff_id, gym=gym)
    else:
        staff_filter = staff_members
    
    # Obtener fichajes
    shifts = WorkShift.objects.filter(
        staff__in=staff_filter,
        start_time__date__gte=start_date,
        start_time__date__lte=end_date
    ).select_related('staff', 'staff__user').order_by('-start_time')
    
    # Obtener alertas no resueltas
    pending_alerts = MissingCheckinAlert.objects.filter(
        staff__gym=gym,
        is_resolved=False,
        date__gte=start_date,
        date__lte=end_date
    ).select_related('staff', 'staff__user').order_by('-date')
    
    if staff_id:
        pending_alerts = pending_alerts.filter(staff_id=staff_id)
    
    # Calcular estadísticas
    total_shifts = shifts.count()
    total_hours = sum(s.duration_hours for s in shifts if s.end_time)
    avg_hours_per_day = round(total_hours / max(1, (end_date - start_date).days), 2)
    
    # Empleados sin fichar hoy
    staff_without_checkin_today = _get_staff_without_checkin_today(gym)
    
    context = {
        'shifts': shifts[:100],  # Limitar para rendimiento
        'pending_alerts': pending_alerts,
        'staff_without_checkin_today': staff_without_checkin_today,
        'staff_members': staff_members,
        'start_date': start_date,
        'end_date': end_date,
        'selected_staff': staff_id,
        'show_alerts_only': show_alerts_only,
        'stats': {
            'total_shifts': total_shifts,
            'total_hours': round(total_hours, 1),
            'avg_hours_per_day': avg_hours_per_day,
            'pending_alerts_count': pending_alerts.count(),
        }
    }
    
    return render(request, 'backoffice/staff/shift_report.html', context)


def _get_staff_without_checkin_today(gym):
    """Obtiene empleados activos que deberían haber fichado hoy pero no lo han hecho"""
    today = timezone.now().date()
    today_weekday = today.weekday()
    now_time = timezone.now().time()
    
    # Empleados con horario esperado para hoy
    staff_with_schedule_today = StaffExpectedSchedule.objects.filter(
        staff__gym=gym,
        staff__is_active=True,
        day_of_week=today_weekday,
        is_active=True,
        start_time__lte=now_time  # Ya deberían haber fichado
    ).select_related('staff', 'staff__user')
    
    # Filtrar los que NO tienen fichaje hoy
    staff_ids_with_shift_today = WorkShift.objects.filter(
        staff__gym=gym,
        start_time__date=today
    ).values_list('staff_id', flat=True)
    
    return [
        {
            'staff': schedule.staff,
            'expected_time': schedule.start_time,
            'grace_minutes': schedule.grace_minutes,
            'minutes_late': _calculate_minutes_late(schedule.start_time, schedule.grace_minutes)
        }
        for schedule in staff_with_schedule_today
        if schedule.staff_id not in staff_ids_with_shift_today
    ]


def _calculate_minutes_late(expected_time, grace_minutes):
    """Calcula los minutos de retraso"""
    now = timezone.now()
    expected_datetime = datetime.combine(now.date(), expected_time)
    expected_datetime = timezone.make_aware(expected_datetime)
    expected_with_grace = expected_datetime + timedelta(minutes=grace_minutes)
    
    if now > expected_with_grace:
        diff = now - expected_with_grace
        return int(diff.total_seconds() / 60)
    return 0


@login_required
@require_gym_permission("staff.resolve_checkinalert")
def resolve_alert(request, pk):
    """Resolver/justificar una alerta de fichaje"""
    alert = get_object_or_404(MissingCheckinAlert, pk=pk, staff__gym=request.gym)
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        alert.is_resolved = True
        alert.resolution_notes = notes
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.save()
        messages.success(request, 'Alerta resuelta correctamente.')
    
    return redirect('shift_report')


@login_required
@require_gym_permission("staff.export_shift_report")
def shift_export_excel(request):
    """Exporta informe de fichajes a Excel"""
    gym = request.gym
    
    # Filtros
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    staff_id = request.GET.get('staff')
    
    today = timezone.now().date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else today
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else end_date - timedelta(days=30)
    
    # Obtener fichajes
    shifts = WorkShift.objects.filter(
        staff__gym=gym,
        start_time__date__gte=start_date,
        start_time__date__lte=end_date
    ).select_related('staff', 'staff__user').order_by('-start_time')
    
    if staff_id:
        shifts = shifts.filter(staff_id=staff_id)
    
    config = ExportConfig(
        title=f"Informe de Fichajes ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})",
        headers=['Fecha', 'Empleado', 'Entrada', 'Salida', 'Horas', 'Método', 'Estado'],
        data_extractor=lambda s: [
            s.start_time.strftime('%d/%m/%Y'),
            f"{s.staff.user.first_name} {s.staff.user.last_name}",
            s.start_time.strftime('%H:%M'),
            s.end_time.strftime('%H:%M') if s.end_time else '-',
            f"{s.duration_hours}h" if s.end_time else 'En curso',
            s.get_method_display(),
            'Cerrado' if s.end_time else 'Abierto',
        ],
        column_widths=[12, 25, 10, 10, 10, 15, 12]
    )
    
    excel_file = GenericExportService.export_to_excel(shifts, config, gym.name)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"fichajes_{gym.name}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_gym_permission("staff.export_shift_report")
def shift_export_pdf(request):
    """Exporta informe de fichajes a PDF"""
    gym = request.gym
    
    # Filtros
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    staff_id = request.GET.get('staff')
    
    today = timezone.now().date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else today
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else end_date - timedelta(days=30)
    
    # Obtener fichajes
    shifts = WorkShift.objects.filter(
        staff__gym=gym,
        start_time__date__gte=start_date,
        start_time__date__lte=end_date
    ).select_related('staff', 'staff__user').order_by('-start_time')
    
    if staff_id:
        shifts = shifts.filter(staff_id=staff_id)
    
    config = ExportConfig(
        title=f"Informe de Fichajes ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})",
        headers=['Fecha', 'Empleado', 'Entrada', 'Salida', 'Horas', 'Método'],
        data_extractor=lambda s: [
            s.start_time.strftime('%d/%m/%Y'),
            f"{s.staff.user.first_name} {s.staff.user.last_name}",
            s.start_time.strftime('%H:%M'),
            s.end_time.strftime('%H:%M') if s.end_time else '-',
            f"{s.duration_hours}h" if s.end_time else '-',
            s.get_method_display(),
        ],
        column_widths=[12, 25, 10, 10, 10, 15]
    )
    
    pdf_file = GenericExportService.export_to_pdf(shifts, config, gym.name)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    filename = f"fichajes_{gym.name}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_gym_permission("staff.change_expectedschedule")
def staff_schedule_edit(request, pk):
    """Editar horario esperado de un empleado"""
    profile = get_object_or_404(StaffProfile, pk=pk, gym=request.gym)
    
    DAYS_OF_WEEK = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'), 
        (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo')
    ]
    
    if request.method == 'POST':
        # Procesar cada día
        for day_num, day_name in DAYS_OF_WEEK:
            is_active = request.POST.get(f'day_{day_num}_active') == 'on'
            start_time_str = request.POST.get(f'day_{day_num}_start', '')
            end_time_str = request.POST.get(f'day_{day_num}_end', '')
            grace = request.POST.get(f'day_{day_num}_grace', '15')
            
            schedule, created = StaffExpectedSchedule.objects.get_or_create(
                staff=profile,
                day_of_week=day_num,
                defaults={
                    'start_time': time(9, 0),
                    'end_time': time(17, 0),
                    'grace_minutes': 15
                }
            )
            
            if is_active and start_time_str and end_time_str:
                schedule.is_active = True
                schedule.start_time = datetime.strptime(start_time_str, '%H:%M').time()
                schedule.end_time = datetime.strptime(end_time_str, '%H:%M').time()
                schedule.grace_minutes = int(grace) if grace.isdigit() else 15
                schedule.save()
            else:
                schedule.is_active = False
                schedule.save()
        
        messages.success(request, f'Horario de {profile} actualizado correctamente.')
        return redirect('staff_detail', pk=pk)
    
    # Obtener horarios actuales
    schedules = {s.day_of_week: s for s in profile.expected_schedules.all()}
    
    schedule_data = []
    for day_num, day_name in DAYS_OF_WEEK:
        schedule = schedules.get(day_num)
        schedule_data.append({
            'day_num': day_num,
            'day_name': day_name,
            'is_active': schedule.is_active if schedule else False,
            'start_time': schedule.start_time.strftime('%H:%M') if schedule else '09:00',
            'end_time': schedule.end_time.strftime('%H:%M') if schedule else '17:00',
            'grace_minutes': schedule.grace_minutes if schedule else 15,
        })
    
    context = {
        'profile': profile,
        'schedule_data': schedule_data,
    }
    return render(request, 'backoffice/staff/schedule_edit.html', context)


# ==========================================
# EXPORT FUNCTIONS
# ==========================================
from django.http import HttpResponse
from core.export_service import GenericExportService, ExportConfig


@login_required
@require_gym_permission("staff.view_staffprofile")
def staff_export_excel(request):
    """Exporta listado de personal a Excel"""
    gym = request.gym
    staff_members = StaffProfile.objects.filter(gym=gym).select_related('user')
    
    config = ExportConfig(
        title="Listado de Personal",
        headers=['ID', 'Nombre', 'Email', 'Rol', 'PIN', 'Estado', 'Fecha Alta'],
        data_extractor=lambda s: [
            s.id,
            f"{s.user.first_name} {s.user.last_name}",
            s.user.email,
            s.role or 'Sin rol',
            s.pin_code or '-',
            'Activo' if s.is_active else 'Inactivo',
            s.user.date_joined,
        ],
        column_widths=[8, 22, 28, 15, 10, 10, 15]
    )
    
    excel_file = GenericExportService.export_to_excel(staff_members, config, gym.name)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="personal_{gym.name}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
@require_gym_permission("staff.view_staffprofile")
def staff_export_pdf(request):
    """Exporta listado de personal a PDF"""
    gym = request.gym
    staff_members = StaffProfile.objects.filter(gym=gym).select_related('user')
    
    config = ExportConfig(
        title="Listado de Personal",
        headers=['ID', 'Nombre', 'Email', 'Rol', 'Estado', 'Fecha Alta'],
        data_extractor=lambda s: [
            s.id,
            f"{s.user.first_name} {s.user.last_name}",
            s.user.email,
            s.role or 'Sin rol',
            'Activo' if s.is_active else 'Inactivo',
            s.user.date_joined,
        ],
        column_widths=[8, 22, 28, 15, 10, 15]
    )
    
    pdf_file = GenericExportService.export_to_pdf(staff_members, config, gym.name)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="personal_{gym.name}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response

