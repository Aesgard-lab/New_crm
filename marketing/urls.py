from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='marketing_dashboard'),
    
    # Templates
    path('templates/', views.template_list_view, name='marketing_template_list'),
    path('templates/create/', views.template_create_view, name='marketing_template_create'),
    path('templates/<int:pk>/editor/', views.template_editor_view, name='marketing_template_editor'),
    path('templates/<int:pk>/delete/', views.template_delete_view, name='marketing_template_delete'),
    path('templates/<int:pk>/save/', views.template_save_api, name='marketing_template_save_api'),
    # Campaigns
    path('campaigns/', views.campaign_list_view, name='marketing_campaign_list'),
    path('campaigns/new/', views.campaign_create_view, name='marketing_campaign_create'),
    path('campaigns/new/', views.campaign_create_view, name='marketing_campaign_create'),
    path('campaigns/api/create/', views.campaign_create_api, name='marketing_campaign_create_api'),
    
    # Settings
    path('settings/', views.marketing_settings_view, name='marketing_settings'),
    
    # Popups
    path('popups/', views.popup_list_view, name='marketing_popup_list'),
    path('popups/create/', views.popup_create_view, name='marketing_popup_create'),
    path('popups/<int:pk>/edit/', views.popup_edit_view, name='marketing_popup_edit'),
    path('popups/<int:pk>/delete/', views.popup_delete_view, name='marketing_popup_delete'),
]
