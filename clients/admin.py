from django.contrib import admin
from .models import Client, ClientField, ClientFieldOption, ClientGroup, ClientTag


@admin.register(ClientField)
class ClientFieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'gym', 'field_type', 'is_required', 'show_in_registration', 'display_order', 'is_active']
    list_filter = ['gym', 'field_type', 'is_required', 'show_in_registration', 'is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('gym', 'name', 'slug', 'field_type')
        }),
        ('Configuración', {
            'fields': ('is_required', 'is_active')
        }),
        ('Portal Público', {
            'fields': ('show_in_registration', 'display_order'),
            'description': 'Configura si este campo aparece en el formulario de auto-registro público'
        }),
    )


@admin.register(ClientFieldOption)
class ClientFieldOptionAdmin(admin.ModelAdmin):
    list_display = ['label', 'field', 'value', 'order']
    list_filter = ['field__gym', 'field']
    search_fields = ['label', 'value']


@admin.register(ClientGroup)
class ClientGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'gym', 'parent']
    list_filter = ['gym']
    search_fields = ['name']


@admin.register(ClientTag)
class ClientTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'gym', 'color']
    list_filter = ['gym']
    search_fields = ['name']
