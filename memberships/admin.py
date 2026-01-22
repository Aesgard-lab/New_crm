from django.contrib import admin
from .models import MembershipPlan, PlanAccessRule, MembershipPause

@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'gym', 'base_price', 'is_recurring', 'is_active', 'allow_pause']
    list_filter = ['is_recurring', 'is_active', 'allow_pause', 'gym']
    search_fields = ['name', 'description']

@admin.register(PlanAccessRule)
class PlanAccessRuleAdmin(admin.ModelAdmin):
    list_display = ['plan', 'quantity', 'period']
    list_filter = ['period', 'plan__gym']

@admin.register(MembershipPause)
class MembershipPauseAdmin(admin.ModelAdmin):
    list_display = ['membership', 'start_date', 'end_date', 'status', 'fee_charged', 'created_at']
    list_filter = ['status', 'start_date', 'end_date']
    search_fields = ['membership__client__first_name', 'membership__client__last_name', 'reason']
    readonly_fields = ['created_at', 'created_by']
