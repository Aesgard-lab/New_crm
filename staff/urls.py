from django.urls import path
from . import views

urlpatterns = [
    path("kiosk/", views.staff_kiosk, name="staff_kiosk"),
    path("api/checkin/", views.staff_checkin, name="staff_checkin"),
    
    # Manager Dashboard
    path("list/", views.staff_list, name="staff_list"),
    path("create/", views.staff_create, name="staff_create"),
    path("edit/<int:pk>/", views.staff_edit, name="staff_edit"),
    path("detail/<int:pk>/", views.staff_detail, name="staff_detail"),
    path("detail/<int:pk>/salary/", views.staff_detail_salary, name="staff_detail_salary"),
    path("detail/<int:pk>/task/add/", views.staff_task_add, name="staff_task_add"),
    path("detail/<int:pk>/shift/toggle/", views.staff_toggle_shift, name="staff_toggle_shift"),
]
