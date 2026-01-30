from django.urls import path
from . import views, api

urlpatterns = [
        path('api/days/<int:day_id>/update-name/', api.api_update_day_name, name='api_update_day_name'),
    path('exercises/', views.exercise_list, name='exercise_list'),
    path('exercises/add/', views.exercise_create, name='exercise_create'),
    path('exercises/<int:pk>/edit/', views.exercise_update, name='exercise_edit'),
    
    path('routines/', views.routine_list, name='routine_list'),
    path('routines/add/', views.routine_create, name='routine_create'),
    path('routines/<int:routine_id>/builder/', views.routine_detail, name='routine_detail'), # Renamed/Pointed to builder
    
    # API
    path('api/routines/<int:routine_id>/add-day/', api.api_add_day, name='api_add_day'),
    path('api/routines/<int:routine_id>/add-exercise/', api.api_add_exercise, name='api_add_exercise'),
    path('api/routines/<int:routine_id>/update-order/', api.api_update_order, name='api_update_order'),
    path('api/exercises/<int:rx_id>/update/', api.api_update_details, name='api_update_details'),
    path('api/exercises/<int:rx_id>/delete/', api.api_delete_exercise, name='api_delete_exercise'),
    path('api/exercises/<int:rx_id>/duplicate/', api.api_duplicate_exercise, name='api_duplicate_exercise'),
    path('api/days/<int:day_id>/delete/', api.api_delete_day, name='api_delete_day'),
    path('api/days/<int:day_id>/duplicate/', api.api_duplicate_day, name='api_duplicate_day'),
    
    # Client Routine APIs
    path('api/clients/<int:client_id>/assign/', api.api_assign_routine, name='api_assign_routine'),
    path('api/clients/<int:client_id>/create-personal/', api.api_create_personal_routine, name='api_create_personal_routine'),
]
