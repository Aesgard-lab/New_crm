from django.urls import path
from . import views

urlpatterns = [
    # Client Explorer (existente)
    path('explorer/', views.client_explorer, name='client_explorer'),
    path('explorer/export/', views.export_clients_csv, name='export_clients_csv'),
    
    # Dashboard Analítico Comparativo
    path('analytics/', views.comparative_dashboard, name='comparative_dashboard'),
    path('analytics/api/', views.analytics_api, name='analytics_api'),
    path('analytics/export/', views.export_report, name='export_report'),
    
    # Vistas detalladas
    path('analytics/revenue/', views.revenue_detail, name='revenue_detail'),
    path('analytics/memberships/', views.membership_detail, name='membership_detail'),
    path('analytics/attendance/', views.attendance_detail, name='attendance_detail'),
]
