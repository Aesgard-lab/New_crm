from django.urls import path
from . import views, views_redsys

urlpatterns = [
    # Settings
    path('settings/', views.settings_view, name='finance_settings'),
    path('app-settings/', views.client_app_settings, name='client_app_settings'),
    path('hardware/', views.hardware_settings, name='finance_hardware_settings'),
    path('opening-hours/', views.gym_opening_hours, name='gym_opening_hours'),
    
    # Tax Rates
    path('tax/add/', views.tax_create, name='finance_tax_create'),
    path('tax/<int:pk>/edit/', views.tax_edit, name='finance_tax_edit'),
    path('tax/<int:pk>/delete/', views.tax_delete, name='finance_tax_delete'),
    
    # Payment Methods
    path('method/add/', views.method_create, name='finance_method_create'),
    path('method/<int:pk>/edit/', views.method_edit, name='finance_method_edit'),
    path('method/<int:pk>/delete/', views.method_delete, name='finance_method_delete'),
    
    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('expenses/<int:pk>/mark-paid/', views.expense_mark_paid, name='expense_mark_paid'),
    path('expenses/generate-recurring/', views.expense_generate_recurring, name='expense_generate_recurring'),
    path('expenses/export/excel/', views.expense_export_excel, name='expense_export_excel'),
    path('expenses/export/pdf/', views.expense_export_pdf, name='expense_export_pdf'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Redsys
    path('redsys/authorize/<int:client_id>/', views_redsys.redsys_authorize_start, name='redsys_authorize_start'),
    path('redsys/notify/', views_redsys.redsys_notify, name='redsys_notify'),
    path('redsys/ok/', views_redsys.redsys_ok, name='redsys_ok'),
    path('redsys/ko/', views_redsys.redsys_ko, name='redsys_ko'),
    
    # Stripe Migration
    path('stripe/migration/', views.stripe_migration, name='stripe_migration'),
    path('stripe/migration/template/', views.stripe_migration_template, name='stripe_migration_template'),
    
    # Reports
    path('report/billing/', views.billing_dashboard, name='finance_billing_dashboard'),
]
