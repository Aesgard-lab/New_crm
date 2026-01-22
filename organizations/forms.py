from django import forms
from .models import Gym

class GymSettingsForm(forms.ModelForm):
    smtp_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full rounded-xl border-slate-200 p-2.5',
            'placeholder': '••••••••'
        }),
        help_text='Déjalo vacío si no quieres cambiar la contraseña'
    )
    
    class Meta:
        model = Gym
        fields = [
            'commercial_name', 'legal_name', 'tax_id',
            'address', 'city', 'zip_code', 'province', 'country',
            'phone', 'email', 'website',
            'instagram', 'facebook', 'tiktok', 'youtube',
            'brand_color', 'logo', 'language',
            'smtp_host', 'smtp_port', 'smtp_use_tls', 'smtp_use_ssl',
            'smtp_username', 'smtp_password', 'smtp_from_email',
            'email_signature', 'email_signature_logo', 'email_footer'
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
            
            # SMTP fields
            'smtp_host': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'smtp.gmail.com'}),
            'smtp_port': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': '587'}),
            'smtp_use_tls': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
            'smtp_use_ssl': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
            'smtp_username': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'tu@email.com'}),
            'smtp_from_email': forms.EmailInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'noreply@tugimnasio.com'}),
            
            # Email signature & footer
            'email_signature': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'rows': 4, 'placeholder': 'Ej: Saludos cordiales,\nEl equipo de Tu Gimnasio'}),
            'email_signature_logo': forms.FileInput(attrs={'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100', 'accept': 'image/*'}),
            'email_footer': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'rows': 3, 'placeholder': 'Ej: Este email fue enviado por Tu Gimnasio. Política de privacidad: https://...'}),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Solo actualizar la contraseña si se proporcionó una nueva
        if self.cleaned_data.get('smtp_password'):
            instance.smtp_password = self.cleaned_data['smtp_password']
        # Si no hay contraseña nueva, mantener la que ya existe (no sobreescribir con vacío)
        if commit:
            instance.save()
        return instance
