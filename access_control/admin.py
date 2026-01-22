from django.contrib import admin
from .models import (
    AccessDevice, AccessZone, AccessLog, AccessAlert,
    ClientAccessCredential, AccessSchedule
)


@admin.register(AccessDevice)
class AccessDeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'gym', 'device_type', 'status', 'is_active', 'last_heartbeat']
    list_filter = ['gym', 'device_type', 'status', 'provider', 'is_active']
    search_fields = ['name', 'device_id', 'ip_address']
    readonly_fields = ['last_heartbeat', 'created_at', 'updated_at']


@admin.register(AccessZone)
class AccessZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'gym', 'max_capacity', 'is_active']
    list_filter = ['gym', 'is_active']
    search_fields = ['name']
    filter_horizontal = ['allowed_membership_plans']


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'client', 'direction', 'status', 'device', 'gym']
    list_filter = ['gym', 'direction', 'status', 'denial_reason', 'timestamp']
    search_fields = ['client__first_name', 'client__last_name', 'client__email']
    readonly_fields = ['timestamp', 'raw_data']
    date_hierarchy = 'timestamp'


@admin.register(AccessAlert)
class AccessAlertAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'alert_type', 'severity', 'title', 'is_resolved', 'gym']
    list_filter = ['gym', 'alert_type', 'severity', 'is_resolved']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at']


@admin.register(ClientAccessCredential)
class ClientAccessCredentialAdmin(admin.ModelAdmin):
    list_display = ['client', 'credential_type', 'is_active', 'is_primary', 'valid_from', 'valid_until']
    list_filter = ['credential_type', 'is_active', 'is_primary']
    search_fields = ['client__first_name', 'client__last_name', 'credential_value']
    raw_id_fields = ['client']


@admin.register(AccessSchedule)
class AccessScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'gym', 'start_time', 'end_time', 'is_active']
    list_filter = ['gym', 'is_active']
    search_fields = ['name']
    filter_horizontal = ['membership_plans']
