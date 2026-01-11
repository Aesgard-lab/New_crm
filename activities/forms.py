from django import forms
from .models import Room, ActivityCategory, Activity, CancellationPolicy
from staff.models import StaffProfile

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['name', 'capacity', 'layout_configuration']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'capacity': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'layout_configuration': forms.HiddenInput(),
        }

class ActivityCategoryForm(forms.ModelForm):
    class Meta:
        model = ActivityCategory
        fields = ['name', 'parent', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'parent': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        if gym:
            self.fields['parent'].queryset = ActivityCategory.objects.filter(gym=gym)


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['name', 'category', 'description', 'image', 'color', 'duration', 'base_capacity', 'intensity_level', 'video_url', 'eligible_staff', 'cancellation_policy']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'category': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'description': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'rows': 3}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'w-full h-10 rounded-xl border-slate-200 cursor-pointer p-1'}),
            'duration': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'base_capacity': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'intensity_level': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'video_url': forms.URLInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'eligible_staff': forms.CheckboxSelectMultiple(),
            'cancellation_policy': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        if gym:
            self.fields['category'].queryset = ActivityCategory.objects.filter(gym=gym)
            self.fields['eligible_staff'].queryset = StaffProfile.objects.filter(gym=gym).select_related('user')
            self.fields['cancellation_policy'].queryset = CancellationPolicy.objects.filter(gym=gym)

class CancellationPolicyForm(forms.ModelForm):
    class Meta:
        model = CancellationPolicy
        fields = ['name', 'window_hours', 'penalty_type', 'fee_amount']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'window_hours': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'penalty_type': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'fee_amount': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
        }
