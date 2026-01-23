from django import forms
from django.core.exceptions import ValidationError
from .models import TaxRate, PaymentMethod, FinanceSettings, Supplier, ExpenseCategory, Expense
from organizations.models import GymOpeningHours
import json
from datetime import time

class GymOpeningHoursForm(forms.ModelForm):
    """Form para editar horarios de apertura del gym"""
    
    class Meta:
        model = GymOpeningHours
        fields = [
            'monday_open', 'monday_close',
            'tuesday_open', 'tuesday_close',
            'wednesday_open', 'wednesday_close',
            'thursday_open', 'thursday_close',
            'friday_open', 'friday_close',
            'saturday_open', 'saturday_close',
            'sunday_open', 'sunday_close',
        ]
        widgets = {
            'monday_open': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'monday_close': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'tuesday_open': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'tuesday_close': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'wednesday_open': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'wednesday_close': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'thursday_open': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'thursday_close': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'friday_open': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'friday_close': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'saturday_open': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'saturday_close': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'sunday_open': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'sunday_close': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
        }
        labels = {
            'monday_open': 'Lunes - Apertura',
            'monday_close': 'Lunes - Cierre',
            'tuesday_open': 'Martes - Apertura',
            'tuesday_close': 'Martes - Cierre',
            'wednesday_open': 'Miércoles - Apertura',
            'wednesday_close': 'Miércoles - Cierre',
            'thursday_open': 'Jueves - Apertura',
            'thursday_close': 'Jueves - Cierre',
            'friday_open': 'Viernes - Apertura',
            'friday_close': 'Viernes - Cierre',
            'saturday_open': 'Sábado - Apertura',
            'saturday_close': 'Sábado - Cierre',
            'sunday_open': 'Domingo - Apertura',
            'sunday_close': 'Domingo - Cierre',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        days = [
            ('monday', 'Lunes'),
            ('tuesday', 'Martes'),
            ('wednesday', 'Miércoles'),
            ('thursday', 'Jueves'),
            ('friday', 'Viernes'),
            ('saturday', 'Sábado'),
            ('sunday', 'Domingo'),
        ]
        
        # Validar que las horas de cierre sean después de apertura
        for day_code, day_label in days:
            open_time = cleaned_data.get(f'{day_code}_open')
            close_time = cleaned_data.get(f'{day_code}_close')
            
            if open_time and close_time:
                if open_time >= close_time:
                    raise ValidationError(f'{day_label}: la hora de cierre debe ser posterior a la de apertura')
        
        return cleaned_data


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
        fields = [
            'stripe_public_key', 'stripe_secret_key', 
            'redsys_merchant_code', 'redsys_merchant_terminal', 'redsys_secret_key', 'redsys_environment', 
            'currency',
            'auto_charge_enabled', 'auto_charge_time', 'auto_charge_max_retries', 'auto_charge_retry_days'
        ]
        widgets = {
            'stripe_public_key': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': 'pk_test_...'}),
            'stripe_secret_key': forms.PasswordInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': 'sk_test_...', 'render_value': True}),
            'redsys_merchant_code': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': 'Ej: 999000888'}),
            'redsys_merchant_terminal': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': '001'}),
            'redsys_secret_key': forms.PasswordInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': 'sq7H...', 'render_value': True}),
            'redsys_environment': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm'}),
            'currency': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'placeholder': 'EUR'}),
            'auto_charge_enabled': forms.CheckboxInput(attrs={'class': 'rounded text-indigo-600 focus:ring-indigo-500 h-5 w-5'}),
            'auto_charge_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-xl border-slate-200 text-sm'}),
            'auto_charge_max_retries': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'min': '1', 'max': '10'}),
            'auto_charge_retry_days': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200 text-sm', 'min': '1', 'max': '30'}),
        }


