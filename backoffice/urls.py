from django.urls import path
from . import views
from organizations.views import gym_settings_view
from accounts.views import switch_gym
from clients.views import (
    clients_list, client_create, client_detail, client_edit, 
    client_add_note, client_delete_note, client_add_document, client_edit_note,
    client_get_stripe_setup
)

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("select-gym/", views.select_gym, name="select_gym"),
    path("switch-gym/<int:gym_id>/", switch_gym, name="switch_gym"),
    
    # Settings (Organization)
    path("settings/gym/", gym_settings_view, name="gym_settings"),

    path("clients/", clients_list, name="clients"),
    path("clients/create/", client_create, name="client_create"),
    path("clients/<int:client_id>/", client_detail, name="client_detail"),
    path("clients/<int:client_id>/edit/", client_edit, name="client_edit"),
    path("clients/<int:client_id>/add-note/", client_add_note, name="client_add_note"),
    path("clients/notes/<int:note_id>/edit/", client_edit_note, name="client_edit_note"),
    path("clients/notes/<int:note_id>/delete/", client_delete_note, name="client_delete_note"),
    path("clients/<int:client_id>/add-document/", client_add_document, name="client_add_document"),
    
    # Stripe
    path("clients/<int:client_id>/stripe-setup/", client_get_stripe_setup, name="client_get_stripe_setup"),
    
    path("staff/", views.staff_page, name="staff"),
]
