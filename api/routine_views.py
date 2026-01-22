"""
API Views for Client Routines (Mobile App).
Allows clients to view their assigned workout routines and exercises.
"""
from rest_framework import views, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from clients.models import Client
from routines.models import ClientRoutine, WorkoutRoutine, RoutineDay, RoutineExercise, Exercise


class ClientRoutinesListView(generics.ListAPIView):
    """
    Get list of routines assigned to the authenticated client.
    Returns active routines with basic info.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get client
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get client's active routines
        assignments = ClientRoutine.objects.filter(
            client=client,
            is_active=True
        ).select_related('routine').order_by('-start_date')
        
        routines_data = []
        for assignment in assignments:
            routine = assignment.routine
            # Count total exercises across all days
            total_exercises = RoutineExercise.objects.filter(
                day__routine=routine
            ).count()
            
            routines_data.append({
                'id': routine.id,
                'assignment_id': assignment.id,
                'name': routine.name,
                'description': routine.description,
                'goal': routine.goal,
                'goal_display': dict(WorkoutRoutine.GOALS).get(routine.goal, routine.goal),
                'difficulty': routine.difficulty,
                'difficulty_display': dict(WorkoutRoutine.DIFFICULTY).get(routine.difficulty, routine.difficulty),
                'days_count': routine.days.count(),
                'exercises_count': total_exercises,
                'start_date': assignment.start_date.isoformat() if assignment.start_date else None,
                'end_date': assignment.end_date.isoformat() if assignment.end_date else None,
            })
        
        return Response({
            'count': len(routines_data),
            'routines': routines_data
        })


class RoutineDetailView(views.APIView):
    """
    Get detailed view of a routine with all days and exercises.
    URL: /api/routines/<routine_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, routine_id):
        # Get client
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify client has access to this routine
        try:
            assignment = ClientRoutine.objects.get(
                client=client,
                routine_id=routine_id,
                is_active=True
            )
        except ClientRoutine.DoesNotExist:
            return Response(
                {'error': 'Rutina no encontrada o no tienes acceso'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        routine = assignment.routine
        
        # Build days with exercises
        days_data = []
        for day in routine.days.all().order_by('order'):
            exercises_data = []
            for rx in day.exercises.all().order_by('order'):
                exercise = rx.exercise
                exercises_data.append({
                    'id': rx.id,
                    'exercise_id': exercise.id,
                    'name': exercise.name,
                    'description': exercise.description,
                    'muscle_group': exercise.muscle_group,
                    'muscle_group_display': dict(Exercise.MUSCLE_GROUPS).get(exercise.muscle_group, exercise.muscle_group),
                    'video_url': exercise.video_url or None,
                    'sets': rx.sets,
                    'reps': rx.reps,
                    'rest': rx.rest,
                    'notes': rx.notes,
                    'order': rx.order,
                })
            
            days_data.append({
                'id': day.id,
                'name': day.name,
                'order': day.order,
                'exercises_count': len(exercises_data),
                'exercises': exercises_data,
            })
        
        return Response({
            'id': routine.id,
            'name': routine.name,
            'description': routine.description,
            'goal': routine.goal,
            'goal_display': dict(WorkoutRoutine.GOALS).get(routine.goal, routine.goal),
            'difficulty': routine.difficulty,
            'difficulty_display': dict(WorkoutRoutine.DIFFICULTY).get(routine.difficulty, routine.difficulty),
            'assignment': {
                'id': assignment.id,
                'start_date': assignment.start_date.isoformat() if assignment.start_date else None,
                'end_date': assignment.end_date.isoformat() if assignment.end_date else None,
            },
            'days_count': len(days_data),
            'days': days_data,
        })


class ExerciseDetailView(views.APIView):
    """
    Get detailed info for a single exercise.
    URL: /api/exercises/<exercise_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, exercise_id):
        # Get client to verify they belong to a gym
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get exercise (verify it belongs to client's gym)
        try:
            exercise = Exercise.objects.get(
                id=exercise_id,
                gym=client.gym
            )
        except Exercise.DoesNotExist:
            return Response(
                {'error': 'Ejercicio no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get tags as list
        tags = list(exercise.tags.values_list('name', flat=True))
        
        return Response({
            'id': exercise.id,
            'name': exercise.name,
            'description': exercise.description,
            'muscle_group': exercise.muscle_group,
            'muscle_group_display': dict(Exercise.MUSCLE_GROUPS).get(exercise.muscle_group, exercise.muscle_group),
            'video_url': exercise.video_url or None,
            'tags': tags,
        })