class AppSettingsForm(forms.ModelForm):
    class Meta:
        model = FinanceSettings
        fields = ['allow_client_delete_card', 'allow_client_pay_next_fee']
        widgets = {
            'allow_client_delete_card': forms.CheckboxInput(attrs={'class': 'rounded text-indigo-600 focus:ring-indigo-500 h-5 w-5'}),
            'allow_client_pay_next_fee': forms.CheckboxInput(attrs={'class': 'rounded text-indigo-600 focus:ring-indigo-500 h-5 w-5'}),
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'tax_id', 'email', 'phone', 'address', 'bank_account', 'contact_person', 'notes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'placeholder': 'Nombre del proveedor'}),
            'tax_id': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'placeholder': 'CIF/NIF'}),
            'email': forms.EmailInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'placeholder': 'email@proveedor.com'}),
            'phone': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'placeholder': '+34 600 000 000'}),
            'address': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200', 'rows': 3}),
            'bank_account': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'placeholder': 'ES00 0000 0000 0000 0000 0000'}),
            'contact_person': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'placeholder': 'Persona de contacto'}),
            'notes': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded text-indigo-600 focus:ring-indigo-500 h-5 w-5'}),
        }


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'color', 'icon', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'placeholder': 'Ej: Alquiler, Suministros'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-20 rounded-lg border-slate-200'}),
            'icon': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'placeholder': '💰'}),
            'description': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded text-indigo-600 focus:ring-indigo-500 h-5 w-5'}),
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'supplier', 'category', 'concept', 'reference_number', 'description',
            'base_amount', 'tax_rate', 'issue_date', 'due_date', 'payment_date',
            'status', 'payment_method', 'paid_amount',
            'is_recurring', 'recurrence_frequency', 'recurrence_day', 'is_active_recurrence',
            'attachment', 'related_products', 'notes'
        ]
        widgets = {
            'supplier': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'category': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'concept': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'placeholder': 'Ej: Alquiler Enero 2026'}),
            'reference_number': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'placeholder': 'Nº Factura'}),
            'description': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200', 'rows': 3}),
            'base_amount': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'step': '0.01', 'placeholder': '0.00'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'step': '0.01', 'placeholder': '21.00'}),
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-xl border-slate-200'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-xl border-slate-200'}),
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-xl border-slate-200'}),
            'status': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'payment_method': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'step': '0.01', 'placeholder': '0.00'}),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'rounded text-indigo-600 focus:ring-indigo-500 h-5 w-5', 'x-model': 'isRecurring'}),
            'recurrence_frequency': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200', 'x-show': 'isRecurring'}),
            'recurrence_day': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'min': '1', 'max': '28', 'x-show': 'isRecurring'}),
            'is_active_recurrence': forms.CheckboxInput(attrs={'class': 'rounded text-indigo-600 focus:ring-indigo-500 h-5 w-5', 'x-show': 'isRecurring'}),
            'attachment': forms.FileInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'related_products': forms.SelectMultiple(attrs={'class': 'w-full rounded-xl border-slate-200', 'size': '5'}),
            'notes': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200', 'rows': 3}),
        }
    
    def __init__(self, *args, gym=None, **kwargs):
        super().__init__(*args, **kwargs)
        if gym:
            self.fields['supplier'].queryset = Supplier.objects.filter(gym=gym, is_active=True)
            self.fields['category'].queryset = ExpenseCategory.objects.filter(gym=gym, is_active=True)
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(gym=gym, is_active=True)
            self.fields['related_products'].queryset = gym.products.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        is_recurring = cleaned_data.get('is_recurring')
        recurrence_frequency = cleaned_data.get('recurrence_frequency')
        recurrence_day = cleaned_data.get('recurrence_day')
        
        if is_recurring:
            if not recurrence_frequency or recurrence_frequency == 'NONE':
                raise ValidationError('Debe seleccionar una frecuencia para gastos recurrentes')
            if not recurrence_day:
                raise ValidationError('Debe especificar el día del mes para gastos recurrentes')
            if recurrence_day < 1 or recurrence_day > 28:
                raise ValidationError('El día del mes debe estar entre 1 y 28')
        
        return cleaned_data


class ExpenseQuickPayForm(forms.Form):
    """Form rápido para marcar como pagado desde el listado"""
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-xl border-slate-200'}),
        required=False
    )
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'})
    )
    
    def __init__(self, *args, gym=None, **kwargs):
        super().__init__(*args, **kwargs)
        if gym:
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(gym=gym, is_active=True)
