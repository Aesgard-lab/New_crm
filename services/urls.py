from django.urls import path
from . import views

urlpatterns = [
    path('', views.service_list, name='service_list'),
    path('create/', views.service_create, name='service_create'),
    path('<int:pk>/edit/', views.service_edit, name='service_edit'),
    path('export/excel/', views.service_export_excel, name='service_export_excel'),
    path('export/pdf/', views.service_export_pdf, name='service_export_pdf'),
    
    path('categories/', views.category_list, name='service_category_list'),
    path('categories/create/', views.category_create, name='service_category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='service_category_edit'),
]
