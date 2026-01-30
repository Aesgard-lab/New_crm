from django.urls import path
from . import views

urlpatterns = [
    # Lista y CRUD
    path('', views.discount_list, name='discount_list'),
    path('create/', views.discount_create, name='discount_create'),
    path('<int:pk>/', views.discount_detail, name='discount_detail'),
    path('<int:pk>/edit/', views.discount_edit, name='discount_edit'),
    path('<int:pk>/delete/', views.discount_delete, name='discount_delete'),
    path('<int:pk>/toggle/', views.discount_toggle_active, name='discount_toggle_active'),
    path('export/excel/', views.discount_export_excel, name='discount_export_excel'),
    path('export/pdf/', views.discount_export_pdf, name='discount_export_pdf'),
    
    # AJAX
    path('validate/', views.validate_discount_code, name='validate_discount_code'),
    path('client/<int:client_id>/available/', views.available_discounts_for_client, name='available_discounts_for_client'),
    
    # Referral Programs
    path('referrals/', views.referral_program_list, name='referral_program_list'),
    path('referrals/create/', views.referral_program_create, name='referral_program_create'),
    path('referrals/tracking/', views.referral_tracking, name='referral_tracking'),
    
    # Analytics
    path('analytics/', views.discount_analytics, name='discount_analytics'),
]
