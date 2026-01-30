from django.urls import path
from . import views

app_name = "providers"

urlpatterns = [
    path("", views.provider_list, name="provider_list"),
    path("new/", views.provider_create, name="provider_create"),
    path("<int:pk>/edit/", views.provider_edit, name="provider_edit"),
    path("export/excel/", views.provider_export_excel, name="provider_export_excel"),
    path("export/pdf/", views.provider_export_pdf, name="provider_export_pdf"),
    path("purchase-orders/", views.purchase_order_list, name="purchase_order_list"),
    path("purchase-orders/new/", views.purchase_order_create, name="purchase_order_create"),
    path("purchase-orders/<int:pk>/edit/", views.purchase_order_edit, name="purchase_order_edit"),
]
