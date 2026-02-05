from django.urls import path
from . import views, scheduler_api, session_api, review_views, analytics_views, checkin_views, quick_client_api


urlpatterns = [
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/create/', views.room_create, name='room_create'),
    path('rooms/<int:pk>/edit/', views.room_edit, name='room_edit'),
    path('rooms/export/excel/', views.room_export_excel, name='room_export_excel'),
    path('rooms/export/pdf/', views.room_export_pdf, name='room_export_pdf'),
    
    path('classes/', views.activity_list, name='activity_list'),
    path('classes/create/', views.activity_create, name='activity_create'),
    path('classes/<int:pk>/edit/', views.activity_edit, name='activity_edit'),
    path('classes/export/excel/', views.activity_export_excel, name='activity_export_excel'),
    path('classes/export/pdf/', views.activity_export_pdf, name='activity_export_pdf'),

    path('categories/', views.category_list, name='activity_category_list'),
    path('categories/create/', views.category_create, name='activity_category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='activity_category_edit'),

    # Policies
    path('policies/', views.policy_list, name='policy_list'),
    path('policies/create/', views.policy_create, name='policy_create'),
    path('policies/<int:pk>/edit/', views.policy_edit, name='policy_edit'),
    
    # Schedule Settings
    path('settings/schedule/', views.schedule_settings, name='schedule_settings'),

    # Calendar / Scheduler
    path('calendar/', views.calendar_view, name='calendar_view'),
    path('api/events/', scheduler_api.get_calendar_events, name='api_calendar_events'),
    path('api/events/create/', scheduler_api.create_session_api, name='api_session_create'),
    path('api/events/update/', scheduler_api.update_session_api, name='api_session_update'),
    
    # Session Detail API (for class modal)
    path('api/sessions/', session_api.get_sessions_list, name='api_sessions_list'),
    path('api/session/<int:session_id>/', session_api.get_session_detail, name='api_session_detail'),
    path('api/session/<int:session_id>/attendees/', session_api.add_attendee, name='api_session_add_attendee'),
    path('api/session/<int:session_id>/attendees/<int:client_id>/remove/', session_api.remove_attendee, name='api_session_remove_attendee'),
    path('api/session/<int:session_id>/attendance/', session_api.mark_attendance, name='api_session_mark_attendance'),
    path('api/session/<int:session_id>/cancel/', session_api.cancel_session, name='api_session_cancel'),
    path('api/session/<int:session_id>/update/', session_api.update_session, name='api_session_update_detail'),
    path('api/session/<int:session_id>/waitlist/<int:entry_id>/promote/', session_api.promote_waitlist, name='api_session_promote_waitlist'),
    path('api/session/<int:session_id>/waitlist/<int:entry_id>/remove/', session_api.remove_from_waitlist, name='api_session_remove_waitlist'),
    path('api/session/<int:session_id>/waitlist/add/', session_api.add_to_waitlist, name='api_session_add_waitlist'),
    path('api/session/<int:session_id>/waitlist/claim/', session_api.claim_waitlist_spot, name='api_session_claim_waitlist'),
    path('api/session/<int:session_id>/search-clients/', session_api.search_clients_for_session, name='api_session_search_clients'),
    
    # Spot Booking API
    path('api/session/<int:session_id>/spots/', session_api.get_session_spots, name='api_session_spots'),
    path('api/session/<int:session_id>/spots/reserve/', session_api.reserve_spot, name='api_session_reserve_spot'),
    
    path('api/quick-client/create/', quick_client_api.create_quick_client, name='api_quick_client_create'),
    
    # Check-in QR System
    path('checkin/settings/', checkin_views.attendance_settings_view, name='attendance_settings'),
    path('checkin/sessions/', checkin_views.today_sessions_qr_list, name='today_sessions_qr'),
    path('checkin/qr/<int:session_id>/', checkin_views.session_qr_display, name='session_qr_display'),
    path('checkin/qr/<int:session_id>/api/', checkin_views.qr_display_api, name='qr_display_api'),
    path('checkin/qr/<str:token>/', checkin_views.qr_checkin, name='qr_checkin'),
    
    # Review Reports & Settings
    path('reviews/report/', review_views.review_report, name='review_report'),
    path('reviews/export/', review_views.export_reviews_csv, name='export_reviews_csv'),
    path('reviews/<int:review_id>/approve/', review_views.toggle_review_approval, name='toggle_review_approval'),
    path('reviews/<int:review_id>/public/', review_views.toggle_review_public, name='toggle_review_public'),
    path('reviews/settings/', review_views.review_settings_view, name='review_settings'),
    
    # Analytics & Reports
    path('analytics/', analytics_views.analytics_dashboard, name='analytics_dashboard'),
    path('reports/attendance/', analytics_views.attendance_report, name='attendance_report'),
    path('reports/staff/', analytics_views.staff_report, name='staff_report'),
    path('reports/activities/', analytics_views.activity_report, name='activity_report'),
    path('reports/advanced/', analytics_views.advanced_analytics, name='advanced_analytics'),
    
    # API endpoints para gráficas
    path('api/analytics/heatmap/', analytics_views.api_heatmap_data, name='api_heatmap_data'),
    path('api/analytics/trends/', analytics_views.api_attendance_trends, name='api_attendance_trends'),
    path('api/analytics/predict/', analytics_views.api_predict_attendance, name='api_predict_attendance'),
    
    # Export
    path('reports/export/csv/', analytics_views.export_report_csv, name='export_report_csv'),
]

