from django.contrib import admin
from .models import LockerZone, Locker, LockerAssignment


@admin.register(LockerZone)
class LockerZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'gym', 'rows', 'columns', 'total_lockers', 'available_lockers', 'is_active']
    list_filter = ['gym', 'is_active']
    search_fields = ['name']


@admin.register(Locker)
class LockerAdmin(admin.ModelAdmin):
    list_display = ['number', 'zone', 'size', 'status', 'monthly_price']
    list_filter = ['zone', 'status', 'size']
    search_fields = ['number', 'zone__name']


@admin.register(LockerAssignment)
class LockerAssignmentAdmin(admin.ModelAdmin):
    list_display = ['locker', 'client', 'start_date', 'end_date', 'price', 'status']
    list_filter = ['status', 'locker__zone']
    search_fields = ['locker__number', 'client__first_name', 'client__last_name']
    date_hierarchy = 'start_date'
