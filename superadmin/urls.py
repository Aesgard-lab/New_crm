"""
URL configuration for superadmin panel.
"""
from django.urls import path
from . import views

app_name = 'superadmin'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Gyms
    path('gyms/', views.gym_list, name='gym_list'),
    path('gyms/create/', views.gym_create, name='gym_create'),
    path('gyms/<int:gym_id>/', views.gym_detail, name='gym_detail'),
    path('gyms/<int:gym_id>/change-plan/', views.gym_change_plan, name='gym_change_plan'),
    path('gyms/<int:gym_id>/change-billing-mode/', views.gym_change_billing_mode, name='gym_change_billing_mode'),
    path('gyms/<int:gym_id>/login-as-admin/', views.gym_login_as_admin, name='gym_login_as_admin'),
    
    # Franchises
    path('franchises/', views.franchise_list, name='franchise_list'),
    path('franchises/create/', views.franchise_create, name='franchise_create'),
    path('franchises/<int:franchise_id>/edit/', views.franchise_edit, name='franchise_edit'),
    
    # Subscription Plans
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/create/', views.plan_create, name='plan_create'),
    path('plans/<int:plan_id>/edit/', views.plan_edit, name='plan_edit'),
    
    # Billing Config
    path('billing-config/', views.billing_config, name='billing_config'),
    
    # Verifactu Developer Config
    path('verifactu-config/', views.verifactu_developer_config, name='verifactu_developer_config'),
    
    # Audit Logs
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    
    # System & Migration
    path('system/', views.system_status, name='system_status'),
    path('system/init-plans/', views.system_initialize_plans, name='system_initialize_plans'),
    path('system/migrate/', views.system_migrate_orphans, name='system_migrate_orphans'),
]
