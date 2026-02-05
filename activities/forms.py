from django import forms
from .models import Room, ActivityCategory, Activity, ActivityPolicy
from .models import Room, ActivityCategory, Activity, ActivityPolicy
from organizations.models import Gym
from staff.models import StaffProfile

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['name', 'capacity', 'layout_configuration']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'capacity': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'layout_configuration': forms.HiddenInput(),
        }

class ActivityCategoryForm(forms.ModelForm):
    class Meta:
        model = ActivityCategory
        fields = ['name', 'parent', 'icon']
        labels = {
            'parent': 'Categoría Padre',
        }
        help_texts = {
            'parent': 'Selecciona una categoría principal para crear una subcategoría',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'parent': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        if gym:
            # Solo mostrar categorías principales (sin padre) como opciones de categoría padre
            self.fields['parent'].queryset = ActivityCategory.objects.filter(gym=gym, parent__isnull=True)
            self.fields['parent'].empty_label = "-- Ninguna (es categoría principal) --"


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['name', 'category', 'description', 'image', 'color', 'duration', 'base_capacity', 'intensity_level', 'video_url', 'eligible_staff', 'policy', 'qr_checkin_enabled', 'is_visible_online', 'allow_spot_booking']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'category': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'description': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'rows': 3}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'w-full h-10 rounded-xl border-slate-200 cursor-pointer p-1'}),
            'duration': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'base_capacity': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'intensity_level': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'video_url': forms.URLInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'eligible_staff': forms.CheckboxSelectMultiple(),
            'policy': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'qr_checkin_enabled': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'is_visible_online': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'allow_spot_booking': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
        }
    
    propagate_to_gyms = forms.ModelMultipleChoiceField(
        queryset=Gym.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
        label="Propagar a otros gimnasios",
        help_text="Selecciona los gimnasios donde quieres copiar/actualizar esta actividad."
    )

    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        user = kwargs.pop('user', None)  # Receive user to check franchise ownership
        super().__init__(*args, **kwargs)
        if gym:
            self.fields['category'].queryset = ActivityCategory.objects.filter(gym=gym)
            self.fields['eligible_staff'].queryset = StaffProfile.objects.filter(gym=gym).select_related('user')
            self.fields['policy'].queryset = ActivityPolicy.objects.filter(gym=gym)
            
            # Franchise Propagation Logic
            # Allow if user is Superuser OR Franchise Owner
            is_owner = user and gym.franchise and (user.is_superuser or user in gym.franchise.owners.all())
            
            if is_owner:
                # Show all gyms in franchise
                franchise_gyms = gym.franchise.gyms.all()
                self.fields['propagate_to_gyms'].queryset = franchise_gyms
                
                # Pre-select gyms that already have this activity (by name)
                if self.instance and self.instance.pk:
                    # Find gyms in franchise that have an activity with the same name
                    gyms_with_activity = list(Activity.objects.filter(
                        gym__in=franchise_gyms,
                        name=self.instance.name
                    ).exclude(gym=gym).values_list('gym_id', flat=True))
                    
                    if gyms_with_activity:
                        self.initial['propagate_to_gyms'] = gyms_with_activity
            else:
                # Remove field if not owner/admin
                del self.fields['propagate_to_gyms']

class ActivityPolicyForm(forms.ModelForm):
    MEMBERSHIP_CHOICES = [
        ('', 'Heredar de configuración general'),
        ('true', 'Sí, requerir'),
        ('false', 'No, permitir sin esto'),
    ]
    
    require_active_membership_choice = forms.ChoiceField(
        choices=MEMBERSHIP_CHOICES,
        required=False,
        label="Requiere Membresía Activa",
        widget=forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'})
    )
    
    require_paid_membership_choice = forms.ChoiceField(
        choices=MEMBERSHIP_CHOICES,
        required=False,
        label="Requiere Membresía Pagada",
        widget=forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'})
    )
    
    class Meta:
        model = ActivityPolicy
        fields = ['name', 'booking_window_mode', 'booking_window_value', 'booking_time_release', 
                  'booking_weekday_release',
                  'waitlist_enabled', 'waitlist_mode', 'waitlist_limit', 'auto_promote_cutoff_hours',
                  'waitlist_claim_timeout_minutes', 'vip_groups', 'vip_membership_plans',
                  'cancellation_window_value', 'cancellation_window_unit', 'penalty_type', 'fee_amount']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'booking_window_value': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'booking_time_release': forms.TimeInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'type': 'time'}),
            'booking_window_mode': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'booking_weekday_release': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'waitlist_mode': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'waitlist_limit': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'auto_promote_cutoff_hours': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'waitlist_claim_timeout_minutes': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'vip_groups': forms.CheckboxSelectMultiple(attrs={'class': 'rounded border-slate-300 text-[var(--brand-color)]'}),
            'vip_membership_plans': forms.CheckboxSelectMultiple(attrs={'class': 'rounded border-slate-300 text-[var(--brand-color)]'}),
            'cancellation_window_value': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'cancellation_window_unit': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'penalty_type': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'fee_amount': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        if gym:
            from clients.models import ClientGroup
            from memberships.models import MembershipPlan
            self.fields['vip_groups'].queryset = ClientGroup.objects.filter(gym=gym)
            self.fields['vip_membership_plans'].queryset = MembershipPlan.objects.filter(gym=gym, is_active=True)
        
        # Inicializar los campos de elección con los valores del modelo
        if self.instance and self.instance.pk:
            if self.instance.require_active_membership is None:
                self.initial['require_active_membership_choice'] = ''
            elif self.instance.require_active_membership:
                self.initial['require_active_membership_choice'] = 'true'
            else:
                self.initial['require_active_membership_choice'] = 'false'
                
            if self.instance.require_paid_membership is None:
                self.initial['require_paid_membership_choice'] = ''
            elif self.instance.require_paid_membership:
                self.initial['require_paid_membership_choice'] = 'true'
            else:
                self.initial['require_paid_membership_choice'] = 'false'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Convertir los campos de elección a valores del modelo
        active_choice = cleaned_data.get('require_active_membership_choice', '')
        paid_choice = cleaned_data.get('require_paid_membership_choice', '')
        
        if active_choice == '':
            cleaned_data['require_active_membership'] = None
        elif active_choice == 'true':
            cleaned_data['require_active_membership'] = True
        else:
            cleaned_data['require_active_membership'] = False
            
        if paid_choice == '':
            cleaned_data['require_paid_membership'] = None
        elif paid_choice == 'true':
            cleaned_data['require_paid_membership'] = True
        else:
            cleaned_data['require_paid_membership'] = False
        
        # Validar coherencia
        if cleaned_data.get('require_paid_membership') is True and cleaned_data.get('require_active_membership') is False:
            raise forms.ValidationError("Si requieres membresía pagada, no puedes desactivar explícitamente membresía activa")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Asignar los valores convertidos
        instance.require_active_membership = self.cleaned_data.get('require_active_membership')
        instance.require_paid_membership = self.cleaned_data.get('require_paid_membership')
        if commit:
            instance.save()
            self.save_m2m()
        return instance
