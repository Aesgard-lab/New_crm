from django.urls import path
from .views_franchise import FranchiseDashboardView
from . import views
from . import views_holidays
from . import views_goals

urlpatterns = [
    path('franchise/dashboard/', FranchiseDashboardView.as_view(), name='franchise-dashboard'),
    
    # Widget embebible
    path('widget-code/', views.widget_code_generator, name='widget_code'),
    
    # Horarios y festivos
    path('horarios/', views_holidays.gym_opening_hours, name='gym_opening_hours'),
    path('festivos/', views_holidays.gym_holidays_list, name='gym_holidays_list'),
    path('festivos/crear/', views_holidays.gym_holiday_create, name='gym_holiday_create'),
    path('festivos/<int:holiday_id>/editar/', views_holidays.gym_holiday_edit, name='gym_holiday_edit'),
    path('festivos/<int:holiday_id>/eliminar/', views_holidays.gym_holiday_delete, name='gym_holiday_delete'),
    
    # Objetivos
    path('objetivos/', views_goals.gym_goals_list, name='gym_goals_list'),
    path('objetivos/crear/', views_goals.gym_goal_create, name='gym_goal_create'),
    path('objetivos/<int:goal_id>/editar/', views_goals.gym_goal_edit, name='gym_goal_edit'),
    path('objetivos/<int:goal_id>/eliminar/', views_goals.gym_goal_delete, name='gym_goal_delete'),
    path('objetivos/<int:goal_id>/progreso/', views_goals.gym_goal_progress_api, name='gym_goal_progress_api'),
]
