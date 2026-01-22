from django.contrib import admin
from .models import Room, ActivityCategory, Activity, ActivityPolicy, WaitlistEntry

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

@admin.register(ActivityPolicy)
class ActivityPolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'booking_window_mode', 'waitlist_enabled')
    list_filter = ('gym', 'booking_window_mode', 'waitlist_enabled')

@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('client', 'session', 'status', 'joined_at')
    list_filter = ('status', 'joined_at')

