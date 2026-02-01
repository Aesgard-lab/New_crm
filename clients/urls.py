from django.urls import path
from . import views
from . import portal_views
from . import review_views
from . import advance_payment_views
from . import calendar_views

urlpatterns = [
    # Duplicate clients and merging
    path("duplicates/", views.clients_duplicates, name="clients_duplicates"),
    path("merge/<int:c1_id>/<int:c2_id>/", views.merge_clients_wizard, name="merge_clients_wizard"),
    
    # Auth
    path('login/', portal_views.portal_login, name='portal_login'),
    path('logout/', portal_views.portal_logout, name='portal_logout'),
    path('forgot-password/', portal_views.portal_forgot_password, name='portal_forgot_password'),
    path('reset-password/<str:uidb64>/<str:token>/', portal_views.portal_reset_password, name='portal_reset_password'),
    
    # Dashboard
    path('', portal_views.portal_home, name='portal_home'),
    
    # Bookings
    path('bookings/', portal_views.portal_bookings, name='portal_bookings'),
    path('bookings/<int:session_id>/action/', portal_views.portal_book_session, name='portal_book_session'),
    path('history/', portal_views.portal_history, name='portal_history'),
    
    # Calendar Sync (iCal)
    path('calendar/', calendar_views.calendar_sync_page, name='portal_calendar_sync'),
    path('calendar/settings/', calendar_views.get_calendar_settings, name='portal_calendar_settings'),
    path('calendar/regenerate-token/', calendar_views.regenerate_calendar_token, name='portal_calendar_regenerate'),
    path('calendar/booking/<int:booking_id>/download/', calendar_views.download_booking_ics, name='portal_download_booking_ics'),
    
    # Profile
    path('profile/', portal_views.portal_profile, name='portal_profile'),
    path('profile/edit/', portal_views.portal_profile_edit, name='portal_profile_edit'),
    path('profile/change-password/', portal_views.portal_change_password, name='portal_change_password'),
    path('profile/toggle-email-notifications/', portal_views.portal_toggle_email_notifications, name='portal_toggle_email_notifications'),
    path('profile/cards/', portal_views.portal_payment_methods, name='portal_payment_methods'),
    path('profile/cards/setup-intent/', portal_views.portal_get_stripe_setup, name='portal_get_stripe_setup'),
    path('profile/cards/redsys-setup/', portal_views.portal_get_redsys_setup, name='portal_get_redsys_setup'),
    path('profile/cards/redsys-callback/', portal_views.portal_redsys_tokenization_callback, name='portal_redsys_tokenization_callback'),
    path('profile/cards/<str:pm_id>/delete/', portal_views.portal_delete_payment_method, name='portal_delete_payment_method'),
    
    # Routines
    path('routines/', portal_views.portal_routines, name='portal_routines'),
    path('routines/<int:routine_id>/', portal_views.portal_routine_detail, name='portal_routine_detail'),
    
    # Workout Tracking
    path('routines/day/<int:day_id>/start/', portal_views.portal_start_workout, name='portal_start_workout'),
    path('workout/<int:workout_id>/', portal_views.portal_workout_tracking, name='portal_workout_tracking'),
    path('workout/<int:workout_id>/log/<int:exercise_log_id>/set/', portal_views.portal_log_set, name='portal_log_set'),
    path('workout/<int:workout_id>/log/<int:exercise_log_id>/complete/', portal_views.portal_complete_exercise, name='portal_complete_exercise'),
    path('workout/<int:workout_id>/finish/', portal_views.portal_finish_workout, name='portal_finish_workout'),
    path('workout/<int:workout_id>/summary/', portal_views.portal_workout_summary, name='portal_workout_summary'),
    path('workout-history/', portal_views.portal_workout_history, name='portal_workout_history'),
    
    # Gamificación
    path('gamification/', portal_views.portal_gamification_dashboard, name='portal_gamification'),
    path('gamification/achievements/', portal_views.portal_achievements, name='portal_achievements'),
    path('gamification/leaderboard/', portal_views.portal_leaderboard, name='portal_leaderboard'),
    path('gamification/challenges/', portal_views.portal_challenges, name='portal_challenges'),
    path('gamification/challenges/<int:challenge_id>/join/', portal_views.portal_join_challenge, name='portal_join_challenge'),
    
    # Check-in QR (escáner de cámara)
    path('checkin/', portal_views.portal_easy_checkin, name='portal_checkin'),  # Nueva vista unificada
    path('checkin/scanner/', portal_views.portal_checkin_scanner, name='portal_checkin_scanner'),  # Vista antigua
    path('checkin/process/', portal_views.portal_checkin_process, name='portal_checkin_process'),
    path('checkin/quick/', portal_views.portal_quick_checkin, name='portal_quick_checkin'),  # Check-in directo
    path('checkin/my-qr/', portal_views.portal_checkin_qr, name='portal_checkin_qr'),
    path('checkin/refresh/', portal_views.portal_checkin_refresh, name='portal_checkin_refresh'),
    
    # Documents & Contracts
    path('documents/', portal_views.portal_documents, name='portal_documents'),
    path('documents/<int:document_id>/', portal_views.portal_document_detail, name='portal_document_detail'),
    path('documents/<int:document_id>/sign/', portal_views.portal_document_sign, name='portal_document_sign'),
    
    # Shop / Tienda
    path('shop/', portal_views.portal_shop, name='portal_shop'),
    path('shop/schedule-change/', portal_views.portal_schedule_membership_change, name='portal_schedule_membership_change'),
    path('shop/cancel-change/<int:change_id>/', portal_views.portal_cancel_scheduled_change, name='portal_cancel_scheduled_change'),
    
    # Notifications
    path('notifications/', portal_views.portal_notifications, name='portal_notifications'),
    
    # Chat
    path('chat/', portal_views.portal_chat, name='portal_chat'),
    path('chat/send/', portal_views.portal_chat_send, name='portal_chat_send'),
    path('chat/poll/', portal_views.portal_chat_poll, name='portal_chat_poll'),
    
    # Reviews
    path('review/<int:request_id>/', review_views.portal_submit_review, name='portal_submit_review'),
    
    
    # Billing
    path('billing/', portal_views.portal_billing, name='portal_billing'),
    path('billing/pay/', portal_views.portal_process_payment, name='portal_pay_next'),
    path('billing/pay/<int:payment_id>/', portal_views.portal_process_payment, name='portal_retry_payment'),
    
    # Advance Payment
    path('advance-payment/', advance_payment_views.advance_payment_view, name='portal_advance_payment'),
    path('advance-payment/process/', advance_payment_views.process_advance_payment, name='portal_process_advance_payment'),

    # API
    path('api/popup/<int:popup_id>/read/', portal_views.portal_mark_popup_read, name='portal_mark_popup_read'),
]

