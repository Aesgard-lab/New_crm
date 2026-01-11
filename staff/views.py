from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import StaffProfile, WorkShift

def staff_kiosk(request):
    """Renderiza la interfaz del Kiosco (Tablet)"""
    return render(request, "staff/kiosk.html")

@require_POST
def staff_checkin(request):
    """Procesa el fichaje por PIN"""
    pin = request.POST.get("pin")
    
    if not pin:
        return JsonResponse({"status": "error", "message": "Introduce un PIN"}, status=400)

    # Buscar empleado por PIN (y que esté activo)
    # TODO: Filtrar por Gym actual si la tablet está asignada a ubicación
    staff = StaffProfile.objects.filter(pin_code=pin, is_active=True).first()
    
    if not staff:
        return JsonResponse({"status": "error", "message": "PIN incorrecto o usuario no encontrado"}, status=404)

    # Buscar si tiene turno abierto
    open_shift = WorkShift.objects.filter(staff=staff, end_time__isnull=True).first()
    
    if open_shift:
        # Cerrar turno
        open_shift.end_time = timezone.now()
        open_shift.save()
        
        # Calcular duración
        duration = open_shift.duration_hours
        msg = f"Adiós {staff.user.first_name}. Turno cerrado ({duration}h)."
        return JsonResponse({"status": "success", "action": "checkout", "message": msg, "staff_name": staff.user.first_name})
    else:
        # Abrir turno
        WorkShift.objects.create(
            staff=staff,
            start_time=timezone.now(),
            method=WorkShift.Method.TABLET
        )
        msg = f"Hola {staff.user.first_name}. Turno iniciado."
        return JsonResponse({"status": "success", "action": "checkin", "message": msg, "staff_name": staff.user.first_name})

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
            return redirect("staff_list")
    else:
        user_form = StaffUserForm(instance=user)
        profile_form = StaffProfileForm(instance=profile)

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
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
    from django.db.models import Sum
    commissions_this_month = StaffCommission.objects.filter(staff=profile, date__gte=month_start).aggregate(total=Sum('amount'))['total'] or 0
    
    # Datos recientes
    recent_shifts = profile.shifts.order_by('-start_time')[:5]
    recent_tasks = profile.assigned_tasks.order_by('-created_at')[:5]
    
    is_clocked_in = profile.shifts.filter(end_time__isnull=True).exists()

    from .models import SalaryConfig
    salary_config, _ = SalaryConfig.objects.get_or_create(staff=profile)
    from .forms import StaffSalaryForm, StaffTaskForm
    
    context = {
        "profile": profile,
        "total_hours": round(total_hours, 1),
        "total_commissions": commissions_this_month,
        "recent_shifts": recent_shifts,
        "recent_tasks": recent_tasks,
        "is_clocked_in": is_clocked_in,
        "salary_form": StaffSalaryForm(instance=salary_config),
        "task_form": StaffTaskForm(),
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
            task.assigned_by = request.user
            task.save()
            return redirect("staff_detail", pk=pk)
            
    return redirect("staff_detail", pk=pk)
