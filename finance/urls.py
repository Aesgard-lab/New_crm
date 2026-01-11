from django.urls import path
from . import views, views_redsys

urlpatterns = [
    # Settings
    path('settings/', views.settings_view, name='finance_settings'),
    
    # Tax Rates
    path('tax/add/', views.tax_create, name='finance_tax_create'),
    path('tax/<int:pk>/edit/', views.tax_edit, name='finance_tax_edit'),
    path('tax/<int:pk>/delete/', views.tax_delete, name='finance_tax_delete'),
    
    # Payment Methods
    path('method/add/', views.method_create, name='finance_method_create'),
    path('method/<int:pk>/edit/', views.method_edit, name='finance_method_edit'),
    path('method/<int:pk>/delete/', views.method_delete, name='finance_method_delete'),
    
    # Redsys
    path('redsys/authorize/<int:client_id>/', views_redsys.redsys_authorize_start, name='redsys_authorize_start'),
    path('redsys/notify/', views_redsys.redsys_notify, name='redsys_notify'),
    path('redsys/ok/', views_redsys.redsys_ok, name='redsys_ok'),
    path('redsys/ko/', views_redsys.redsys_ko, name='redsys_ko'),
]
