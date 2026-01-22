from django import forms
from .models import Gym

class GymSettingsForm(forms.ModelForm):
    class Meta:
        model = Gym
        fields = [
            'commercial_name', 'legal_name', 'tax_id',
            'address', 'city', 'zip_code', 'province', 'country',
            'phone', 'email', 'website',
            'instagram', 'facebook', 'tiktok', 'youtube',
            'brand_color', 'logo', 'language'
        ]
        widgets = {
            'commercial_name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Ej: Qombo Arganzuela'}),
            'legal_name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Ej: Qombo SL'}),
            'tax_id': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Ej: B12345678'}),
            
            'address': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'city': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'zip_code': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'province': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'country': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            
            'phone': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'email': forms.EmailInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'website': forms.URLInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            
            'instagram': forms.URLInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'https://instagram.com/tu_gimnasio'}),
            'facebook': forms.URLInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'tiktok': forms.URLInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'youtube': forms.URLInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            
            'brand_color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-20 rounded p-1 border border-slate-200 cursor-pointer'}),
            'logo': forms.FileInput(attrs={'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'}),
            'language': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
        }
