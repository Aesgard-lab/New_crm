from django.contrib import admin
from .models import TaxRate, ClientWallet, WalletTransaction, WalletSettings

@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ('name', 'rate_percent', 'is_active')


@admin.register(ClientWallet)
class ClientWalletAdmin(admin.ModelAdmin):
    list_display = ('client', 'balance', 'is_active', 'allow_negative', 'total_topups', 'total_spent', 'updated_at')
    list_filter = ('is_active', 'allow_negative', 'gym')
    search_fields = ('client__email', 'client__first_name', 'client__last_name')
    raw_id_fields = ('client',)
    readonly_fields = ('balance', 'total_topups', 'total_spent', 'created_at', 'updated_at')


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'balance_after', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('wallet__client__email', 'description')
    raw_id_fields = ('wallet', 'order', 'created_by')
    readonly_fields = ('balance_before', 'balance_after', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(WalletSettings)
class WalletSettingsAdmin(admin.ModelAdmin):
    list_display = ('gym', 'wallet_enabled', 'topup_bonus_enabled', 'allow_negative_default', 'show_in_client_portal', 'show_in_app')
    list_filter = ('wallet_enabled', 'topup_bonus_enabled', 'allow_negative_default')
