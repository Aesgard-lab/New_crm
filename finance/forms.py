from django import forms
from .models import TaxRate, PaymentMethod, FinanceSettings

class TaxRateForm(forms.ModelForm):
    class Meta:
        model = TaxRate
        fields = ['name', 'rate_percent', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500 focus:border-blue-500'}),
            'rate_percent': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500 focus:border-blue-500', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
        }

class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ['name', 'is_cash', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500 focus:border-blue-500'}),
            'is_cash': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
        }
class FinanceSettingsForm(forms.ModelForm):
    class Meta:
        model = FinanceSettings
        fields = ['stripe_public_key', 'stripe_secret_key', 'redsys_merchant_code', 'redsys_merchant_terminal', 'redsys_secret_key', 'redsys_environment', 'currency']
        widgets = {
            'stripe_public_key': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': 'pk_test_...'}),
            'stripe_secret_key': forms.PasswordInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': 'sk_test_...', 'render_value': True}),
            'redsys_merchant_code': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': 'Ej: 999000888'}),
            'redsys_merchant_terminal': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': '001'}),
            'redsys_secret_key': forms.PasswordInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': 'sq7H...', 'render_value': True}),
            'redsys_environment': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm'}),
            'currency': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': 'EUR'}),
        }
