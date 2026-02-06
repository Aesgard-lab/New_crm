from django.contrib import admin
from .models import (
    SubscriptionPlan,
    GymSubscription,
    FranchiseSubscription,
    Invoice,
    PaymentAttempt,
    BillingConfig,
    AuditLog,
    GymEmailUsage
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_monthly', 'is_demo', 'is_active', 'module_transactional_email']
    list_filter = ['is_demo', 'is_active', 'module_transactional_email']
    search_fields = ['name']
    
    fieldsets = (
        ('Info Básica', {
            'fields': ('name', 'description', 'display_order')
        }),
        ('Precios', {
            'fields': ('price_monthly', 'price_yearly')
        }),
        ('Módulos Habilitados', {
            'fields': (
                'module_pos', 'module_calendar', 'module_marketing',
                'module_reporting', 'module_client_portal', 'module_public_portal',
                'module_automations', 'module_routines', 'module_gamification',
                'module_verifactu', 'module_transactional_email'
            )
        }),
        ('Límites de Email Transaccional', {
            'fields': ('transactional_email_limit_daily', 'transactional_email_limit_monthly'),
            'classes': ('collapse',),
            'description': 'Configura límites de envío para gimnasios que usen el servicio de email de la plataforma'
        }),
        ('Límites Generales', {
            'fields': ('max_members', 'max_staff', 'max_locations')
        }),
        ('Estado', {
            'fields': ('is_demo', 'is_active')
        }),
        ('Stripe', {
            'fields': ('stripe_product_id', 'stripe_price_monthly_id', 'stripe_price_yearly_id'),
            'classes': ('collapse',)
        })
    )


@admin.register(GymSubscription)
class GymSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['gym', 'plan', 'status', 'current_period_end']
    list_filter = ['status', 'billing_frequency']
    search_fields = ['gym__name']
    raw_id_fields = ['gym']


@admin.register(FranchiseSubscription)
class FranchiseSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['franchise', 'plan', 'status', 'current_period_end']
    list_filter = ['status']
    search_fields = ['franchise__name']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'gym', 'franchise', 'total_amount', 'status', 'issue_date']
    list_filter = ['status', 'issue_date']
    search_fields = ['invoice_number', 'gym__name', 'franchise__name']
    date_hierarchy = 'issue_date'


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'status', 'amount', 'attempted_at']
    list_filter = ['status']


@admin.register(BillingConfig)
class BillingConfigAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Only allow one instance
        return BillingConfig.objects.count() == 0
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'superadmin', 'target_gym', 'target_franchise', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['superadmin__email', 'target_gym__name', 'target_franchise__name', 'description']
    readonly_fields = ['action', 'superadmin', 'target_gym', 'target_franchise', 'description', 'ip_address', 'user_agent', 'created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(GymEmailUsage)
class GymEmailUsageAdmin(admin.ModelAdmin):
    list_display = ['gym', 'date', 'emails_sent']
    list_filter = ['date', 'gym']
    search_fields = ['gym__name']
    date_hierarchy = 'date'
    readonly_fields = ['gym', 'date', 'emails_sent']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
