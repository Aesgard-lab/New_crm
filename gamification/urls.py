from django.urls import path
from . import views

app_name = 'gamification'

urlpatterns = [
    # Vistas de gestión
    path('<int:gym_id>/settings/', views.gamification_settings_view, name='settings'),
    path('<int:gym_id>/leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('<int:gym_id>/achievements/', views.achievements_view, name='achievements'),
    path('<int:gym_id>/challenges/', views.challenges_view, name='challenges'),
    path('<int:gym_id>/client/<int:client_id>/', views.client_progress_view, name='client_progress'),
    
    # API endpoints para app móvil
    path('<int:gym_id>/api/my-progress/', views.api_my_progress, name='api_my_progress'),
    path('<int:gym_id>/api/my-achievements/', views.api_my_achievements, name='api_my_achievements'),
    path('<int:gym_id>/api/leaderboard/', views.api_leaderboard, name='api_leaderboard'),
]
