from django import forms
from .models import Campaign, EmailTemplate, Popup, MarketingSettings

class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['name', 'subject', 'audience_type', 'scheduled_at']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Ej: Promo Verano'}),
            'subject': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Asunto del correo'}),
            'audience_type': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'scheduled_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
        }
class MarketingSettingsForm(forms.ModelForm):
    class Meta:
        model = MarketingSettings
        fields = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_use_tls', 'default_sender_email', 'default_sender_name']
        widgets = {
            'smtp_host': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'smtp_port': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'smtp_username': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'smtp_password': forms.PasswordInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'render_value': True}),
            'default_sender_email': forms.EmailInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'default_sender_name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'smtp_use_tls': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
        }

class PopupForm(forms.ModelForm):
    class Meta:
        model = Popup
        fields = ['title', 'content', 'audience_type', 'audience_filter_value', 'start_date', 'end_date', 'is_active', 'image']
        widgets = {
             'title': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Título'}),
             'content': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'rows': 4, 'placeholder': 'Contenido HTML permitido...'}),
             'audience_type': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'x-model': 'audienceType'}),
             'audience_filter_value': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Ej: VIP, Crossfit', 'x-show': "audienceType === 'CUSTOM_TAG'", 'x-cloak': True}),
             'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
             'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
             'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
             'image': forms.FileInput(attrs={'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'}),
        }
