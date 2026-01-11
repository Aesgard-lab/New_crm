from django.urls import path
from . import views

urlpatterns = [
    path('', views.plan_list, name='membership_plan_list'),
    path('create/', views.plan_create, name='membership_plan_create'),
    path('<int:pk>/edit/', views.plan_edit, name='membership_plan_edit'),
]
