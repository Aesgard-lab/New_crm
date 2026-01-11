from django.contrib import admin
from .models import StaffProfile, WorkShift, SalaryConfig, IncentiveRule, StaffCommission, StaffTask

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "gym", "photo", "pin_code", "is_active")
    list_filter = ("gym", "role", "is_active")
    search_fields = ("user__username", "user__email", "pin_code")

@admin.register(WorkShift)
class WorkShiftAdmin(admin.ModelAdmin):
    list_display = ("staff", "start_time", "end_time", "duration_hours", "method", "is_closed")
    list_filter = ("method", "is_closed", "start_time")
    search_fields = ("staff__user__username",)

@admin.register(SalaryConfig)
class SalaryConfigAdmin(admin.ModelAdmin):
    list_display = ("staff", "mode", "base_amount")

@admin.register(IncentiveRule)
class IncentiveRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "value", "gym", "is_active")
    list_filter = ("type", "gym")

@admin.register(StaffCommission)
class StaffCommissionAdmin(admin.ModelAdmin):
    list_display = ("staff", "amount", "concept", "date", "rule")
    list_filter = ("staff", "date")

@admin.register(StaffTask)
class StaffTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "gym", "assigned_to", "status", "incentive_amount", "created_by")
    list_filter = ("status", "gym", "assigned_to", "assigned_role")
    search_fields = ("title", "description")
