from django.contrib import admin
from django.utils.html import format_html
from .models import (
    GamificationSettings,
    ClientProgress,
    Achievement,
    ClientAchievement,
    Challenge,
    ChallengeParticipation,
    XPTransaction,
)


@admin.register(GamificationSettings)
class GamificationSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'gym',
        'enabled',
        'xp_per_attendance',
        'xp_per_review',
        'xp_per_level',
        'max_level',
        'show_leaderboard',
    ]
    list_filter = ['enabled', 'show_leaderboard', 'show_on_portal', 'show_on_app']
    search_fields = ['gym__name']
    fieldsets = (
        ('Gimnasio', {
            'fields': ('gym', 'enabled')
        }),
        ('Configuración de XP', {
            'fields': (
                'xp_per_attendance',
                'xp_per_routine_completion',
                'xp_per_review',
                'xp_per_referral',
            )
        }),
        ('Niveles', {
            'fields': ('xp_per_level', 'max_level')
        }),
        ('Visibilidad', {
            'fields': ('show_leaderboard', 'show_on_portal', 'show_on_app')
        }),
    )


@admin.register(ClientProgress)
class ClientProgressAdmin(admin.ModelAdmin):
    list_display = [
        'client_name',
        'current_level',
        'total_xp',
        'rank_display',
        'current_streak',
        'longest_streak',
    ]
    list_filter = ['current_level']
    search_fields = ['client__user__first_name', 'client__user__last_name', 'client__user__email']
    readonly_fields = [
        'total_xp',
        'current_level',
        'current_streak',
        'longest_streak',
        'total_visits',
        'total_reviews',
        'total_referrals',
        'total_routines_completed',
        'last_visit_date',
        'rank_display',
    ]
    # No incluir inlines porque no hay ForeignKey desde ClientAchievement ni XPTransaction a ClientProgress
    
    fieldsets = (
        ('Cliente', {
            'fields': ('client',)
        }),
        ('Progreso', {
            'fields': (
                'total_xp',
                'current_level',
                'rank_display',
            )
        }),
        ('Rachas', {
            'fields': ('current_streak', 'longest_streak', 'last_visit_date')
        }),
        ('Estadísticas', {
            'fields': ('total_visits', 'total_reviews', 'total_referrals', 'total_routines_completed')
        }),
    )
    
    def client_name(self, obj):
        return obj.client.user.get_full_name() or obj.client.user.email
    client_name.short_description = 'Cliente'
    
    def rank_display(self, obj):
        """Retorna el badge/rango según el nivel"""
        badge = self.get_rank_badge()
        colors = {
            'Novato': '#6B7280',
            'Aprendiz': '#10B981',
            'Experto': '#3B82F6',
            'Maestro': '#8B5CF6',
            'Leyenda': '#F59E0B',
        }
        color = colors.get(badge['name'], '#6B7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600;">{} {}</span>',
            color,
            badge['icon'],
            badge['name']
        )
    rank_display.short_description = 'Rango'


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = [
        'icon_display',
        'name',
        'requirement_type',
        'requirement_value',
        'xp_reward',
        'is_active',
        'unlocked_count',
    ]
    list_filter = ['is_active', 'requirement_type']
    search_fields = ['name', 'description', 'code']
    fieldsets = (
        ('Información Básica', {
            'fields': ('code', 'name', 'description', 'icon')
        }),
        ('Requisitos', {
            'fields': ('requirement_type', 'requirement_value')
        }),
        ('Recompensas', {
            'fields': ('xp_reward',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
    )
    
    def icon_display(self, obj):
        return format_html('<span style="font-size: 24px;">{}</span>', obj.icon)
    icon_display.short_description = 'Icono'
    
    def unlocked_count(self, obj):
        return obj.clientachievement_set.count()
    unlocked_count.short_description = 'Desbloqueados'


@admin.register(ClientAchievement)
class ClientAchievementAdmin(admin.ModelAdmin):
    list_display = ['client_name', 'achievement', 'unlocked_at']
    list_filter = ['unlocked_at', 'achievement']
    search_fields = ['client__user__first_name', 'client__user__last_name', 'achievement__name']
    readonly_fields = ['unlocked_at']
    
    def client_name(self, obj):
        return obj.client.user.get_full_name() or obj.client.user.email
    client_name.short_description = 'Cliente'


class ChallengeParticipationInline(admin.TabularInline):
    model = ChallengeParticipation
    extra = 0
    readonly_fields = ['current_progress', 'completed', 'joined_at', 'completed_at']


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'gym',
        'start_date',
        'end_date',
        'is_active_display',
        'participant_count',
        'completion_rate',
        'reward_xp',
    ]
    list_filter = ['is_active', 'start_date', 'end_date', 'gym']
    search_fields = ['title', 'description']
    inlines = [ChallengeParticipationInline]
    fieldsets = (
        ('Información Básica', {
            'fields': ('gym', 'title', 'description', 'image')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date')
        }),
        ('Objetivo', {
            'fields': ('target_type', 'target_value')
        }),
        ('Recompensas', {
            'fields': ('reward_xp', 'reward_discount')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
    )
    
    def is_active_display(self, obj):
        from django.utils import timezone
        now = timezone.now()
        if obj.start_date <= now <= obj.end_date and obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ Activo</span>')
        elif now < obj.start_date:
            return format_html('<span style="color: orange;">⏳ Próximo</span>')
        else:
            return format_html('<span style="color: gray;">✗ Finalizado</span>')
    is_active_display.short_description = 'Estado'
    
    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Participantes'
    
    def completion_rate(self, obj):
        total = obj.participants.count()
        if total == 0:
            return '0%'
        completed = obj.challengeparticipation_set.filter(completed=True).count()
        rate = (completed / total) * 100
        return format_html('<span style="font-weight: 600;">{:.1f}%</span>', rate)
    completion_rate.short_description = 'Tasa Completado'


@admin.register(ChallengeParticipation)
class ChallengeParticipationAdmin(admin.ModelAdmin):
    list_display = [
        'client_name',
        'challenge',
        'current_progress',
        'target_value',
        'progress_percentage',
        'completed',
        'joined_at',
    ]
    list_filter = ['completed', 'joined_at', 'challenge']
    search_fields = ['client__user__first_name', 'client__user__last_name', 'challenge__title']
    readonly_fields = ['joined_at', 'completed_at']
    
    def client_name(self, obj):
        return obj.client.user.get_full_name() or obj.client.user.email
    client_name.short_description = 'Cliente'
    
    def target_value(self, obj):
        return obj.challenge.target_value
    target_value.short_description = 'Objetivo'
    
    def progress_percentage(self, obj):
        if obj.challenge.target_value == 0:
            return '0%'
        percentage = (obj.current_progress / obj.challenge.target_value) * 100
        color = '#10B981' if percentage >= 100 else '#F59E0B' if percentage >= 50 else '#6B7280'
        return format_html(
            '<div style="background: #E5E7EB; border-radius: 8px; overflow: hidden; width: 100px;">'
            '<div style="background: {}; height: 20px; width: {}%; text-align: center; color: white; font-size: 11px; line-height: 20px; font-weight: 600;">{:.0f}%</div>'
            '</div>',
            color,
            min(percentage, 100),
            percentage
        )
    progress_percentage.short_description = 'Progreso %'


@admin.register(XPTransaction)
class XPTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'client_name',
        'amount_display',
        'reason',
        'balance_after',
        'created_at',
    ]
    list_filter = ['created_at', 'reason']
    search_fields = ['client__user__first_name', 'client__user__last_name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def client_name(self, obj):
        return obj.client.user.get_full_name() or obj.client.user.email
    client_name.short_description = 'Cliente'
    
    def amount_display(self, obj):
        color = '#10B981' if obj.amount > 0 else '#EF4444'
        return format_html(
            '<span style="color: {}; font-weight: 600;">{:+d} XP</span>',
            color,
            obj.amount
        )
    amount_display.short_description = 'XP'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
