from django.urls import path
from . import views

app_name = 'access_control'

urlpatterns = [
    # Dashboard y listados
    path('', views.access_dashboard, name='dashboard'),
    path('logs/', views.access_log_list, name='log_list'),
    path('devices/', views.device_list, name='device_list'),
    path('devices/new/', views.device_create, name='device_create'),
    path('devices/<int:device_id>/', views.device_detail, name='device_detail'),
    path('devices/<int:device_id>/edit/', views.device_edit, name='device_edit'),
    path('zones/', views.zone_list, name='zone_list'),
    path('zones/new/', views.zone_create, name='zone_create'),
    path('zones/<int:zone_id>/edit/', views.zone_edit, name='zone_edit'),
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
    
    # Historial de cliente (para embeber en ficha)
    path('client/<int:client_id>/history/', views.client_access_history, name='client_history'),
    
    # API para frontend (AJAX)
    path('api/live-feed/', views.api_live_access_feed, name='api_live_feed'),
    path('api/manual-access/', views.api_manual_access, name='api_manual_access'),
    path('api/device/bulk/', views.api_device_bulk, name='api_device_bulk'),
]

# URLs para la API de hardware (se añaden a api/urls.py separadamente)
api_urlpatterns = [
    path('access/validate/', views.api_validate_access, name='api_access_validate'),
    path('access/validate-qr/', views.api_validate_qr, name='api_access_validate_qr'),
    path('access/heartbeat/', views.api_device_heartbeat, name='api_access_heartbeat'),
    path('access/occupancy/', views.api_get_occupancy, name='api_access_occupancy'),
]
