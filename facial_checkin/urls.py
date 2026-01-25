"""
URLs para el módulo de reconocimiento facial.
"""
from django.urls import path
from . import api, views

app_name = 'facial_checkin'

urlpatterns = [
    # API endpoints
    path('api/status/', api.face_recognition_status, name='api_status'),
    path('api/register/', api.register_face, name='api_register'),
    path('api/verify/', api.verify_face, name='api_verify'),
    path('api/delete/', api.delete_face_data, name='api_delete'),
    path('api/stats/', api.face_recognition_stats, name='api_stats'),
    
    # Kiosko
    path('api/kiosk/<int:gym_id>/verify/', api.kiosk_verify, name='kiosk_verify'),
    
    # Vistas web
    path('settings/', views.face_settings_view, name='settings'),
    path('register/', views.client_register_face, name='client_register'),
    path('kiosk/', views.kiosk_view, name='kiosk'),
]
