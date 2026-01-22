from django.urls import path
from . import views

app_name = 'lockers'

urlpatterns = [
    # Dashboard
    path('', views.locker_dashboard, name='dashboard'),
    
    # Zonas
    path('zones/', views.zone_list, name='zone_list'),
    path('zones/new/', views.zone_create, name='zone_create'),
    path('zones/<int:zone_id>/', views.zone_detail, name='zone_detail'),
    path('zones/<int:zone_id>/edit/', views.zone_edit, name='zone_edit'),
    path('zones/<int:zone_id>/delete/', views.zone_delete, name='zone_delete'),
    
    # Taquillas
    path('zones/<int:zone_id>/lockers/new/', views.locker_create, name='locker_create'),
    path('lockers/<int:locker_id>/edit/', views.locker_edit, name='locker_edit'),
    path('lockers/<int:locker_id>/delete/', views.locker_delete, name='locker_delete'),
    
    # Asignaciones
    path('assignments/', views.assignment_list, name='assignment_list'),
    path('lockers/<int:locker_id>/assign/', views.assign_locker, name='assign'),
    path('assignments/<int:assignment_id>/release/', views.release_locker, name='release'),
    path('client/<int:client_id>/assign/', views.assign_locker_to_client, name='assign_to_client'),
    
    # API
    path('api/locker/<int:locker_id>/status/', views.api_locker_status, name='api_locker_status'),
    path('api/clients/search/', views.api_search_clients, name='api_search_clients'),
    path('api/lockers/available/', views.api_available_lockers, name='api_available_lockers'),
]
