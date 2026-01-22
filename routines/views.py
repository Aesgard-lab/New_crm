from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import require_gym_permission
from .models import Exercise, WorkoutRoutine

@login_required
@require_gym_permission('routines.view_exercise')
def exercise_list(request):
    exercises = Exercise.objects.filter(gym=request.gym, is_active=True).order_by('name')
    return render(request, 'backoffice/routines/exercise_list.html', {'exercises': exercises})

@login_required
@require_gym_permission('routines.add_exercise')
def exercise_create(request):
    from .forms import ExerciseForm
    if request.method == 'POST':
        form = ExerciseForm(request.POST)
        if form.is_valid():
            form.save(gym=request.gym)
            messages.success(request, 'Ejercicio creado correctamente')
            return redirect('exercise_list')
    else:
        form = ExerciseForm()
        
    return render(request, 'backoffice/routines/exercise_form.html', {
        'form': form
    })

@login_required
@require_gym_permission('routines.change_exercise')
def exercise_update(request, pk):
    from .forms import ExerciseForm
    exercise = get_object_or_404(Exercise, pk=pk, gym=request.gym)
    
    if request.method == 'POST':
        form = ExerciseForm(request.POST, instance=exercise)
        if form.is_valid():
            form.save(gym=request.gym)
            messages.success(request, 'Ejercicio actualizado correctamente')
            return redirect('exercise_list')
    else:
        form = ExerciseForm(instance=exercise)
        
    return render(request, 'backoffice/routines/exercise_form.html', {
        'form': form
    })

@login_required
@require_gym_permission('routines.view_workoutroutine')
def routine_list(request):
    routines = WorkoutRoutine.objects.filter(gym=request.gym, is_template=True).order_by('-created_at')
    return render(request, 'backoffice/routines/routine_list.html', {'routines': routines})

@login_required
@require_gym_permission('routines.add_workoutroutine')
def routine_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        goal = request.POST.get('goal')
        difficulty = request.POST.get('difficulty')
        
        routine = WorkoutRoutine.objects.create(
            gym=request.gym,
            name=name,
            goal=goal,
            difficulty=difficulty,
            is_template=True
        )
        return redirect('routine_detail', routine_id=routine.id) # To Builder
        
    return render(request, 'backoffice/routines/routine_form.html', {
        'goals': WorkoutRoutine.GOALS,
        'difficulties': WorkoutRoutine.DIFFICULTY
    })

@login_required
def routine_detail(request, routine_id):
    routine = get_object_or_404(WorkoutRoutine, id=routine_id, gym=request.gym)
    exercises = Exercise.objects.filter(gym=request.gym, is_active=True).prefetch_related('tags')
    
    # Simple serialization for initial state if needed, but we render in template
    return render(request, 'backoffice/routines/builder.html', {
        'routine': routine,
        'exercises': exercises,
        'muscle_groups': Exercise.MUSCLE_GROUPS
    })
