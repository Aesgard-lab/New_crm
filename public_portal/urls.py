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
    
    # PWA - Manifest dinámico, iconos y Service Worker
    path('gym/<slug:slug>/manifest.json', views.gym_manifest, name='gym_manifest'),
    path('gym/<slug:slug>/pwa-icon/<int:size>/', views.gym_pwa_icon, name='gym_pwa_icon'),
    path('gym/<slug:slug>/sw.js', views.gym_service_worker, name='gym_service_worker'),
    
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
    
    # Notificaciones y anuncios
    path('gym/<slug:slug>/notifications/', views.public_notifications, name='public_notifications'),
    
    # Gamificación
    path('gym/<slug:slug>/leaderboard/', views.public_leaderboard, name='public_leaderboard'),
    path('gym/<slug:slug>/achievements/', views.public_achievements, name='public_achievements'),
    
    # Rutinas
    path('gym/<slug:slug>/routines/', views.public_routines, name='public_routines'),
    path('gym/<slug:slug>/routines/<int:routine_id>/', views.public_routine_detail, name='public_routine_detail'),
    
    # QR Check-in
    path('gym/<slug:slug>/checkin/', views.public_checkin, name='public_checkin'),
    path('gym/<slug:slug>/checkin/my-qr/', views.public_my_qr, name='public_my_qr'),
    path('gym/<slug:slug>/checkin/process/', views.public_checkin_process, name='public_checkin_process'),
    
    # Documentos
    path('gym/<slug:slug>/documents/', views.public_documents, name='public_documents'),
    path('gym/<slug:slug>/documents/<int:document_id>/', views.public_document_detail, name='public_document_detail'),
    path('gym/<slug:slug>/documents/<int:document_id>/sign/', views.public_document_sign, name='public_document_sign'),
    
    # Recuperar contraseña
    path('gym/<slug:slug>/forgot-password/', views.public_forgot_password, name='public_forgot_password'),
    path('gym/<slug:slug>/reset-password/<str:token>/', views.public_reset_password, name='public_reset_password'),
    
    # API para calendario
    path('gym/<slug:slug>/api/schedule/events/', views.api_public_schedule_events, name='api_public_schedule_events'),
    
    # API para reservas
    path('gym/<slug:slug>/api/bookings/book/', views.api_book_session, name='api_book_session'),
    path('gym/<slug:slug>/api/bookings/<int:booking_id>/cancel/', views.api_cancel_booking, name='api_cancel_booking'),
    
    # API para lista de espera
    path('gym/<slug:slug>/api/waitlist/<int:entry_id>/claim/', views.api_claim_waitlist_spot, name='api_claim_waitlist_spot'),
    path('gym/<slug:slug>/api/waitlist/my-entries/', views.api_my_waitlist_entries, name='api_my_waitlist_entries'),
    
    # Calendar Sync (iCal)
    path('gym/<slug:slug>/calendar/', views.public_calendar_sync, name='public_calendar_sync'),
    path('gym/<slug:slug>/calendar/settings/', views.public_calendar_settings, name='public_calendar_settings'),
    path('gym/<slug:slug>/calendar/regenerate-token/', views.public_calendar_regenerate, name='public_calendar_regenerate'),
    path('gym/<slug:slug>/calendar/booking/<int:booking_id>/download/', views.public_download_booking_ics, name='public_download_booking_ics'),
    
    # Programa de Referidos
    path('gym/<slug:slug>/referrals/', views.public_referrals, name='public_referrals'),
    path('gym/<slug:slug>/api/referrals/share-data/', views.api_referral_share_data, name='api_referral_share_data'),
    
    # Monedero / Wallet
    path('gym/<slug:slug>/wallet/', views.public_wallet, name='public_wallet'),
    
    # Autenticación de clientes
    path('gym/<slug:slug>/login/', views.public_login, name='public_login'),
    path('gym/<slug:slug>/logout/', views.public_logout, name='public_logout'),
    path('gym/<slug:slug>/register/', views.public_register, name='public_register'),
]
