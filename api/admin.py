from django.contrib import admin
from .models import PasswordResetToken

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['email', 'code', 'created_at', 'used', 'is_valid']
    list_filter = ['used', 'created_at']
    search_fields = ['email', 'code']
    readonly_fields = ['created_at']
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Valid'

