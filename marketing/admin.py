from django.contrib import admin
from .models import (
    MarketingSettings, EmailTemplate, Campaign, Popup, Advertisement, AdvertisementImpression,
    LeadPipeline, LeadStage, LeadStageAutomation, LeadCard,
    EmailWorkflow, EmailWorkflowStep, EmailWorkflowExecution, EmailWorkflowStepLog,
    LeadScoringRule, LeadScore, LeadScoreLog, LeadScoringAutomation,
    RetentionAlert, RetentionRule
)

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


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('title', 'gym', 'position', 'ad_type', 'is_active', 'priority', 'impressions', 'clicks', 'ctr', 'start_date')
    list_filter = ('is_active', 'gym', 'position', 'ad_type', 'cta_action')
    search_fields = ('title', 'gym__name', 'cta_text')
    ordering = ('priority', '-created_at')
    readonly_fields = ('impressions', 'clicks', 'ctr', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('gym', 'title', 'position', 'ad_type', 'created_by')
        }),
        ('Multimedia', {
            'fields': ('image_desktop', 'image_mobile', 'video_url')
        }),
        ('Call to Action', {
            'fields': ('cta_text', 'cta_action', 'cta_url')
        }),
        ('Segmentación', {
            'fields': ('target_gyms',)
        }),
        ('Programación', {
            'fields': ('start_date', 'end_date', 'priority', 'duration_seconds')
        }),
        ('Configuración', {
            'fields': ('is_collapsible', 'is_active')
        }),
        ('Analytics', {
            'fields': ('impressions', 'clicks', 'ctr'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AdvertisementImpression)
class AdvertisementImpressionAdmin(admin.ModelAdmin):
    list_display = ('advertisement', 'client', 'timestamp', 'clicked')
    list_filter = ('clicked', 'timestamp', 'advertisement')
    search_fields = ('advertisement__title', 'client__first_name', 'client__last_name')
    readonly_fields = ('advertisement', 'client', 'timestamp', 'clicked')
    
    def has_add_permission(self, request):
        return False  # No permitir crear manualmente


# =============================================================================
# LEAD MANAGEMENT ADMIN
# =============================================================================

class LeadStageInline(admin.TabularInline):
    model = LeadStage
    extra = 1
    ordering = ['order']

class LeadStageAutomationInline(admin.TabularInline):
    model = LeadStageAutomation
    fk_name = 'from_stage'
    extra = 0

@admin.register(LeadPipeline)
class LeadPipelineAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'is_active', 'created_at')
    list_filter = ('is_active', 'gym')
    search_fields = ('name', 'gym__name')
    inlines = [LeadStageInline]

@admin.register(LeadStage)
class LeadStageAdmin(admin.ModelAdmin):
    list_display = ('name', 'pipeline', 'order', 'monthly_quota', 'is_won', 'is_lost')
    list_filter = ('pipeline', 'is_won', 'is_lost')
    search_fields = ('name', 'pipeline__name')
    ordering = ['pipeline', 'order']
    inlines = [LeadStageAutomationInline]

@admin.register(LeadStageAutomation)
class LeadStageAutomationAdmin(admin.ModelAdmin):
    list_display = ('name', 'from_stage', 'to_stage', 'trigger_type', 'trigger_days', 'action_type', 'is_active', 'priority')
    list_filter = ('trigger_type', 'action_type', 'is_active', 'from_stage__pipeline')
    search_fields = ('name', 'from_stage__name', 'to_stage__name')
    list_editable = ('is_active', 'priority')
    ordering = ['-priority', 'from_stage__order']

@admin.register(LeadCard)
class LeadCardAdmin(admin.ModelAdmin):
    list_display = ('client', 'stage', 'assigned_to', 'source', 'next_followup', 'updated_at')
    list_filter = ('stage', 'source', 'assigned_to')
    search_fields = ('client__first_name', 'client__last_name', 'client__email')
    raw_id_fields = ('client', 'assigned_to')
    date_hierarchy = 'created_at'


# =============================================================================
# EMAIL WORKFLOWS ADMIN
# =============================================================================

class EmailWorkflowStepInline(admin.TabularInline):
    model = EmailWorkflowStep
    extra = 1
    ordering = ['order']
    fields = ('order', 'delay_days', 'subject', 'template', 'is_active')

@admin.register(EmailWorkflow)
class EmailWorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'trigger_event', 'is_active', 'created_at')
    list_filter = ('trigger_event', 'is_active', 'gym')
    search_fields = ('name', 'gym__name')
    inlines = [EmailWorkflowStepInline]

@admin.register(EmailWorkflowStep)
class EmailWorkflowStepAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'order', 'delay_days', 'subject', 'is_active')
    list_filter = ('workflow', 'is_active')
    search_fields = ('workflow__name', 'subject')
    ordering = ['workflow', 'order']

@admin.register(EmailWorkflowExecution)
class EmailWorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ('client', 'workflow', 'status', 'current_step', 'started_at')
    list_filter = ('status', 'workflow')
    search_fields = ('client__first_name', 'client__last_name', 'workflow__name')
    raw_id_fields = ('client',)
    date_hierarchy = 'started_at'

@admin.register(EmailWorkflowStepLog)
class EmailWorkflowStepLogAdmin(admin.ModelAdmin):
    list_display = ('execution', 'step', 'sent_at', 'success', 'opened')
    list_filter = ('success', 'opened')
    search_fields = ('execution__client__first_name', 'execution__client__last_name')
    date_hierarchy = 'sent_at'


# =============================================================================
# LEAD SCORING ADMIN
# =============================================================================

@admin.register(LeadScoringRule)
class LeadScoringRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'event_type', 'points', 'is_active')
    list_filter = ('event_type', 'is_active', 'gym')
    search_fields = ('name', 'gym__name')

class LeadScoreLogInline(admin.TabularInline):
    model = LeadScoreLog
    extra = 0
    readonly_fields = ('points', 'description', 'created_at')
    can_delete = False
    ordering = ['-created_at']

@admin.register(LeadScore)
class LeadScoreAdmin(admin.ModelAdmin):
    list_display = ('client', 'score', 'last_positive_event', 'last_negative_event', 'updated_at')
    list_filter = ('client__gym',)
    search_fields = ('client__first_name', 'client__last_name', 'client__email')
    readonly_fields = ('score', 'last_positive_event', 'last_negative_event', 'updated_at')
    inlines = [LeadScoreLogInline]

@admin.register(LeadScoreLog)
class LeadScoreLogAdmin(admin.ModelAdmin):
    list_display = ('lead_score', 'points', 'description', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('lead_score__client__first_name', 'lead_score__client__last_name', 'description')
    date_hierarchy = 'created_at'

@admin.register(LeadScoringAutomation)
class LeadScoringAutomationAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'min_score', 'max_score', 'action_type', 'is_active')
    list_filter = ('action_type', 'is_active', 'gym')
    search_fields = ('name', 'gym__name')


# =============================================================================
# RETENTION ALERTS ADMIN
# =============================================================================

@admin.register(RetentionAlert)
class RetentionAlertAdmin(admin.ModelAdmin):
    list_display = ('client', 'alert_type', 'status', 'risk_score', 'days_inactive', 'assigned_to', 'created_at')
    list_filter = ('alert_type', 'status', 'gym')
    search_fields = ('client__first_name', 'client__last_name', 'title')
    raw_id_fields = ('client', 'assigned_to')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

@admin.register(RetentionRule)
class RetentionRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'alert_type', 'days_threshold', 'risk_score', 'is_active')
    list_filter = ('alert_type', 'is_active', 'gym')
    search_fields = ('name', 'gym__name')

