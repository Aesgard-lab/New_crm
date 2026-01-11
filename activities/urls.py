from django.urls import path
from . import views, scheduler_api

urlpatterns = [
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/create/', views.room_create, name='room_create'),
    path('rooms/<int:pk>/edit/', views.room_edit, name='room_edit'),
    
    path('classes/', views.activity_list, name='activity_list'),
    path('classes/create/', views.activity_create, name='activity_create'),
    path('classes/<int:pk>/edit/', views.activity_edit, name='activity_edit'),

    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),

    # Calendar / Scheduler
    path('calendar/', views.calendar_view, name='calendar_view'),
    path('api/events/', scheduler_api.get_calendar_events, name='api_calendar_events'),
    path('api/events/create/', scheduler_api.create_session_api, name='api_session_create'),
    path('api/events/update/', scheduler_api.update_session_api, name='api_session_update'),
]
