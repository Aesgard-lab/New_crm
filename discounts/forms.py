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
    """Formulario completo para programas de referidos"""
    
    class Meta:
        model = ReferralProgram
        fields = [
            'name', 'description', 'reward_type',
            # Recompensas para quien refiere
            'referrer_discount', 'referrer_credit_amount', 'referrer_free_days',
            # Recompensas para el referido
            'referred_discount', 'referred_credit_amount', 'referred_free_days',
            # Condiciones
            'require_membership_purchase', 'min_membership_value',
            # Bonus por múltiples referidos
            'min_referrals_for_bonus', 'bonus_discount', 'bonus_credit_amount',
            # Límites
            'max_referrals_per_client', 'max_total_referrals',
            # Vigencia
            'valid_from', 'valid_until',
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Trae un Amigo 2026'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción visible para los clientes'}),
            'reward_type': forms.Select(attrs={'class': 'form-select'}),
            # Referrer rewards
            'referrer_discount': forms.Select(attrs={'class': 'form-select'}),
            'referrer_credit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'referrer_free_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            # Referred rewards
            'referred_discount': forms.Select(attrs={'class': 'form-select'}),
            'referred_credit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'referred_free_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            # Conditions
            'require_membership_purchase': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'min_membership_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            # Bonus
            'min_referrals_for_bonus': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'bonus_discount': forms.Select(attrs={'class': 'form-select'}),
            'bonus_credit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            # Limits
            'max_referrals_per_client': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': '0 = ilimitado'}),
            'max_total_referrals': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': '0 = ilimitado'}),
            # Validity
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'valid_until': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        gyms = kwargs.pop('gyms', None)  # Para franquicias
        super().__init__(*args, **kwargs)
        
        # Filtrar descuentos por gimnasio o gimnasios de franquicia
        if gyms:
            discount_queryset = Discount.objects.filter(gym__in=gyms, is_active=True)
        elif gym:
            discount_queryset = Discount.objects.filter(gym=gym, is_active=True)
        else:
            discount_queryset = Discount.objects.none()
        
        self.fields['referrer_discount'].queryset = discount_queryset
        self.fields['referred_discount'].queryset = discount_queryset
        self.fields['bonus_discount'].queryset = discount_queryset
        
        # Hacer opcionales los campos de descuento
        self.fields['referrer_discount'].required = False
        self.fields['referred_discount'].required = False
        self.fields['bonus_discount'].required = False


class ReferralSettingsForm(forms.Form):
    """Formulario para configuración de referidos en PublicPortalSettings"""
    referral_program_enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Habilitar Programa de Referidos'
    )
    referral_share_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '¡Únete a mi gimnasio! Usa mi código de referido y ambos obtendremos descuentos.'
        }),
        label='Mensaje para Compartir'
    )
