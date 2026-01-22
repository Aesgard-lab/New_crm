from django import forms
from organizations.models import Franchise, Gym
from accounts.models import User

class FranchiseForm(forms.ModelForm):
    """
    Form to create or edit a Franchise.
    """
    owners = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5 bg-white'}),
        help_text="Selecciona los usuarios propietarios de esta franquicia"
    )

    class Meta:
        model = Franchise
        fields = ['name', 'owners', 'allow_cross_booking']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Ej: FitLife España'}),
            'allow_cross_booking': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500'}),
        }
        labels = {
            'name': 'Nombre de la Franquicia',
            'owners': 'Propietarios (Dueños)',
            'allow_cross_booking': 'Permitir Reservas Cruzadas',
        }
        help_texts = {
            'allow_cross_booking': 'Los clientes pueden reservar clases en cualquier gimnasio de la franquicia',
        }

class GymCreationForm(forms.ModelForm):
    """
    Form to create a NEW gym.
    Basic fields only, settings can be configured later.
    """
    class Meta:
        model = Gym
        fields = [
            'name', 'commercial_name', 'franchise', 
            'tax_id', 'address', 'city', 'country'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Nombre Interno'}),
            'commercial_name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Nombre Comercial / Público'}),
            'franchise': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'tax_id': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'address': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'city': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'country': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
        }
