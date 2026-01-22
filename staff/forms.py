from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group  # Added Import
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
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if email and qs.exists():
            raise forms.ValidationError("Este email ya está registrado como usuario.")
        return email

class StaffProfileForm(forms.ModelForm):
    assigned_role = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label="Rol (Permisos)",
        required=False,
        widget=forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
        help_text="Define los permisos de acceso"
    )

    class Meta:
        model = StaffProfile
        fields = ["role", "assigned_role", "bio", "color", "photo", "pin_code", "is_active"]
        widgets = {
            'role': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-20 p-1 rounded-lg border-slate-200'}),
            'pin_code': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]', 'placeholder': 'Ej: 1234'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.user.groups.exists():
            self.fields['assigned_role'].initial = self.instance.user.groups.first()


from .models import SalaryConfig, StaffTask, IncentiveRule
from activities.models import Activity, ActivityCategory

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

class IncentiveRuleForm(forms.ModelForm):
    """Form para crear/editar reglas de incentivos con filtros de actividad y horario"""
    
    # Campos adicionales para días de la semana (checkboxes)
    monday = forms.BooleanField(required=False, label='Lunes')
    tuesday = forms.BooleanField(required=False, label='Martes')
    wednesday = forms.BooleanField(required=False, label='Miércoles')
    thursday = forms.BooleanField(required=False, label='Jueves')
    friday = forms.BooleanField(required=False, label='Viernes')
    saturday = forms.BooleanField(required=False, label='Sábado')
    sunday = forms.BooleanField(required=False, label='Domingo')
    
    class Meta:
        model = IncentiveRule
        fields = [
            'staff', 'name', 'type', 'value',
            'activity', 'activity_category',
            'time_start', 'time_end',
            'criteria', 'is_active'
        ]
        widgets = {
            'staff': forms.Select(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'placeholder': 'Ej: Spinning Mañanas'
            }),
            'type': forms.Select(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500'
            }),
            'value': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'placeholder': 'Porcentaje o Cantidad',
                'step': '0.01'
            }),
            'activity': forms.Select(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
            }),
            'activity_category': forms.Select(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
            }),
            'time_start': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
            }),
            'time_end': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
            }),
            'criteria': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500 font-mono text-sm',
                'rows': 2,
                'placeholder': '{"product_type": "membership"}'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-slate-300 text-blue-600 focus:ring-blue-500'
            }),
        }
    
    def __init__(self, *args, gym=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if gym:
            # Filtrar staff, actividades y categorías por gym
            self.fields['staff'].queryset = StaffProfile.objects.filter(gym=gym)
            self.fields['activity'].queryset = Activity.objects.filter(gym=gym).order_by('name')
            self.fields['activity_category'].queryset = ActivityCategory.objects.filter(gym=gym).order_by('name')
        
        # Hacer campos opcionales
        self.fields['staff'].required = False
        self.fields['activity'].required = False
        self.fields['activity_category'].required = False
        self.fields['time_start'].required = False
        self.fields['time_end'].required = False
        
        # Opciones "Ninguna" en los selects
        self.fields['staff'].empty_label = "Todo el equipo"
        self.fields['activity'].empty_label = "Cualquier actividad"
        self.fields['activity_category'].empty_label = "Cualquier categoría"
        
        # Si estamos editando, cargar los días seleccionados
        if self.instance and self.instance.pk and self.instance.weekdays:
            weekday_map = {
                'MON': 'monday', 'TUE': 'tuesday', 'WED': 'wednesday',
                'THU': 'thursday', 'FRI': 'friday', 'SAT': 'saturday', 'SUN': 'sunday'
            }
            for code, field_name in weekday_map.items():
                if code in self.instance.weekdays:
                    self.fields[field_name].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        activity = cleaned_data.get('activity')
        activity_category = cleaned_data.get('activity_category')
        time_start = cleaned_data.get('time_start')
        time_end = cleaned_data.get('time_end')
        
        # Validar que no se seleccionen actividad Y categoría simultáneamente
        if activity and activity_category:
            raise forms.ValidationError(
                "No puedes seleccionar una actividad específica Y una categoría al mismo tiempo. "
                "Elige solo una opción."
            )
        
        # Validar que si hay horario, estén ambos campos
        if (time_start and not time_end) or (time_end and not time_start):
            raise forms.ValidationError(
                "Debes especificar tanto la hora de inicio como la de fin, o dejar ambas vacías."
            )
        
        # Validar que hora fin sea mayor que hora inicio
        if time_start and time_end and time_end <= time_start:
            raise forms.ValidationError(
                "La hora de fin debe ser posterior a la hora de inicio."
            )
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Construir array de weekdays basado en checkboxes
        weekdays = []
        day_map = [
            ('monday', 'MON'), ('tuesday', 'TUE'), ('wednesday', 'WED'),
            ('thursday', 'THU'), ('friday', 'FRI'), ('saturday', 'SAT'), ('sunday', 'SUN')
        ]
        
        for field_name, code in day_map:
            if self.cleaned_data.get(field_name):
                weekdays.append(code)
        
        instance.weekdays = weekdays
        
        if commit:
            instance.save()
        return instance
