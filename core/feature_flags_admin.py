"""
Feature Flags Admin Configuration
"""
from django.contrib import admin
from django.utils.html import format_html
from .feature_flags import FeatureFlag


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'status_badge',
        'rollout_strategy',
        'rollout_percentage',
        'scheduling_info',
        'updated_at'
    ]
    list_filter = ['enabled', 'rollout_strategy', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'enabled')
        }),
        ('Rollout Configuration', {
            'fields': ('rollout_strategy', 'rollout_percentage', 'user_ids', 'group_names'),
            'classes': ('collapse',)
        }),
        ('Scheduling', {
            'fields': ('enable_at', 'disable_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        if obj.enabled:
            return format_html(
                '<span style="color: white; background-color: #28a745; '
                'padding: 3px 10px; border-radius: 3px;">ON</span>'
            )
        return format_html(
            '<span style="color: white; background-color: #dc3545; '
            'padding: 3px 10px; border-radius: 3px;">OFF</span>'
        )
    status_badge.short_description = 'Status'
    
    def scheduling_info(self, obj):
        parts = []
        if obj.enable_at:
            parts.append(f"Enable: {obj.enable_at.strftime('%Y-%m-%d %H:%M')}")
        if obj.disable_at:
            parts.append(f"Disable: {obj.disable_at.strftime('%Y-%m-%d %H:%M')}")
        return ' | '.join(parts) if parts else '-'
    scheduling_info.short_description = 'Schedule'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['enable_flags', 'disable_flags']
    
    @admin.action(description='Enable selected feature flags')
    def enable_flags(self, request, queryset):
        count = queryset.update(enabled=True)
        self.message_user(request, f'{count} feature flags enabled.')
    
    @admin.action(description='Disable selected feature flags')
    def disable_flags(self, request, queryset):
        count = queryset.update(enabled=False)
        self.message_user(request, f'{count} feature flags disabled.')
