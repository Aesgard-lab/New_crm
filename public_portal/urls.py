"""
URLs del Portal Público
"""

from django.urls import path
from . import views

urlpatterns = [
    # Página de búsqueda de gimnasios (landing principal)
    path('', views.gym_search_landing, name='gym_search_landing'),
    
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
    
    # Perfil del cliente (estilo app)
    path('gym/<slug:slug>/profile/', views.public_client_profile, name='public_client_profile'),
    path('gym/<slug:slug>/profile/attendance/', views.public_attendance_history, name='public_attendance_history'),
    path('gym/<slug:slug>/profile/payments/', views.public_payment_history, name='public_payment_history'),
    path('gym/<slug:slug>/profile/payment-methods/', views.public_payment_methods, name='public_payment_methods'),
    path('gym/<slug:slug>/profile/orders/', views.public_orders_history, name='public_orders_history'),
    path('gym/<slug:slug>/profile/memberships/', views.public_my_memberships, name='public_my_memberships'),
    
    # Adelantar cobro y pago de membresía pendiente
    path('gym/<slug:slug>/advance-payment/', views.public_advance_payment, name='public_advance_payment'),
    path('gym/<slug:slug>/advance-payment/process/', views.public_process_advance_payment, name='public_process_advance_payment'),
    path('gym/<slug:slug>/membership/<int:membership_id>/checkout/', views.public_checkout_membership, name='public_checkout_membership'),
    
    # Chat con el gimnasio
    path('gym/<slug:slug>/chat/', views.public_chat, name='public_chat'),
    path('gym/<slug:slug>/chat/send/', views.public_chat_send_message, name='public_chat_send'),
    
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
