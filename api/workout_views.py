"""
API Views for Workout Tracking (Mobile App).
Allows clients to log their workouts, sets, and track progress.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum
import json

from clients.models import Client
from routines.models import (
    ClientRoutine, RoutineDay, RoutineExercise, 
    WorkoutLog, ExerciseLog
)


def get_client_from_user(user):
    """Helper para obtener cliente desde el usuario"""
    try:
        return Client.objects.select_related('gym').get(user=user)
    except Client.DoesNotExist:
        return None


class StartWorkoutView(views.APIView):
    """
    POST: Iniciar un nuevo entrenamiento basado en un día de rutina.
    
    Body: {
        "day_id": 123
    }
    
    Returns the workout_id to use for tracking.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        day_id = request.data.get('day_id')
        if not day_id:
            return Response({'error': 'day_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            day = RoutineDay.objects.select_related('routine').get(id=day_id)
        except RoutineDay.DoesNotExist:
            return Response({'error': 'Día no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar que el cliente tiene esta rutina asignada
        if not ClientRoutine.objects.filter(
            client=client,
            routine=day.routine,
            is_active=True
        ).exists():
            return Response(
                {'error': 'No tienes acceso a esta rutina'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Crear workout log
        workout = WorkoutLog.objects.create(
            client=client,
            routine=day.routine,
            routine_day=day
        )
        
        # Pre-crear ExerciseLogs para cada ejercicio del día
        exercises_data = []
        for re in day.exercises.all().select_related('exercise').order_by('order'):
            exercise_log = ExerciseLog.objects.create(
                workout_log=workout,
                exercise=re.exercise,
                routine_exercise=re,
                sets_data=[]
            )
            exercises_data.append({
                'exercise_log_id': exercise_log.id,
                'exercise_id': re.exercise.id,
                'exercise_name': re.exercise.name,
                'target_sets': re.sets,
                'target_reps': re.reps,
                'rest_time': re.rest,
                'notes': re.notes,
                'order': re.order,
                'sets_completed': 0,
                'completed': False,
            })
        
        return Response({
            'success': True,
            'workout_id': workout.id,
            'routine_name': day.routine.name,
            'day_name': day.name,
            'started_at': workout.date.isoformat(),
            'exercises': exercises_data,
        })


class WorkoutStatusView(views.APIView):
    """
    GET: Obtener el estado actual de un entrenamiento en curso.
    URL: /api/workout/<workout_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, workout_id):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            workout = WorkoutLog.objects.select_related(
                'routine', 'routine_day'
            ).get(id=workout_id, client=client)
        except WorkoutLog.DoesNotExist:
            return Response({'error': 'Entrenamiento no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # Obtener logs de ejercicios
        exercise_logs = workout.exercise_logs.all().select_related(
            'exercise', 'routine_exercise'
        ).order_by('routine_exercise__order')
        
        exercises_data = []
        for log in exercise_logs:
            sets_data = log.sets_data or []
            exercises_data.append({
                'exercise_log_id': log.id,
                'exercise_id': log.exercise.id,
                'exercise_name': log.exercise.name,
                'target_sets': log.routine_exercise.sets if log.routine_exercise else None,
                'target_reps': log.routine_exercise.reps if log.routine_exercise else None,
                'rest_time': log.routine_exercise.rest if log.routine_exercise else None,
                'notes': log.routine_exercise.notes if log.routine_exercise else None,
                'sets_completed': len(sets_data),
                'sets_data': sets_data,
                'completed': log.completed,
            })
        
        # Calcular tiempo transcurrido
        started = timezone.make_aware(
            timezone.datetime.combine(workout.date, timezone.datetime.min.time())
        )
        duration_minutes = int((timezone.now() - started).total_seconds() / 60)
        
        return Response({
            'workout_id': workout.id,
            'routine_name': workout.routine.name if workout.routine else None,
            'day_name': workout.routine_day.name if workout.routine_day else None,
            'date': workout.date.isoformat(),
            'duration_minutes': duration_minutes,
            'completed': workout.completed,
            'difficulty_rating': workout.difficulty_rating,
            'exercises': exercises_data,
        })


class LogSetView(views.APIView):
    """
    POST: Registrar una serie de un ejercicio.
    URL: /api/workout/<workout_id>/log/<exercise_log_id>/set/
    
    Body: {
        "reps": 12,
        "weight": 50.0
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, workout_id, exercise_log_id):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        # Verificar workout pertenece al cliente
        try:
            workout = WorkoutLog.objects.get(id=workout_id, client=client, completed=False)
        except WorkoutLog.DoesNotExist:
            return Response(
                {'error': 'Entrenamiento no encontrado o ya completado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener exercise log
        try:
            exercise_log = ExerciseLog.objects.get(id=exercise_log_id, workout_log=workout)
        except ExerciseLog.DoesNotExist:
            return Response({'error': 'Ejercicio no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        reps = request.data.get('reps', 0)
        weight = request.data.get('weight', 0)
        
        # Añadir set
        sets_data = exercise_log.sets_data or []
        sets_data.append({
            'reps': int(reps),
            'weight': float(weight),
            'timestamp': timezone.now().isoformat(),
        })
        exercise_log.sets_data = sets_data
        exercise_log.save()
        
        return Response({
            'success': True,
            'set_number': len(sets_data),
            'reps': reps,
            'weight': weight,
            'total_sets': len(sets_data),
        })


class CompleteExerciseView(views.APIView):
    """
    POST: Marcar un ejercicio como completado.
    URL: /api/workout/<workout_id>/log/<exercise_log_id>/complete/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, workout_id, exercise_log_id):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            workout = WorkoutLog.objects.get(id=workout_id, client=client, completed=False)
        except WorkoutLog.DoesNotExist:
            return Response(
                {'error': 'Entrenamiento no encontrado o ya completado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            exercise_log = ExerciseLog.objects.get(id=exercise_log_id, workout_log=workout)
        except ExerciseLog.DoesNotExist:
            return Response({'error': 'Ejercicio no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        exercise_log.completed = True
        exercise_log.save()
        
        # Contar ejercicios completados
        total = workout.exercise_logs.count()
        completed = workout.exercise_logs.filter(completed=True).count()
        
        return Response({
            'success': True,
            'exercise_completed': True,
            'exercises_completed': completed,
            'exercises_total': total,
            'all_completed': completed == total,
        })


class FinishWorkoutView(views.APIView):
    """
    POST: Finalizar un entrenamiento.
    URL: /api/workout/<workout_id>/finish/
    
    Body: {
        "difficulty_rating": 7,  # 1-10
        "notes": "Buen entrenamiento"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, workout_id):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            workout = WorkoutLog.objects.get(id=workout_id, client=client, completed=False)
        except WorkoutLog.DoesNotExist:
            return Response(
                {'error': 'Entrenamiento no encontrado o ya completado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calcular estadísticas
        total_sets = 0
        total_reps = 0
        total_volume = 0.0
        
        for log in workout.exercise_logs.all():
            sets_data = log.sets_data or []
            for s in sets_data:
                total_sets += 1
                reps = s.get('reps', 0)
                weight = s.get('weight', 0)
                total_reps += reps
                total_volume += reps * weight
        
        # Calcular duración
        started = timezone.make_aware(
            timezone.datetime.combine(workout.date, timezone.datetime.min.time())
        )
        duration_minutes = int((timezone.now() - started).total_seconds() / 60)
        
        # Actualizar workout
        workout.completed = True
        workout.duration_minutes = duration_minutes
        workout.total_sets = total_sets
        workout.total_reps = total_reps
        workout.total_volume = total_volume
        workout.difficulty_rating = request.data.get('difficulty_rating')
        workout.notes = request.data.get('notes', '')
        workout.save()
        
        return Response({
            'success': True,
            'workout_id': workout.id,
            'summary': {
                'duration_minutes': duration_minutes,
                'total_sets': total_sets,
                'total_reps': total_reps,
                'total_volume': total_volume,
                'difficulty_rating': workout.difficulty_rating,
            }
        })


class WorkoutHistoryView(views.APIView):
    """
    GET: Obtener historial de entrenamientos del cliente.
    URL: /api/workout/history/
    
    Query params:
    - limit: número de resultados (default 20)
    - offset: para paginación
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        workouts = WorkoutLog.objects.filter(
            client=client,
            completed=True
        ).select_related('routine', 'routine_day').order_by('-date')[offset:offset+limit]
        
        # Estadísticas generales
        stats = WorkoutLog.objects.filter(client=client, completed=True).aggregate(
            total_workouts=Sum('id'),
            total_volume=Sum('total_volume'),
            total_sets=Sum('total_sets'),
        )
        
        total_workouts = WorkoutLog.objects.filter(client=client, completed=True).count()
        
        # Últimos 30 días
        from datetime import timedelta
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        last_30_days = WorkoutLog.objects.filter(
            client=client,
            completed=True,
            date__gte=thirty_days_ago
        ).count()
        
        workouts_data = []
        for w in workouts:
            workouts_data.append({
                'id': w.id,
                'date': w.date.isoformat(),
                'routine_name': w.routine.name if w.routine else None,
                'day_name': w.routine_day.name if w.routine_day else None,
                'duration_minutes': w.duration_minutes,
                'total_sets': w.total_sets,
                'total_volume': float(w.total_volume) if w.total_volume else 0,
                'difficulty_rating': w.difficulty_rating,
            })
        
        return Response({
            'stats': {
                'total_workouts': total_workouts,
                'last_30_days': last_30_days,
                'total_volume': float(stats['total_volume'] or 0),
            },
            'workouts': workouts_data,
            'has_more': len(workouts_data) == limit,
        })


class ActiveWorkoutView(views.APIView):
    """
    GET: Verificar si hay un entrenamiento en curso sin terminar.
    Útil para resumir un entrenamiento después de cerrar la app.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = get_client_from_user(request.user)
        if not client:
            return Response({'error': 'No es un cliente'}, status=status.HTTP_403_FORBIDDEN)
        
        # Buscar entrenamientos de hoy no completados
        today = timezone.now().date()
        active_workout = WorkoutLog.objects.filter(
            client=client,
            date=today,
            completed=False
        ).select_related('routine', 'routine_day').first()
        
        if not active_workout:
            return Response({
                'has_active_workout': False,
            })
        
        return Response({
            'has_active_workout': True,
            'workout_id': active_workout.id,
            'routine_name': active_workout.routine.name if active_workout.routine else None,
            'day_name': active_workout.routine_day.name if active_workout.routine_day else None,
        })
