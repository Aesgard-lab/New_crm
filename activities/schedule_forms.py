from django import forms
from .models import ScheduleSettings


class ScheduleSettingsForm(forms.ModelForm):
    class Meta:
        model = ScheduleSettings
        exclude = ['gym', 'created_at', 'updated_at']
        widgets = {
            'allow_room_overlaps': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 rounded focus:ring-blue-500'
            }),
            'allow_staff_overlaps': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 rounded focus:ring-blue-500'
            }),
            'min_break_between_classes': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-slate-200 focus:border-blue-500 focus:ring-blue-500',
                'min': '0',
                'placeholder': '0'
            }),
            'max_consecutive_classes': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-slate-200 focus:border-blue-500 focus:ring-blue-500',
                'min': '0',
                'placeholder': '0 = sin límite'
            }),
            'max_advance_booking_days': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-slate-200 focus:border-blue-500 focus:ring-blue-500',
                'min': '0',
                'placeholder': '30'
            }),
            'min_advance_booking_hours': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-slate-200 focus:border-blue-500 focus:ring-blue-500',
                'min': '0',
                'placeholder': '0'
            }),
            'allow_cancellation': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 rounded focus:ring-blue-500'
            }),
            'cancellation_deadline_hours': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-slate-200 focus:border-blue-500 focus:ring-blue-500',
                'min': '0',
                'placeholder': '2'
            }),
            'enable_waitlist': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 rounded focus:ring-blue-500'
            }),
            'auto_assign_from_waitlist': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 rounded focus:ring-blue-500'
            }),
            'notify_class_changes': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 rounded focus:ring-blue-500'
            }),
            'reminder_hours_before': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-slate-200 focus:border-blue-500 focus:ring-blue-500',
                'min': '0',
                'placeholder': '2'
            }),
        }
