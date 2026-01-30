from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
import json
from .models import WorkoutRoutine, RoutineDay, RoutineExercise, Exercise, ClientRoutine
from clients.models import Client
from django.db import transaction

@login_required
@require_http_methods(["PATCH"])
def api_update_day_name(request, day_id):
    """Updates the name of a RoutineDay"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'status': 'error', 'message': 'El nombre no puede estar vacío.'}, status=400)
        day = get_object_or_404(RoutineDay, id=day_id, routine__gym=request.gym)
        day.name = name
        day.save()
        return JsonResponse({'status': 'success', 'name': day.name})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
from django.shortcuts import get_object_or_404
from .models import WorkoutRoutine, RoutineDay, RoutineExercise, Exercise
import json

from .models import WorkoutRoutine, RoutineDay, RoutineExercise, Exercise, ClientRoutine
from clients.models import Client
from django.db import transaction

@login_required
@require_POST
def api_assign_routine(request, client_id):
    """Clones a template routine and assigns it to a client"""
    try:
        data = json.loads(request.body)
        template_id = data.get('template_id')
        
        client = get_object_or_404(Client, id=client_id, gym=request.gym)
        template = get_object_or_404(WorkoutRoutine, id=template_id, gym=request.gym, is_template=True)
        
        with transaction.atomic():
            # Clone Routine
            new_routine = WorkoutRoutine.objects.create(
                gym=request.gym,
                name=f"{template.name} - {client.first_name}",
                description=template.description,
                goal=template.goal,
                difficulty=template.difficulty,
                is_template=False
            )
            
            # Clone Days & Exercises
            for day in template.days.all():
                new_day = RoutineDay.objects.create(
                    routine=new_routine,
                    name=day.name,
                    order=day.order
                )
                for rx in day.exercises.all():
                    RoutineExercise.objects.create(
                        day=new_day,
                        exercise=rx.exercise,
                        order=rx.order,
                        sets=rx.sets,
                        reps=rx.reps,
                        rest=rx.rest,
                        notes=rx.notes
                    )
            
            # Create Assignment
            ClientRoutine.objects.create(
                client=client,
                routine=new_routine,
                is_active=True
            )
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def api_create_personal_routine(request, client_id):
    """Creates a blank routine for a client"""
    try:
        client = get_object_or_404(Client, id=client_id, gym=request.gym)
        
        with transaction.atomic():
            new_routine = WorkoutRoutine.objects.create(
                gym=request.gym,
                name=f"Rutina Personal - {client.first_name}",
                is_template=False
            )
            
            # Default Day 1
            RoutineDay.objects.create(routine=new_routine, name="Día 1", order=1)
            
            ClientRoutine.objects.create(
                client=client,
                routine=new_routine,
                is_active=True
            )
            
        return JsonResponse({
            'status': 'success', 
            'routine_id': new_routine.id 
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def api_add_exercise(request, routine_id):
    """Adds an exercise to a specific day in the routine"""
    routine = get_object_or_404(WorkoutRoutine, id=routine_id, gym=request.gym)
    
    try:
        data = json.loads(request.body)
        day_id = data.get('day_id')
        exercise_id = data.get('exercise_id')
        
        # Get or create day if not exists (though UI should provide valid day_id)
        if day_id == 'new':
            last_day = routine.days.last()
            order = last_day.order + 1 if last_day else 1
            day = RoutineDay.objects.create(routine=routine, name=f"Día {order}", order=order)
        else:
            day = get_object_or_404(RoutineDay, id=day_id, routine=routine)
            
        exercise = get_object_or_404(Exercise, id=exercise_id)
        
        # Create RoutineExercise
        last_ex = day.exercises.last()
        order = last_ex.order + 1 if last_ex else 1
        
        routine_exercise = RoutineExercise.objects.create(
            day=day, 
            exercise=exercise,
            order=order
        )
        
        return JsonResponse({
            'status': 'success', 
            'id': routine_exercise.id,
            'name': exercise.name,
            'video': exercise.video_url,
            'muscle_group': exercise.muscle_group,
            'order': order
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def api_update_order(request, routine_id):
    """Updates the order of exercises within a day or moves between days"""
    try:
        data = json.loads(request.body)
        day_id = data.get('day_id')
        ordered_ids = data.get('ordered_ids', []) # List of RoutineExercise IDs in new order
        
        day = get_object_or_404(RoutineDay, id=day_id, routine__id=routine_id)
        
        # Iterate and update order/day
        for index, text_id in enumerate(ordered_ids):
            rx_id = int(text_id)
            RoutineExercise.objects.filter(id=rx_id).update(day=day, order=index+1)
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def api_update_details(request, rx_id):
    """Updates sets, reps, rest, notes for a routine exercise"""
    try:
        data = json.loads(request.body)
        rx = get_object_or_404(RoutineExercise, id=rx_id, day__routine__gym=request.gym)
        
        if 'sets' in data: rx.sets = data['sets']
        if 'reps' in data: rx.reps = data['reps']
        if 'rest' in data: rx.rest = data['rest']
        if 'notes' in data: rx.notes = data['notes']
        
        rx.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def api_delete_exercise(request, rx_id):
    try:
        rx = get_object_or_404(RoutineExercise, id=rx_id, day__routine__gym=request.gym)
        rx.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def api_add_day(request, routine_id):
    routine = get_object_or_404(WorkoutRoutine, id=routine_id, gym=request.gym)
    last_day = routine.days.last()
    order = last_day.order + 1 if last_day else 1
    new_day = RoutineDay.objects.create(routine=routine, name=f"Día {order}", order=order)
    
    return JsonResponse({
        'status': 'success',
        'day_id': new_day.id,
        'name': new_day.name
    })

@login_required
@require_POST
def api_delete_day(request, day_id):
    day = get_object_or_404(RoutineDay, id=day_id, routine__gym=request.gym)
    day.delete()
    return JsonResponse({'status': 'success'})
@login_required
@require_POST
def api_duplicate_day(request, day_id):
    """Duplicates a day with all its exercises"""
    try:
        original_day = get_object_or_404(RoutineDay, id=day_id, routine__gym=request.gym)
        
        with transaction.atomic():
            # Calculate new order
            last_day = original_day.routine.days.last()
            new_order = last_day.order + 1 if last_day else 1
            
            # Create new day
            new_day = RoutineDay.objects.create(
                routine=original_day.routine,
                name=f"{original_day.name} (Copia)",
                order=new_order
            )
            
            # Copy all exercises
            for rx in original_day.exercises.all():
                RoutineExercise.objects.create(
                    day=new_day,
                    exercise=rx.exercise,
                    order=rx.order,
                    sets=rx.sets,
                    reps=rx.reps,
                    rest=rx.rest,
                    notes=rx.notes
                )
            
        return JsonResponse({
            'status': 'success',
            'day_id': new_day.id,
            'name': new_day.name
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def api_duplicate_exercise(request, rx_id):
    """Duplicates a routine exercise in the same day"""
    try:
        original_rx = get_object_or_404(RoutineExercise, id=rx_id, day__routine__gym=request.gym)
        
        # Get last order in day
        last_rx = original_rx.day.exercises.last()
        new_order = last_rx.order + 1 if last_rx else 1
        
        # Create duplicate
        new_rx = RoutineExercise.objects.create(
            day=original_rx.day,
            exercise=original_rx.exercise,
            order=new_order,
            sets=original_rx.sets,
            reps=original_rx.reps,
            rest=original_rx.rest,
            notes=original_rx.notes
        )
        
        return JsonResponse({
            'status': 'success',
            'rx_id': new_rx.id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)