from django.urls import path
from . import views, api

urlpatterns = [
    path('', views.dashboard_view, name='marketing_dashboard'),
    
    # ========== API ENDPOINTS (Client App) ==========
    # Advertisements API
    path('api/advertisements/active/', api.api_get_active_advertisements, name='api_advertisements_active'),
    path('api/advertisements/<int:ad_id>/impression/', api.api_track_advertisement_impression, name='api_advertisement_impression'),
    path('api/advertisements/<int:ad_id>/click/', api.api_track_advertisement_click, name='api_advertisement_click'),
    path('api/advertisements/positions/', api.api_get_advertisement_positions, name='api_advertisement_positions'),
    
    # Demo page (solo para desarrollo)
    path('demo/', views.demo_advertisements_view, name='marketing_demo_advertisements'),
    
    # Templates
    path('templates/', views.template_list_view, name='marketing_template_list'),
    path('templates/create/', views.template_create_view, name='marketing_template_create'),
    path('templates/<int:pk>/editor/', views.template_editor_view, name='marketing_template_editor'),
    path('templates/<int:pk>/delete/', views.template_delete_view, name='marketing_template_delete'),
    path('templates/<int:pk>/save/', views.template_save_api, name='marketing_template_save_api'),
    # Campaigns
    path('campaigns/', views.campaign_list_view, name='marketing_campaign_list'),
    path('campaigns/new/', views.campaign_create_view, name='marketing_campaign_create'),
    path('campaigns/api/create/', views.campaign_create_api, name='marketing_campaign_create_api'),
    
    # Settings
    path('settings/', views.marketing_settings_view, name='marketing_settings'),
    
    # Popups
    path('popups/', views.popup_list_view, name='marketing_popup_list'),
    path('popups/create/', views.popup_create_view, name='marketing_popup_create'),
    path('popups/<int:pk>/edit/', views.popup_edit_view, name='marketing_popup_edit'),
    path('popups/<int:pk>/delete/', views.popup_delete_view, name='marketing_popup_delete'),
    
    # Advertisements / Banners
    path('advertisements/', views.advertisement_list_view, name='marketing_advertisement_list'),
    path('advertisements/create/', views.advertisement_create_view, name='marketing_advertisement_create'),
    path('advertisements/<int:pk>/edit/', views.advertisement_edit_view, name='marketing_advertisement_edit'),
    path('advertisements/<int:pk>/delete/', views.advertisement_delete_view, name='marketing_advertisement_delete'),
    path('advertisements/<int:pk>/toggle/', views.advertisement_toggle_status_view, name='marketing_advertisement_toggle'),
    
    # Lead Management
    path('leads/', views.lead_board_view, name='lead_board'),
    path('leads/settings/', views.lead_settings_view, name='lead_settings'),
    path('leads/api/card/<int:card_id>/move/', views.lead_card_move_api, name='lead_card_move_api'),
    path('leads/api/card/<int:card_id>/', views.lead_card_detail_api, name='lead_card_detail_api'),
    
    # Automatizaciones
    path('automation/', views.automation_dashboard, name='automation_dashboard'),
    
    # Email Workflows
    path('automation/workflows/', views.workflow_list, name='workflow_list'),
    path('automation/workflows/create/', views.workflow_create, name='workflow_create'),
    path('automation/workflows/<int:pk>/', views.workflow_detail, name='workflow_detail'),
    
    # Lead Scoring
    path('automation/scoring/', views.scoring_dashboard, name='scoring_dashboard'),
    path('automation/scoring/create/', views.scoring_rule_create, name='scoring_rule_create'),
    
    # Retention Alerts
    path('automation/retention/', views.retention_alerts_list, name='retention_alerts_list'),
    path('automation/retention/create/', views.retention_rule_create, name='retention_rule_create'),
    path('automation/retention/<int:pk>/resolve/', views.retention_alert_resolve, name='retention_alert_resolve'),
]

