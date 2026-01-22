from django.urls import path
from . import views, api

urlpatterns = [
    path('pos/', views.pos_home, name='pos_home'),
    
    # API
    path('api/products/search/', api.search_products, name='api_pos_products_search'),
    path('api/clients/search/', api.search_clients, name='api_pos_clients_search'),
    path('api/sale/process/', api.process_sale, name='api_pos_process_sale'),
    path('api/client/<int:client_id>/cards/', api.get_client_cards, name='api_pos_client_cards'),
    
    # Order Management API
    path('api/order/<int:order_id>/', api.order_detail_json, name='api_order_detail'),
    path('api/order/<int:order_id>/cancel/', api.order_cancel, name='api_order_cancel'),
    path('api/order/<int:order_id>/update/', api.order_update, name='api_order_update'),
    path('api/order/<int:order_id>/update-status/', api.order_update_status, name='api_order_update_status'),
    path('api/order/<int:order_id>/send-ticket/', api.order_send_ticket, name='api_order_send_ticket'),
    path('api/order/<int:order_id>/invoice/', api.order_generate_invoice, name='api_order_generate_invoice'),
    path('api/subscription/<int:pk>/charge/', api.subscription_charge, name='api_subscription_charge'),
]
