from django.urls import path
from . import views
from . import barcode_api

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('create/', views.product_create, name='product_create'),
    path('<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('export/excel/', views.product_export_excel, name='product_export_excel'),
    path('export/pdf/', views.product_export_pdf, name='product_export_pdf'),
    
    path('categories/', views.category_list, name='product_category_list'),
    path('categories/create/', views.category_create, name='product_category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='product_category_edit'),
    
    # === API de Códigos de Barras ===
    path('api/scan/', barcode_api.barcode_scan, name='product_barcode_scan'),
    path('api/barcode/validate/', barcode_api.barcode_validate, name='product_barcode_validate'),
    path('api/labels/pdf/', barcode_api.barcode_labels_pdf, name='product_labels_pdf'),
    path('api/quick-create/', barcode_api.quick_create_from_scan, name='product_quick_create'),
    path('api/without-barcode/', barcode_api.products_without_barcode, name='products_without_barcode'),
]
