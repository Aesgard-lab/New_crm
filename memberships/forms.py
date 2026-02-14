from django import forms
from django.forms import inlineformset_factory
from .models import MembershipPlan, PlanAccessRule
from finance.models import TaxRate
from activities.models import ActivityCategory, Activity
from services.models import ServiceCategory, Service
from organizations.models import Gym

class MembershipPlanForm(forms.ModelForm):
    class Meta:
        model = MembershipPlan
        fields = [
            'name', 'description', 'receipt_notes', 'image', 'barcode', 'base_price', 'tax_rate', 'additional_tax_rates', 'price_strategy',
            'is_recurring', 'is_membership', 
            'frequency_amount', 'frequency_unit',
            'activation_mode',
            # Enrollment fee / Matrícula
            'has_enrollment_fee', 'enrollment_fee', 'enrollment_fee_tax_rate', 'enrollment_fee_price_strategy', 'enrollment_fee_waivable', 'enrollment_fee_channel',
            'contract_required', 'contract_content', # Contract
            'prorate_first_month', 'scheduling_open_day',
            # Pause fields
            'allow_pause', 'pause_fee', 'pause_min_days', 'pause_max_days', 
            'pause_max_per_year', 'pause_advance_notice_days',
            'pause_allows_gym_access', 'pause_allows_booking', 'pause_extends_end_date',
            'is_active', 'is_visible_online',
            # Eligibility restrictions (nuevo sistema)
            'eligibility_criteria', 'eligibility_days_threshold', 'visibility_for_ineligible', 'eligibility_badge_text',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'description': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'rows': 3}),
            'receipt_notes': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'rows': 3, 'placeholder': 'Ej: Válido solo en horario de mañanas. No acumulable con otras promociones.'}),
            'barcode': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'placeholder': 'Ej: 8400001234567'}),
            'base_price': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'tax_rate': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'additional_tax_rates': forms.CheckboxSelectMultiple(attrs={'class': 'space-y-1'}),
            'price_strategy': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
            # Flexible Cycle
            'frequency_amount': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'frequency_unit': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
            'pack_validity_days': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'activation_mode': forms.RadioSelect(attrs={'class': 'text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'scheduling_open_day': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'min': '1', 'max': '28', 'placeholder': 'Ej: 1'}),
            
            # Enrollment Fee / Matrícula
            'has_enrollment_fee': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-amber-500 focus:ring-amber-500'}),
            'enrollment_fee': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'step': '0.01', 'placeholder': '0.00'}),
            'enrollment_fee_tax_rate': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'enrollment_fee_price_strategy': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'enrollment_fee_waivable': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'enrollment_fee_channel': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
            # Contract
            'contract_content': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'rows': 10}),
            'contract_required': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            
            # Pause Configuration
            'allow_pause': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'pause_fee': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'step': '0.01'}),
            'pause_min_days': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'pause_max_days': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'pause_max_per_year': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'pause_advance_notice_days': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'pause_allows_gym_access': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'pause_allows_booking': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'pause_extends_end_date': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            
            # Toggles
            'is_recurring': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'is_membership': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'prorate_first_month': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'is_visible_online': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            
            # Eligibility restrictions (nuevo sistema)
            'eligibility_criteria': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'eligibility_days_threshold': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'visibility_for_ineligible': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'eligibility_badge_text': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'placeholder': '🎁 Solo Nuevos'}),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Siempre limpiar el flag legacy: el nuevo sistema eligibility_criteria es la fuente de verdad
        instance.is_new_client_only = False
        if commit:
            instance.save()
            self.save_m2m()
        return instance
    
    propagate_to_gyms = forms.ModelMultipleChoiceField(
        queryset=Gym.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
        label="Propagar a otros gimnasios",
        help_text="Selecciona los gimnasios donde quieres copiar/actualizar este plan."
    )

    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if gym:
            tax_qs = TaxRate.objects.filter(gym=gym)
            self.fields['tax_rate'].queryset = tax_qs
            self.fields['additional_tax_rates'].queryset = tax_qs
            self.fields['enrollment_fee_tax_rate'].queryset = tax_qs

            # Franchise Propagation Logic
            is_owner = user and gym.franchise and (user.is_superuser or user in gym.franchise.owners.all())
            
            if is_owner:
                self.fields['propagate_to_gyms'].queryset = gym.franchise.gyms.all()
            else:
                del self.fields['propagate_to_gyms']

