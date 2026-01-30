from django.urls import path
from . import views

urlpatterns = [
    path("kiosk/", views.staff_kiosk, name="staff_kiosk"),
    path("api/checkin/", views.staff_checkin, name="staff_checkin"),
    
    # Manager Dashboard
    path("list/", views.staff_list, name="staff_list"),
    path("create/", views.staff_create, name="staff_create"),
    path("edit/<int:pk>/", views.staff_edit, name="staff_edit"),
    path("detail/<int:pk>/", views.staff_detail, name="staff_detail"),
    path("detail/<int:pk>/salary/", views.staff_detail_salary, name="staff_detail_salary"),
    path("detail/<int:pk>/task/add/", views.staff_task_add, name="staff_task_add"),
    path("detail/<int:pk>/shift/toggle/", views.staff_toggle_shift, name="staff_toggle_shift"),
    
    # Role Settings
    path("roles/", views.role_list, name="role_list"),
    path("roles/create/", views.role_create, name="role_create"),
    path("roles/<int:role_id>/edit/", views.role_edit, name="role_edit"),
    
    # Audit Logs
    path("audit-logs/", views.audit_log_list, name="audit_log_list"),
    
    # Incentive Rules
    path("incentives/", views.incentive_list, name="incentive_list"),
    path("incentives/create/", views.incentive_create, name="incentive_create"),
    path("incentives/<int:pk>/edit/", views.incentive_edit, name="incentive_edit"),
    path("incentives/<int:pk>/delete/", views.incentive_delete, name="incentive_delete"),
    
    # Rating Incentives
    path("rating-incentives/", views.rating_incentive_list, name="rating_incentive_list"),
    path("rating-incentives/create/", views.rating_incentive_create, name="rating_incentive_create"),
    path("rating-incentives/<int:pk>/edit/", views.rating_incentive_edit, name="rating_incentive_edit"),
    path("rating-incentives/<int:pk>/delete/", views.rating_incentive_delete, name="rating_incentive_delete"),
    path("rating-performance/", views.staff_rating_performance, name="staff_rating_performance"),
    
    # Staff Personal View
    path("my-commissions/", views.my_commissions, name="my_commissions"),
    
    # ==========================================
    # VACATION & ABSENCE MANAGEMENT
    # ==========================================
    # Calendar & Dashboard
    path("vacations/", views.vacation_calendar, name="vacation_calendar"),
    path("vacations/calendar-data/", views.vacation_calendar_data, name="vacation_calendar_data"),
    
    # My Vacations (Employee)
    path("vacations/my/", views.my_vacations, name="my_vacations"),
    path("vacations/request/", views.vacation_request_create, name="vacation_request_create"),
    path("vacations/request/<int:pk>/cancel/", views.vacation_request_cancel, name="vacation_request_cancel"),
    
    # Manager Actions
    path("vacations/pending/", views.vacation_pending_list, name="vacation_pending_list"),
    path("vacations/request/<int:pk>/approve/", views.vacation_request_approve, name="vacation_request_approve"),
    path("vacations/request/<int:pk>/reject/", views.vacation_request_reject, name="vacation_request_reject"),
    
    # Balance Management
    path("vacations/balances/", views.vacation_balances, name="vacation_balances"),
    path("vacations/balance/<int:pk>/adjust/", views.vacation_balance_adjust, name="vacation_balance_adjust"),
    
    # Policy & Settings
    path("vacations/settings/", views.vacation_settings, name="vacation_settings"),
    path("vacations/blocked-periods/", views.blocked_periods_list, name="blocked_periods_list"),
    path("vacations/blocked-periods/create/", views.blocked_period_create, name="blocked_period_create"),
    path("vacations/blocked-periods/<int:pk>/delete/", views.blocked_period_delete, name="blocked_period_delete"),
]

