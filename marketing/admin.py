from django.contrib import admin
from .models import MarketingSettings, EmailTemplate, Campaign, Popup

@admin.register(MarketingSettings)
class MarketingSettingsAdmin(admin.ModelAdmin):
    list_display = ('gym', 'default_sender_email', 'smtp_host', 'updated_at')
    search_fields = ('gym__name', 'default_sender_email')

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'updated_at')
    search_fields = ('name', 'gym__name')
    list_filter = ('gym',)

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'status', 'scheduled_at', 'sent_count')
    list_filter = ('status', 'gym', 'scheduled_at')
    search_fields = ('name', 'subject', 'gym__name')

@admin.register(Popup)
class PopupAdmin(admin.ModelAdmin):
    list_display = ('title', 'gym', 'is_active', 'start_date', 'end_date')
    list_filter = ('is_active', 'gym', 'audience_type')
    search_fields = ('title', 'gym__name')