class PlanAccessRuleForm(forms.ModelForm):
    class Meta:
        model = PlanAccessRule
        fields = [
            'activity_category', 'activity', 'service_category', 'service', 
            'quantity', 'period',
            'usage_limit', 'usage_limit_period',
            'no_consecutive_days', 'max_simultaneous',
            'advance_booking_days', 'access_time_start', 'access_time_end',
            'booking_priority', 'early_access_hours', 'allow_waitlist'
        ]
        widgets = {
            'activity_category': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm target-selector', 'data-type': 'activity_cat'}),
            'activity': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm target-selector', 'data-type': 'activity'}),
            
            'service_category': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm target-selector', 'data-type': 'service_cat'}),
            'service': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm target-selector', 'data-type': 'service'}),
            
            'quantity': forms.NumberInput(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm', 'placeholder': '0 = Ilimitado', 'min': '0'}),
            'period': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm'}),
            
            # Límite de uso combinado
            'usage_limit': forms.NumberInput(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm', 'placeholder': '0', 'min': '0'}),
            'usage_limit_period': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm'}),
            
            # Restricciones avanzadas
            'no_consecutive_days': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-amber-600'}),
            'max_simultaneous': forms.NumberInput(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm', 'placeholder': '0', 'min': '0'}),
            'advance_booking_days': forms.NumberInput(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm', 'placeholder': '0', 'min': '0'}),
            'access_time_start': forms.TimeInput(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm', 'type': 'time'}),
            'access_time_end': forms.TimeInput(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm', 'type': 'time'}),
            'booking_priority': forms.NumberInput(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm', 'placeholder': '0', 'min': '0'}),
            'early_access_hours': forms.NumberInput(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm', 'placeholder': '0', 'min': '0'}),
            'allow_waitlist': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-blue-600'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].help_text = None
        # Make targeting fields optional (validated in clean)
        self.fields['activity_category'].required = False
        self.fields['activity'].required = False
        self.fields['service_category'].required = False
        self.fields['service'].required = False
        
        # Campos numéricos con default en el modelo → no requeridos en el form
        # Evita "Este campo es requerido" en filas nuevas/vacías
        for fname in ['quantity', 'usage_limit', 'max_simultaneous',
                      'advance_booking_days', 'booking_priority', 'early_access_hours']:
            self.fields[fname].required = False
        
        # Labels más cortos para la tabla
        self.fields['usage_limit'].label = "Límite"
        self.fields['usage_limit_period'].label = "Per. Límite"
        self.fields['no_consecutive_days'].label = "Sin Consecutivos"
        self.fields['max_simultaneous'].label = "Simultáneas"
        self.fields['advance_booking_days'].label = "Días Antelación"
        self.fields['access_time_start'].label = "Hora Desde"
        self.fields['access_time_end'].label = "Hora Hasta"
        self.fields['booking_priority'].label = "Prioridad"
        self.fields['early_access_hours'].label = "Acceso Anticipado (h)"
        self.fields['allow_waitlist'].label = "Waitlist"

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data or cleaned_data.get('DELETE'):
            return cleaned_data
        
        # Aplicar defaults para campos numéricos vacíos
        defaults = {
            'quantity': 0, 'usage_limit': 0, 'max_simultaneous': 0,
            'advance_booking_days': 0, 'booking_priority': 0, 'early_access_hours': 0,
        }
        for field, default in defaults.items():
            if cleaned_data.get(field) is None:
                cleaned_data[field] = default
        
        # Comprobar si hay al menos un target seleccionado
        targets = [
            cleaned_data.get('activity_category'),
            cleaned_data.get('activity'),
            cleaned_data.get('service_category'),
            cleaned_data.get('service')
        ]
        
        if not any(targets):
            # Si además no hay datos significativos → fila vacía, marcar para eliminar
            has_data = (
                cleaned_data.get('quantity', 0) > 0 or
                cleaned_data.get('usage_limit', 0) > 0
            )
            if has_data:
                raise forms.ValidationError(
                    "Has configurado cantidades pero no has seleccionado ninguna Actividad o Servicio. "
                    "Selecciona al menos una o elimina esta fila."
                )
            # Fila vacía sin datos → marcar para borrar silenciosamente
            cleaned_data['DELETE'] = True
            return cleaned_data
        
        # Validar coherencia del límite de uso
        usage_limit = cleaned_data.get('usage_limit', 0) or 0
        usage_limit_period = cleaned_data.get('usage_limit_period', '')
        
        if usage_limit > 0 and not usage_limit_period:
            raise forms.ValidationError(
                "Has indicado un Límite de uso pero falta seleccionar el periodo "
                "(Por Día, Por Semana o Por Mes) en la columna 'Per. Límite'."
            )
        if usage_limit == 0 and usage_limit_period:
            # Limpiar el periodo si no hay límite — no tiene sentido
            cleaned_data['usage_limit_period'] = ''
        
        return cleaned_data

PlanAccessRuleFormSet = inlineformset_factory(
    MembershipPlan, PlanAccessRule, form=PlanAccessRuleForm,
    extra=0, can_delete=True
)
