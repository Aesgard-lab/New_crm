from django.urls import path, include
from . import views
from organizations.views import gym_settings_view
from accounts.views import switch_gym
from clients.views import (
    clients_list, client_create, client_detail, client_edit, 
    client_add_note, client_delete_note, client_add_document, client_edit_note,
    client_get_stripe_setup, client_import, client_export_excel, client_export_pdf,
    client_settings, api_edit_membership, api_get_membership_details, client_toggle_email_notifications,
    # Document Templates
    document_template_list, document_template_create, document_template_edit, document_template_delete,
    # Document Actions
    client_send_document, client_sign_insitu, bulk_send_document,
)

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("select-gym/", views.select_gym, name="select_gym"),
    path("switch-gym/<int:gym_id>/", switch_gym, name="switch_gym"),
    
    # Settings (Organization)
    path("settings/", views.settings_dashboard, name="settings_dashboard"),
    path("settings/gym/", gym_settings_view, name="gym_settings"),
    path("settings/clients/", client_settings, name="client_settings"),
    
    # Document Templates
    path("settings/documents/", document_template_list, name="document_template_list"),
    path("settings/documents/new/", document_template_create, name="document_template_create"),
    path("settings/documents/<int:pk>/edit/", document_template_edit, name="document_template_edit"),
    path("settings/documents/<int:pk>/delete/", document_template_delete, name="document_template_delete"),

    path("clients/", clients_list, name="clients"),
    path("clients/import/", client_import, name="client_import"),
    path("clients/export/excel/", client_export_excel, name="client_export_excel"),
    path("clients/export/pdf/", client_export_pdf, name="client_export_pdf"),
    path("clients/create/", client_create, name="client_create"),
    path("clients/<int:client_id>/", client_detail, name="client_detail"),
    path("clients/<int:client_id>/edit/", client_edit, name="client_edit"),
    path("clients/<int:client_id>/toggle-email-notifications/", client_toggle_email_notifications, name="client_toggle_email_notifications"),
    path("clients/<int:client_id>/add-note/", client_add_note, name="client_add_note"),
    path("clients/notes/<int:note_id>/edit/", client_edit_note, name="client_edit_note"),
    path("clients/notes/<int:note_id>/delete/", client_delete_note, name="client_delete_note"),
    path("clients/<int:client_id>/add-document/", client_add_document, name="client_add_document"),
    path("clients/<int:client_id>/send-document/", client_send_document, name="client_send_document"),
    path("clients/<int:client_id>/documents/<int:document_id>/sign/", client_sign_insitu, name="client_sign_insitu"),
    
    # Bulk Actions
    path("api/bulk-send-document/", bulk_send_document, name="bulk_send_document"),
    
    # API
    path("api/membership-edit/", api_edit_membership, name="api_membership_edit"),
    path("api/membership/<int:membership_id>/details/", api_get_membership_details, name="api_membership_details"),
    
    # Stripe
    path("clients/<int:client_id>/stripe-setup/", client_get_stripe_setup, name="client_get_stripe_setup"),
    
    # Chat
    path("chat/", views.chat_list, name="chat_list"),
    path("chat/search-clients/", views.chat_search_clients, name="chat_search_clients"),
    path("chat/start/<int:client_id>/", views.chat_start_with_client, name="chat_start_with_client"),
    path("chat/<int:room_id>/", views.chat_detail, name="chat_detail"),
    path("chat/<int:room_id>/send/", views.chat_send_message, name="chat_send_message"),
    path("chat/<int:room_id>/poll/", views.chat_poll_messages, name="chat_poll_messages"),
    
    path("staff/", views.staff_page, name="staff"),
    
    # Discounts and Promotions
    path("discounts/", include('discounts.urls')),
]

