from django import forms
from .models import Discount, ReferralProgram
from clients.models import ClientGroup, ClientTag, Client
from memberships.models import MembershipPlan
from services.models import Service
from products.models import Product


class DiscountForm(forms.ModelForm):
    # Override para filtrar por gym
    target_clients = forms.ModelMultipleChoiceField(
        queryset=Client.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Clientes Específicos"
    )
    
    target_groups = forms.ModelMultipleChoiceField(
        queryset=ClientGroup.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Grupos de Clientes"
    )
    
    target_tags = forms.ModelMultipleChoiceField(
        queryset=ClientTag.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Etiquetas de Clientes"
    )
    
    specific_memberships = forms.ModelMultipleChoiceField(
        queryset=MembershipPlan.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Planes de Membresía"
    )
    
    specific_services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Servicios"
    )
    
    specific_products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Productos"
    )
    
    class Meta:
        model = Discount
        fields = [
            'name', 'description', 'discount_type', 'value',
            'code', 'code_case_sensitive',
            'applies_to', 'specific_memberships', 'specific_services', 'specific_products',
            'minimum_purchase', 'maximum_discount_amount',
            'target_type', 'target_clients', 'target_groups', 'target_tags',
            'max_uses_total', 'max_uses_per_client',
            'valid_from', 'valid_until',
            'stackable', 'priority', 'excludes_discounts',
            'is_active', 'auto_apply'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.NumberInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: VERANO2026'}),
            'code_case_sensitive': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'applies_to': forms.Select(attrs={'class': 'form-select'}),
            'minimum_purchase': forms.NumberInput(attrs={'class': 'form-control'}),
            'maximum_discount_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'target_type': forms.Select(attrs={'class': 'form-select'}),
            'max_uses_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_uses_per_client': forms.NumberInput(attrs={'class': 'form-control'}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'valid_until': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'stackable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control'}),
            'excludes_discounts': forms.CheckboxSelectMultiple(),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_apply': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        
        if gym:
            # Filtrar querysets por gimnasio
            self.fields['target_clients'].queryset = Client.objects.filter(gym=gym)
            self.fields['target_groups'].queryset = ClientGroup.objects.filter(gym=gym)
            self.fields['target_tags'].queryset = ClientTag.objects.filter(gym=gym)
            self.fields['specific_memberships'].queryset = MembershipPlan.objects.filter(gym=gym)
            self.fields['specific_services'].queryset = Service.objects.filter(gym=gym)
            self.fields['specific_products'].queryset = Product.objects.filter(gym=gym)
            self.fields['excludes_discounts'].queryset = Discount.objects.filter(gym=gym)


class ReferralProgramForm(forms.ModelForm):
    class Meta:
        model = ReferralProgram
        fields = [
            'name', 'description',
            'referrer_discount', 'referrer_credit_amount',
            'referred_discount',
            'min_referrals_for_bonus', 'bonus_discount',
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'referrer_discount': forms.Select(attrs={'class': 'form-select'}),
            'referrer_credit_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'referred_discount': forms.Select(attrs={'class': 'form-select'}),
            'min_referrals_for_bonus': forms.NumberInput(attrs={'class': 'form-control'}),
            'bonus_discount': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        
        if gym:
            # Filtrar descuentos por gimnasio
            discount_queryset = Discount.objects.filter(gym=gym, is_active=True)
            self.fields['referrer_discount'].queryset = discount_queryset
            self.fields['referred_discount'].queryset = discount_queryset
            self.fields['bonus_discount'].queryset = discount_queryset
