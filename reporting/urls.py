from django.urls import path
from . import views

urlpatterns = [
    path('explorer/', views.client_explorer, name='client_explorer'),
    path('explorer/export/', views.export_clients_csv, name='export_clients_csv'),
]
