from django.contrib import admin
from .models import Room, ActivityCategory, Activity, CancellationPolicy

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'capacity')
    list_filter = ('gym',)

@admin.register(ActivityCategory)
class ActivityCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'parent')
    list_filter = ('gym',)

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'category', 'base_capacity')
    list_filter = ('gym', 'category')

@admin.register(CancellationPolicy)
class CancellationPolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'window_hours', 'penalty_type')
    list_filter = ('gym', 'penalty_type')
