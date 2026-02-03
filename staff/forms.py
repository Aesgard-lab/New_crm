from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group  # Added Import
from .models import StaffProfile
import re

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
            'pin_code': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]', 
                'placeholder': 'Ej: 1234',
                'pattern': '[0-9]{4,6}',
                'inputmode': 'numeric',
                'maxlength': '6',
                'title': 'Introduce 4-6 dígitos'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
        }
    
    def __init__(self, *args, gym=None, **kwargs):
        self.gym = gym
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.user.groups.exists():
                self.fields['assigned_role'].initial = self.instance.user.groups.first()
            # Si ya tiene gym asignado, usarlo
            if not self.gym and self.instance.gym:
                self.gym = self.instance.gym
    
    def clean_pin_code(self):
        """Validación del PIN único por gimnasio"""
        pin_code = self.cleaned_data.get('pin_code')
        
        if not pin_code:
            return pin_code
        
        # Validar formato: solo dígitos y longitud 4-6
        if not re.match(r'^\d{4,6}$', pin_code):
            raise forms.ValidationError(
                'El PIN debe contener solo dígitos (4-6 caracteres).'
            )
        
        # Validar que no sea un PIN débil
        if self._is_weak_pin(pin_code):
            raise forms.ValidationError(
                'El PIN es demasiado fácil. Evita secuencias (1234) o números repetidos (1111).'
            )
        
        # Validar unicidad dentro del gimnasio
        if self.gym:
            qs = StaffProfile.objects.filter(
                gym=self.gym,
                pin_code=pin_code
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise forms.ValidationError(
                    'Este PIN ya está en uso por otro empleado de este gimnasio.'
                )
        
        return pin_code
    
    def _is_weak_pin(self, pin):
        """Detecta PINs débiles como secuencias o números repetidos"""
        # Todos los dígitos iguales (1111, 2222, etc.)
        if len(set(pin)) == 1:
            return True
        
        # Secuencias comunes
        weak_sequences = [
            '0123', '1234', '2345', '3456', '4567', '5678', '6789',
            '9876', '8765', '7654', '6543', '5432', '4321', '3210',
            '0000', '1111', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999',
            '012345', '123456', '234567', '345678', '456789',
            '987654', '876543', '765432', '654321', '543210',
        ]
        
        return pin in weak_sequences


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


# =====================================================
# VACATION & ABSENCE MANAGEMENT FORMS
# =====================================================
from .models import VacationRequest, VacationPolicy, BlockedVacationPeriod, AbsenceType, StaffVacationBalance
from django.db.models import Q


class VacationRequestForm(forms.ModelForm):
    """Formulario para solicitar vacaciones/ausencias"""
    
    class Meta:
        model = VacationRequest
        fields = ['absence_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'absence_type': forms.Select(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:border-blue-500 focus:ring-blue-500',
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-xl border-slate-200 focus:border-blue-500 focus:ring-blue-500',
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-xl border-slate-200 focus:border-blue-500 focus:ring-blue-500',
            }),
            'reason': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full rounded-xl border-slate-200 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Notas adicionales (opcional)...'
            }),
        }
    
    def __init__(self, *args, gym=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if gym:
            # Filtrar tipos de ausencia por gym
            self.fields['absence_type'].queryset = AbsenceType.objects.filter(
                gym=gym,
                is_active=True
            ).order_by('name')
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError(
                    "La fecha de fin debe ser posterior o igual a la fecha de inicio."
                )
            
            # Validar que no sea más de 365 días
            from datetime import timedelta
            if (end_date - start_date).days > 365:
                raise forms.ValidationError(
                    "No puedes solicitar más de 365 días de ausencia en una sola solicitud."
                )
        
        return cleaned_data


class VacationPolicyForm(forms.ModelForm):
    """Formulario para configurar política de vacaciones"""
    
    class Meta:
        model = VacationPolicy
        fields = [
            'base_days_per_year', 'extra_days_per_year_worked', 'max_seniority_days',
            'allow_carry_over', 'max_carry_over_days', 'carry_over_deadline_months',
            'min_advance_days', 'max_consecutive_days',
            'count_weekends', 'exclude_holidays'
        ]
        widgets = {
            'base_days_per_year': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'min': '0',
                'max': '365',
            }),
            'extra_days_per_year_worked': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'min': '0',
                'step': '1',
            }),
            'max_seniority_days': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'min': '0',
            }),
            'allow_carry_over': forms.CheckboxInput(attrs={
                'class': 'rounded border-slate-300 text-blue-600 focus:ring-blue-500'
            }),
            'max_carry_over_days': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'min': '0',
            }),
            'carry_over_deadline_months': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'min': '0',
                'max': '12',
            }),
            'min_advance_days': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'min': '0',
            }),
            'max_consecutive_days': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'min': '0',
            }),
            'count_weekends': forms.CheckboxInput(attrs={
                'class': 'rounded border-slate-300 text-blue-600 focus:ring-blue-500'
            }),
            'exclude_holidays': forms.CheckboxInput(attrs={
                'class': 'rounded border-slate-300 text-blue-600 focus:ring-blue-500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Añadir labels en español
        self.fields['base_days_per_year'].label = 'Días base por año'
        self.fields['extra_days_per_year_worked'].label = 'Días extra por año de antigüedad'
        self.fields['max_seniority_days'].label = 'Máximo bonus por antigüedad'
        self.fields['allow_carry_over'].label = 'Permitir arrastre de días'
        self.fields['max_carry_over_days'].label = 'Máximo días a arrastrar'
        self.fields['carry_over_deadline_months'].label = 'Meses para usar días arrastrados'
        self.fields['min_advance_days'].label = 'Días mínimos de antelación'
        self.fields['max_consecutive_days'].label = 'Máximo días consecutivos'
        self.fields['count_weekends'].label = 'Contar fines de semana'
        self.fields['exclude_holidays'].label = 'Excluir festivos'


class BlockedPeriodForm(forms.ModelForm):
    """Formulario para crear periodos bloqueados"""
    
    class Meta:
        model = BlockedVacationPeriod
        fields = ['name', 'start_date', 'end_date', 'reason']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'placeholder': 'Ej: Navidad, Campaña Verano...'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
            }),
            'reason': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'placeholder': 'Motivo del bloqueo (opcional)...'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError(
                "La fecha de fin debe ser posterior o igual a la fecha de inicio."
            )
        
        return cleaned_data


class BalanceAdjustForm(forms.ModelForm):
    """Formulario para ajustar manualmente el balance de vacaciones"""
    
    class Meta:
        model = StaffVacationBalance
        fields = ['days_allocated', 'days_carried_over', 'days_adjustment', 'notes']
        widgets = {
            'days_allocated': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'min': '0',
                'step': '0.5',
            }),
            'days_carried_over': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'min': '0',
                'step': '0.5',
            }),
            'days_adjustment': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'step': '0.5',
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full rounded-xl border-slate-200 focus:ring-blue-500',
                'placeholder': 'Notas del ajuste (opcional)...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['days_allocated'].label = 'Días asignados'
        self.fields['days_carried_over'].label = 'Días arrastrados del año anterior'
        self.fields['days_adjustment'].label = 'Ajuste manual (+/-)'
        self.fields['notes'].label = 'Notas'
