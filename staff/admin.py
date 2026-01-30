from django.contrib import admin
from .models import (
    StaffProfile, WorkShift, SalaryConfig, IncentiveRule, 
    StaffCommission, StaffTask, AbsenceType, VacationPolicy,
    StaffVacationBalance, VacationRequest, BlockedVacationPeriod
)

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


# ==========================================
# VACATION & ABSENCE ADMIN
# ==========================================

@admin.register(AbsenceType)
class AbsenceTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "gym", "is_paid", "requires_approval", "deducts_from_balance", "is_active")
    list_filter = ("gym", "category", "is_paid", "is_active")
    list_editable = ("is_active",)
    search_fields = ("name",)


@admin.register(VacationPolicy)
class VacationPolicyAdmin(admin.ModelAdmin):
    list_display = ("gym", "base_days_per_year", "allow_carry_over", "max_carry_over_days", "min_advance_days")
    fieldsets = (
        ("Gym", {
            "fields": ("gym",)
        }),
        ("Asignación de Días", {
            "fields": ("base_days_per_year", "extra_days_per_year_worked", "max_seniority_days")
        }),
        ("Arrastre de Días", {
            "fields": ("allow_carry_over", "max_carry_over_days", "carry_over_deadline_months")
        }),
        ("Reglas de Solicitud", {
            "fields": ("min_advance_days", "min_consecutive_days", "max_consecutive_days")
        }),
        ("Calendario", {
            "fields": ("count_weekends", "exclude_holidays", "max_staff_absent_percent")
        }),
    )


@admin.register(StaffVacationBalance)
class StaffVacationBalanceAdmin(admin.ModelAdmin):
    list_display = ("staff", "year", "days_allocated", "days_carried_over", "days_used", "days_pending", "days_available")
    list_filter = ("year", "staff__gym")
    search_fields = ("staff__user__first_name", "staff__user__last_name", "staff__user__email")
    ordering = ["-year", "staff__user__first_name"]
    
    def days_available(self, obj):
        return obj.days_available
    days_available.short_description = "Disponibles"


@admin.register(VacationRequest)
class VacationRequestAdmin(admin.ModelAdmin):
    list_display = ("staff", "absence_type", "start_date", "end_date", "working_days", "status", "approved_by", "created_at")
    list_filter = ("status", "absence_type", "staff__gym", "start_date")
    search_fields = ("staff__user__first_name", "staff__user__last_name", "reason")
    date_hierarchy = "start_date"
    ordering = ["-created_at"]
    
    readonly_fields = ("working_days", "approved_by", "approved_at", "created_at", "updated_at")
    
    actions = ["approve_requests", "reject_requests"]
    
    def approve_requests(self, request, queryset):
        for vacation_request in queryset.filter(status='PENDING'):
            try:
                vacation_request.approve(request.user)
            except ValueError:
                pass
        self.message_user(request, f"Solicitudes aprobadas correctamente.")
    approve_requests.short_description = "Aprobar solicitudes seleccionadas"
    
    def reject_requests(self, request, queryset):
        for vacation_request in queryset.filter(status='PENDING'):
            try:
                vacation_request.reject(request.user, "Rechazado desde admin")
            except ValueError:
                pass
        self.message_user(request, f"Solicitudes rechazadas.")
    reject_requests.short_description = "Rechazar solicitudes seleccionadas"


@admin.register(BlockedVacationPeriod)
class BlockedVacationPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "gym", "start_date", "end_date", "is_active")
    list_filter = ("gym", "is_active", "start_date")
    list_editable = ("is_active",)
    search_fields = ("name", "reason")
