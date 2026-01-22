"""
URLs del Portal Público
"""

from django.urls import path
from . import views

urlpatterns = [
    # Landing page del gym
    path('gym/<slug:slug>/', views.public_gym_home, name='public_gym_home'),
    
    # Módulos principales
    path('gym/<slug:slug>/schedule/', views.public_schedule, name='public_schedule'),
    path('gym/<slug:slug>/pricing/', views.public_pricing, name='public_pricing'),
    path('gym/<slug:slug>/services/', views.public_services, name='public_services'),
    path('gym/<slug:slug>/shop/', views.public_shop, name='public_shop'),
    
    # Compra de planes
    path('gym/<slug:slug>/pricing/purchase/<int:plan_id>/', views.public_plan_purchase, name='public_plan_purchase'),
    path('gym/<slug:slug>/purchase/success/<int:membership_id>/', views.public_purchase_success, name='public_purchase_success'),
    
    # Dashboard del cliente
    path('gym/<slug:slug>/dashboard/', views.public_client_dashboard, name='public_client_dashboard'),
    
    # Gamificación
    path('gym/<slug:slug>/leaderboard/', views.public_leaderboard, name='public_leaderboard'),
    path('gym/<slug:slug>/achievements/', views.public_achievements, name='public_achievements'),
    
    # API para calendario
    path('gym/<slug:slug>/api/schedule/events/', views.api_public_schedule_events, name='api_public_schedule_events'),
    
    # API para reservas
    path('gym/<slug:slug>/api/bookings/book/', views.api_book_session, name='api_book_session'),
    path('gym/<slug:slug>/api/bookings/<int:booking_id>/cancel/', views.api_cancel_booking, name='api_cancel_booking'),
    
    # Autenticación de clientes
    path('gym/<slug:slug>/login/', views.public_login, name='public_login'),
    path('gym/<slug:slug>/logout/', views.public_logout, name='public_logout'),
    path('gym/<slug:slug>/register/', views.public_register, name='public_register'),
]
