from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('create/', views.product_create, name='product_create'),
    path('<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('export/excel/', views.product_export_excel, name='product_export_excel'),
    path('export/pdf/', views.product_export_pdf, name='product_export_pdf'),
    
    path('categories/', views.category_list, name='product_category_list'),
    path('categories/create/', views.category_create, name='product_category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='product_category_edit'),
]
