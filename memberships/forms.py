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
            'name', 'description', 'image', 'base_price', 'tax_rate', 'price_strategy',
            'is_recurring', 'is_membership', 
            'frequency_amount', 'frequency_unit',
            'contract_required', 'contract_content', # Contract
            'prorate_first_month',
            # Pause fields
            'allow_pause', 'pause_fee', 'pause_min_days', 'pause_max_days', 
            'pause_max_per_year', 'pause_advance_notice_days',
            'pause_allows_gym_access', 'pause_allows_booking', 'pause_extends_end_date',
            'is_active', 'is_visible_online'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'description': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'rows': 3}),
            'base_price': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'tax_rate': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'price_strategy': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
            # Flexible Cycle
            'frequency_amount': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'frequency_unit': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
            'pack_validity_days': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
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
        }
    
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
            self.fields['tax_rate'].queryset = TaxRate.objects.filter(gym=gym)

            # Franchise Propagation Logic
            is_owner = user and gym.franchise and (user.is_superuser or user in gym.franchise.owners.all())
            
            if is_owner:
                self.fields['propagate_to_gyms'].queryset = gym.franchise.gyms.all()
            else:
                del self.fields['propagate_to_gyms']

class PlanAccessRuleForm(forms.ModelForm):
    class Meta:
        model = PlanAccessRule
        fields = ['activity_category', 'activity', 'service_category', 'service', 'quantity', 'period']
        widgets = {
            'activity_category': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm target-selector', 'data-type': 'activity_cat'}),
            'activity': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm target-selector', 'data-type': 'activity'}),
            
            'service_category': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm target-selector', 'data-type': 'service_cat'}),
            'service': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm target-selector', 'data-type': 'service'}),
            
            'quantity': forms.NumberInput(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm', 'placeholder': '0 = Ilimitado'}),
            'period': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].help_text = None
        # Make targeting fields optional in the form logic (we'll validate that at least one is present in clean)
        self.fields['activity_category'].required = False
        self.fields['activity'].required = False
        self.fields['service_category'].required = False
        self.fields['service'].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data or cleaned_data.get('DELETE'):
            return cleaned_data
            
        # Check if at least one target is selected
        targets = [
            cleaned_data.get('activity_category'),
            cleaned_data.get('activity'),
            cleaned_data.get('service_category'),
            cleaned_data.get('service')
        ]
        if not any(targets):
            raise forms.ValidationError("Debes seleccionar al menos una Actividad o Servicio.")
        return cleaned_data

PlanAccessRuleFormSet = inlineformset_factory(
    MembershipPlan, PlanAccessRule, form=PlanAccessRuleForm,
    extra=0, can_delete=True
)
