from django import forms
from .models import Campaign, EmailTemplate, Popup, MarketingSettings, Advertisement, SavedAudience

class CampaignForm(forms.ModelForm):
    saved_audience = forms.ModelChoiceField(
        queryset=SavedAudience.objects.none(),
        required=False,
        label='Audiencia Guardada',
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border-slate-200 p-2.5',
            'x-show': "audienceType === 'SAVED_AUDIENCE'",
            'x-cloak': True
        })
    )
    
    class Meta:
        model = Campaign
        fields = ['name', 'subject', 'audience_type', 'audience_filter_value', 'saved_audience', 'scheduled_at']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Ej: Promo Verano'}),
            'subject': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Asunto del correo'}),
            'audience_type': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'x-model': 'audienceType'}),
            'audience_filter_value': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Nombre de etiqueta', 'x-show': "audienceType === 'CUSTOM_TAG'", 'x-cloak': True}),
            'scheduled_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        if gym:
            self.fields['saved_audience'].queryset = SavedAudience.objects.filter(gym=gym, is_active=True)
class MarketingSettingsForm(forms.ModelForm):
    smtp_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full rounded-xl border-slate-200 p-2.5',
            'placeholder': 'Dejar vacío para mantener actual'
        }),
        help_text='Contraseña SMTP (se cifra automáticamente)'
    )
    
    class Meta:
        model = MarketingSettings
        fields = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_use_tls', 'default_sender_email', 'default_sender_name']
        widgets = {
            'smtp_host': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'smtp_port': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'smtp_username': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'default_sender_email': forms.EmailInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'default_sender_name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
            'smtp_use_tls': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Si hay contraseña guardada, mostrar placeholder
            if self.instance.smtp_password:
                self.fields['smtp_password'].widget.attrs['placeholder'] = '••••••••'
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Solo actualizar contraseña si se proporcionó una nueva
        password = self.cleaned_data.get('smtp_password')
        if password:
            instance.smtp_password = password
        if commit:
            instance.save()
        return instance

class PopupForm(forms.ModelForm):
    saved_audience = forms.ModelChoiceField(
        queryset=SavedAudience.objects.none(),
        required=False,
        label='Audiencia Guardada',
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border-slate-200 p-2.5',
            'x-show': "audienceType === 'SAVED_AUDIENCE'",
            'x-cloak': True
        })
    )
    
    class Meta:
        model = Popup
        fields = ['title', 'content', 'priority', 'display_frequency', 'audience_type', 'audience_filter_value', 'saved_audience', 'target_client', 'start_date', 'end_date', 'is_active', 'image']
        widgets = {
             'title': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Título'}),
             'content': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'rows': 4, 'placeholder': 'Contenido HTML permitido...'}),
             'priority': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
             'display_frequency': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
             'audience_type': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'x-model': 'audienceType'}),
             'audience_filter_value': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'placeholder': 'Ej: nombre de etiqueta', 'x-show': "audienceType === 'CUSTOM_TAG'", 'x-cloak': True}),
             'target_client': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 p-2.5', 'x-show': "audienceType === 'ALL_ACTIVE' || audienceType === 'ALL_CLIENTS'", 'placeholder': 'Seleccionar Cliente (Opcional)'}), 
             'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
             'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full rounded-xl border-slate-200 p-2.5'}),
             'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500'}),
             'image': forms.FileInput(attrs={'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        self.fields['start_date'].required = False
        if gym:
            self.fields['saved_audience'].queryset = SavedAudience.objects.filter(gym=gym, is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        send_now = self.data.get('send_now') == 'on' or self.data.get('send_now') == 'true'
        start_date = cleaned_data.get('start_date')

        if not send_now and not start_date:
            self.add_error('start_date', 'La fecha de inicio es obligatoria si no se envía inmediatamente.')
        
        return cleaned_data


class AdvertisementForm(forms.ModelForm):
    """
    Formulario para crear/editar anuncios publicitarios (banners)
    """
    # Campo personalizado para target_screens con checkboxes
    target_screens = forms.MultipleChoiceField(
        choices=Advertisement.ScreenType.choices,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'rounded border-slate-300 text-purple-600 focus:ring-purple-500'
        }),
        required=False,
        label='Pantallas donde mostrar',
        help_text='Dejar vacío para mostrar en todas las pantallas'
    )
    
    saved_audience = forms.ModelChoiceField(
        queryset=SavedAudience.objects.none(),
        required=False,
        label='Audiencia Guardada',
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border-slate-200 p-2.5'
        })
    )
    
    class Meta:
        model = Advertisement
        fields = [
            'title', 'position', 'ad_type',
            'image_desktop', 'image_mobile', 'video_url',
            'cta_text', 'cta_action', 'cta_url',
            'target_gyms', 'audience_type', 'audience_filter_value', 'saved_audience',
            'target_screens', 'start_date', 'end_date',
            'priority', 'duration_seconds', 'is_collapsible', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 p-2.5',
                'placeholder': 'Ej: Black Friday 50% OFF'
            }),
            'position': forms.Select(attrs={
                'class': 'w-full rounded-xl border-slate-200 p-2.5'
            }),
            'ad_type': forms.Select(attrs={
                'class': 'w-full rounded-xl border-slate-200 p-2.5'
            }),
            'image_desktop': forms.FileInput(attrs={
                'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100',
                'accept': 'image/*'
            }),
            'image_mobile': forms.FileInput(attrs={
                'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100',
                'accept': 'image/*'
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 p-2.5',
                'placeholder': 'https://youtube.com/... (opcional)'
            }),
            'cta_text': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 p-2.5',
                'placeholder': '¡Reserva Ahora!'
            }),
            'cta_action': forms.Select(attrs={
                'class': 'w-full rounded-xl border-slate-200 p-2.5'
            }),
            'cta_url': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 p-2.5',
                'placeholder': 'URL o parámetro según la acción'
            }),
            'target_gyms': forms.CheckboxSelectMultiple(attrs={
                'class': 'rounded border-slate-300 text-purple-600 focus:ring-purple-500'
            }),
            'audience_type': forms.Select(attrs={
                'class': 'w-full rounded-xl border-slate-200 p-2.5'
            }),
            'audience_filter_value': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 p-2.5',
                'placeholder': 'Ej: nombre de etiqueta'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full rounded-xl border-slate-200 p-2.5'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full rounded-xl border-slate-200 p-2.5'
            }),
            'priority': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 p-2.5',
                'min': '1'
            }),
            'duration_seconds': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 p-2.5',
                'min': '1',
                'max': '30'
            }),
            'is_collapsible': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded border-slate-300 text-purple-600 focus:ring-purple-500'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded border-slate-300 text-purple-600 focus:ring-purple-500'
            }),
        }
        
        help_texts = {
            'title': 'Nombre interno del anuncio (no visible para clientes)',
            'image_desktop': 'Recomendado: 1080x600px para hero carousel, 1080x200px para footer',
            'image_mobile': 'Si está vacío, se usará image_desktop',
            'target_gyms': 'Selecciona los gimnasios. Vacío = todos',
            'audience_type': 'Segmenta por tipo de cliente',
            'end_date': 'Dejar vacío para anuncio indefinido',
        }
    
    def __init__(self, *args, **kwargs):
        # Extraer el usuario del request si se pasa
        self.user = kwargs.pop('user', None)
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        # start_date es requerido solo si no se marca "Activar Ahora"
        self.fields['start_date'].required = False
        self.fields['target_gyms'].required = False
        
        # Filtrar audiencias guardadas por gimnasio
        if gym:
            self.fields['saved_audience'].queryset = SavedAudience.objects.filter(gym=gym, is_active=True)
        
        # Filtrar target_gyms según permisos de franquicia
        if self.user:
            # Si el usuario NO es owner de franquicia ni superuser, solo puede ver su gimnasio
            if not self.user.franchises_owned.exists() and not self.user.is_superuser:
                # Obtener el gimnasio actual del usuario desde su perfil de staff
                from staff.models import StaffProfile
                staff_profile = StaffProfile.objects.filter(user=self.user, is_active=True).first()
                if staff_profile:
                    # Solo mostrar el gimnasio actual
                    from organizations.models import Gym
                    self.fields['target_gyms'].queryset = Gym.objects.filter(id=staff_profile.gym.id)
                    # Pre-seleccionar el gimnasio actual
                    if not self.instance.pk:
                        self.fields['target_gyms'].initial = [staff_profile.gym.id]
            else:
                # Es owner o superuser: mostrar todos los gimnasios de su franquicia
                from organizations.models import Gym
                if self.user.franchises_owned.exists():
                    franchise_ids = self.user.franchises_owned.values_list('id', flat=True)
                    self.fields['target_gyms'].queryset = Gym.objects.filter(franchise_id__in=franchise_ids)
                # Si es superuser, mostrar todos (queryset por defecto)
        
        # Inicializar target_screens desde el modelo si existe
        if self.instance and self.instance.pk:
            if self.instance.target_screens:
                self.fields['target_screens'].initial = self.instance.target_screens
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Guardar target_screens como lista
        target_screens_data = self.cleaned_data.get('target_screens', [])
        instance.target_screens = list(target_screens_data) if target_screens_data else []
        
        if commit:
            instance.save()
            # Necesario para guardar relaciones ManyToMany
            self.save_m2m()
        
        return instance
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que si hay CTA, tenga texto y acción
        cta_text = cleaned_data.get('cta_text')
        cta_action = cleaned_data.get('cta_action')
        
        if cta_text and not cta_action:
            self.add_error('cta_action', 'Debes seleccionar una acción si defines un texto de CTA')
        
        if cta_action and cta_action != 'NONE' and not cta_text:
            self.add_error('cta_text', 'Debes proporcionar un texto de CTA')
        
        # Validar fechas
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            self.add_error('end_date', 'La fecha de fin debe ser posterior a la fecha de inicio')
        
        return cleaned_data
