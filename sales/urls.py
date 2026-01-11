from django.urls import path
from . import views, api

urlpatterns = [
    path('pos/', views.pos_home, name='pos_home'),
    
    # API
    path('api/products/search/', api.search_products, name='api_pos_products_search'),
    path('api/clients/search/', api.search_clients, name='api_pos_clients_search'),
    path('api/sale/process/', api.process_sale, name='api_pos_process_sale'),
    path('api/client/<int:client_id>/cards/', api.get_client_cards, name='api_pos_client_cards'),
]
