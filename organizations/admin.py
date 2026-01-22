from django.contrib import admin
from .models import Franchise, Gym, GymOpeningHours, GymHoliday


@admin.register(Franchise)
class FranchiseAdmin(admin.ModelAdmin):
    list_display = ("name", "allow_cross_booking", "created_at")
    search_fields = ("name",)
    list_editable = ("allow_cross_booking",)


@admin.register(Gym)
class GymAdmin(admin.ModelAdmin):
    list_display = ("name", "franchise", "is_active", "created_at")
    list_filter = ("is_active", "franchise")
    search_fields = ("name",)


@admin.register(GymOpeningHours)
class GymOpeningHoursAdmin(admin.ModelAdmin):
    list_display = ("gym", "get_hours_summary")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Gimnasio", {"fields": ("gym",)}),
        ("Lunes - Viernes", {"fields": (("monday_open", "monday_close"), ("tuesday_open", "tuesday_close"), ("wednesday_open", "wednesday_close"), ("thursday_open", "thursday_close"), ("friday_open", "friday_close"))}),
        ("Fin de Semana", {"fields": (("saturday_open", "saturday_close"), ("sunday_open", "sunday_close"))}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    
    def get_hours_summary(self, obj):
        return f"L-V: {obj.monday_open}-{obj.monday_close} | S: {obj.saturday_open}-{obj.saturday_close}"
    get_hours_summary.short_description = "Horarios"


@admin.register(GymHoliday)
class GymHolidayAdmin(admin.ModelAdmin):
    list_display = ("date", "name", "gym", "is_closed", "allow_classes")
    list_filter = ("is_closed", "allow_classes", "gym", "date")
    search_fields = ("name", "gym__name")
    date_hierarchy = "date"
    
    fieldsets = (
        ("Información", {"fields": ("gym", "date", "name")}),
        ("Estado", {"fields": ("is_closed", "allow_classes")}),
        ("Horario Especial (si abre)", {"fields": (("special_open", "special_close"),), "classes": ("collapse",)}),
    )
