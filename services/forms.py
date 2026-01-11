from django import forms
from .models import Service, ServiceCategory
from activities.models import Room
from finance.models import TaxRate

class ServiceCategoryForm(forms.ModelForm):
    class Meta:
        model = ServiceCategory
        fields = ['name', 'parent', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'parent': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        if gym:
            self.fields['parent'].queryset = ServiceCategory.objects.filter(gym=gym)

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            'name', 'category', 'description', 'image', 'color',
            'duration', 'max_attendees', 'default_room',
            'base_price', 'tax_rate', 'price_strategy',
            'is_active', 'is_visible_online'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'category': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'description': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'rows': 3}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'w-full h-10 rounded-xl border-slate-200 cursor-pointer p-1'}),
            'duration': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'max_attendees': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'default_room': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'base_price': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'tax_rate': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'price_strategy': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'is_visible_online': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        if gym:
            self.fields['category'].queryset = ServiceCategory.objects.filter(gym=gym)
            self.fields['default_room'].queryset = Room.objects.filter(gym=gym)
            self.fields['tax_rate'].queryset = TaxRate.objects.filter(gym=gym) 
