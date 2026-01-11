from django import forms
from django.contrib.auth import get_user_model
from .models import StaffProfile

User = get_user_model()

class StaffUserForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre", widget=forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}))
    last_name = forms.CharField(label="Apellidos", widget=forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}))
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}), required=False, help_text="Dejar en blanco para mantener la actual (al editar) o '1234' por defecto (al crear)")

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "password"]
    
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este email ya está registrado como usuario.")
        return email

class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = StaffProfile
        fields = ["role", "bio", "color", "photo", "pin_code", "is_active"]
        widgets = {
            'role': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-20 p-1 rounded-lg border-slate-200'}),
            'pin_code': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]', 'placeholder': 'Ej: 1234'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
        }

from .models import SalaryConfig, StaffTask

class StaffSalaryForm(forms.ModelForm):
    class Meta:
        model = SalaryConfig
        fields = ["mode", "base_amount"]
        widgets = {
            'mode': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'base_amount': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
        }

class StaffTaskForm(forms.ModelForm):
    class Meta:
        model = StaffTask
        fields = ["title", "description", "due_date", "incentive_amount"]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'w-full rounded-xl border-slate-200'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-xl border-slate-200'}),
            'incentive_amount': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
        }
