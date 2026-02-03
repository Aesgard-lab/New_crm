from django import forms
from django.utils.text import slugify
from .models import Client, ClientNote, ClientDocument, ClientField, ClientFieldOption, ClientGroup, ClientTag, DocumentTemplate, ClientHealthRecord, ClientHealthDocument


class DocumentTemplateForm(forms.ModelForm):
    """Formulario para crear/editar plantillas de documentos"""
    class Meta:
        model = DocumentTemplate
        fields = ["name", "document_type", "content", "requires_signature", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder-slate-400",
                "placeholder": "Ej: Contrato de Adhesión 2026"
            }),
            "document_type": forms.Select(attrs={
                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            }),
            "content": forms.Textarea(attrs={
                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder-slate-400 min-h-[400px]",
                "rows": 20,
                "placeholder": "Contenido del documento en HTML...",
                "id": "template-content-editor"
            }),
            "requires_signature": forms.CheckboxInput(attrs={
                "class": "w-5 h-5 text-blue-600 bg-slate-100 border-slate-300 rounded focus:ring-blue-500"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "w-5 h-5 text-blue-600 bg-slate-100 border-slate-300 rounded focus:ring-blue-500"
            }),
        }
        labels = {
            "name": "Nombre de la Plantilla",
            "document_type": "Tipo de Documento",
            "content": "Contenido del Documento (HTML)",
            "requires_signature": "Requiere firma del cliente",
            "is_active": "Activo (disponible para enviar)",
        }
        help_texts = {
            "content": "Puedes usar HTML para dar formato. Variables disponibles: {{client_name}}, {{client_dni}}, {{date}}, {{gym_name}}",
        }

class ClientForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400",
            "placeholder": "Nueva contraseña (dejar en blanco para no cambiar)"
        }),
        help_text="Contraseña para el acceso del cliente al portal. Dejar en blanco para mantener la actual."
    )
    
    class Meta:
        model = Client
        fields = [
            "first_name", "last_name", "email", "phone_number", 
            "dni", "birth_date", "gender", "address", 
            "status", "photo", "access_code", "is_company_client", 
            "company_name", "company_tax_id", "company_address", "company_email", "use_company_data_in_invoices",
            "tags", "groups"
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "last_name": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "email": forms.EmailInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "phone_number": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "dni": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "birth_date": forms.DateInput(attrs={"type": "date", "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "gender": forms.Select(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900"}),
            "address": forms.Textarea(attrs={"rows": 2, "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "status": forms.Select(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900"}),
            "photo": forms.FileInput(attrs={"class": "w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-slate-50 file:text-slate-700 hover:file:bg-slate-100"}),
            "access_code": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400", "placeholder": "PIN de acceso"}),
            "is_company_client": forms.CheckboxInput(attrs={"class": "h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500", "x-model": "isCompany"}),
            "company_name": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400", "placeholder": "Razón Social de la empresa"}),
            "company_tax_id": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400", "placeholder": "Ej: B12345678"}),
            "company_address": forms.Textarea(attrs={"rows": 2, "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400", "placeholder": "Dirección fiscal completa"}),
            "company_email": forms.EmailInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400", "placeholder": "facturacion@empresa.com"}),
            "use_company_data_in_invoices": forms.CheckboxInput(attrs={"class": "h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"}),
            "tags": forms.CheckboxSelectMultiple(),
            "groups": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        self.gym = kwargs.pop("gym", None)
        super().__init__(*args, **kwargs)

        if not self.gym and getattr(self.instance, "gym", None):
            self.gym = self.instance.gym

        self._custom_fields = []
        self.custom_bound_fields = []

        if self.gym:
            self._custom_fields = list(
                ClientField.objects.filter(gym=self.gym, is_active=True)
                .prefetch_related("options")
                .order_by("name")
            )

            custom_field_names = []
            for field in self._custom_fields:
                field_name = f"cf_{field.slug}"

                if field.field_type == ClientField.FieldType.TOGGLE:
                    self.fields[field_name] = forms.BooleanField(
                        label=field.name,
                        required=False,
                        widget=forms.CheckboxInput(
                            attrs={
                                "class": "h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
                            }
                        ),
                    )
                    if self.instance and isinstance(self.instance.extra_data, dict):
                        self.fields[field_name].initial = bool(
                            self.instance.extra_data.get(field.slug, False)
                        )
                else:
                    choices = [("", f"Selecciona {field.name}")]
                    for option in field.options.all().order_by("order", "id"):
                        choices.append((option.value, option.label))

                    self.fields[field_name] = forms.ChoiceField(
                        label=field.name,
                        required=field.is_required,
                        choices=choices,
                        widget=forms.Select(
                            attrs={
                                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900"
                            }
                        ),
                    )

                    if self.instance and isinstance(self.instance.extra_data, dict):
                        self.fields[field_name].initial = self.instance.extra_data.get(field.slug, "")

                custom_field_names.append(field_name)

            self.custom_bound_fields = [self[name] for name in custom_field_names]

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Manejar contraseña si se proporcionó
        password = self.cleaned_data.get('password')
        if password:
            # Obtener o crear el usuario asociado
            if hasattr(instance, 'user') and instance.user:
                instance.user.set_password(password)
                if commit:
                    instance.user.save()
            else:
                # Si no tiene usuario, crearlo
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.create_user(
                    username=instance.email,
                    email=instance.email,
                    password=password,
                    first_name=instance.first_name,
                    last_name=instance.last_name,
                    is_staff=False,
                    is_active=True
                )
                instance.user = user

        extra_data = instance.extra_data if isinstance(instance.extra_data, dict) else {}
        for field in self._custom_fields:
            key = field.slug
            form_key = f"cf_{field.slug}"
            value = self.cleaned_data.get(form_key, "")

            if field.field_type == ClientField.FieldType.TOGGLE:
                extra_data[key] = bool(value)
            else:
                if value:
                    extra_data[key] = value
                elif key in extra_data:
                    extra_data.pop(key)

        instance.extra_data = extra_data

        if commit:
            instance.save()
            self.save_m2m()

        return instance


class ClientImportForm(forms.Form):
    """Formulario para importar clientes desde CSV"""
    csv_file = forms.FileField(
        label="Archivo CSV",
        help_text="Soporta Excel guardado como CSV. Máximo 10MB",
        widget=forms.FileInput(attrs={
            "accept": ".csv,.xlsx",
            "class": "w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
        })
    )
    
    update_existing = forms.BooleanField(
        label="Actualizar clientes existentes",
        required=False,
        initial=True,
        help_text="Si está marcado, actualiza clientes duplicados (detectados por email o DNI)",
        widget=forms.CheckboxInput(attrs={"class": "w-4 h-4 text-indigo-600"})
    )
    
    skip_errors = forms.BooleanField(
        label="Saltar filas con errores",
        required=False,
        initial=True,
        help_text="Si está marcado, continúa la importación aunque haya errores en algunas filas",
        widget=forms.CheckboxInput(attrs={"class": "w-4 h-4 text-indigo-600"})
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        
        if not csv_file:
            raise forms.ValidationError("Debes seleccionar un archivo CSV")
        
        # Verificar extensión
        if not csv_file.name.lower().endswith(('.csv', '.xlsx')):
            raise forms.ValidationError("Solo se aceptan archivos CSV o XLSX")
        
        # Verificar tamaño (10MB máximo)
        if csv_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("El archivo no debe superar 10MB")
        
        return csv_file


class ClientNoteForm(forms.ModelForm):
    class Meta:
        model = ClientNote
        fields = ["text", "type", "is_popup"]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 2, "placeholder": "Escribe una nota...", "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400 mb-2"}),
            "type": forms.Select(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 mb-2"}),
            "is_popup": forms.CheckboxInput(attrs={"class": "w-4 h-4 text-slate-900 bg-slate-100 border-slate-300 rounded focus:ring-slate-900"}),
        }


class ClientDocumentForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = [
            "name", "document_type", "file", "content", 
            "requires_signature", "expires_at", "membership_plan"
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder-slate-400",
                "placeholder": "Ej: Contrato de Adhesión 2026"
            }),
            "document_type": forms.Select(attrs={
                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            }),
            "file": forms.FileInput(attrs={
                "class": "w-full text-sm text-slate-600 file:mr-4 file:py-2.5 file:px-6 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100",
                "accept": ".pdf,.doc,.docx"
            }),
            "content": forms.Textarea(attrs={
                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder-slate-400",
                "rows": 8,
                "placeholder": "Contenido del documento en HTML o texto plano..."
            }),
            "requires_signature": forms.CheckboxInput(attrs={
                "class": "w-5 h-5 text-blue-600 bg-slate-100 border-slate-300 rounded focus:ring-blue-500"
            }),
            "expires_at": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            }),
            "membership_plan": forms.Select(attrs={
                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            }),
        }
        labels = {
            "name": "Nombre del Documento",
            "document_type": "Tipo de Documento",
            "file": "Archivo PDF/DOC (opcional)",
            "content": "Contenido del Documento (opcional)",
            "requires_signature": "¿Requiere firma del cliente?",
            "expires_at": "Fecha de Expiración (opcional)",
            "membership_plan": "Plan de Membresía Asociado (opcional)",
        }
        help_texts = {
            "file": "Si subes un archivo, el cliente podrá descargarlo. Si no, solo verá el contenido.",
            "content": "Puedes usar HTML para dar formato al texto. Se mostrará al cliente.",
        }


class ClientGroupForm(forms.ModelForm):
    class Meta:
        model = ClientGroup
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900",
                    "placeholder": "Empresas, Mañanas, Tarde...",
                }
            )
        }


class ClientTagForm(forms.ModelForm):
    class Meta:
        model = ClientTag
        fields = ["name", "color"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900",
                    "placeholder": "VIP, Moroso, Lesionado...",
                }
            ),
            "color": forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "h-10 w-16 rounded border-slate-200 bg-white",
                }
            ),
        }


class ClientFieldForm(forms.ModelForm):
    slug = forms.CharField(
        label="Identificador",
        widget=forms.TextInput(
            attrs={
                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900",
                "placeholder": "como_nos_ha_conocido",
            }
        ),
        help_text="Se autocompleta a partir del nombre. Puedes usar letras, números y guiones bajos.",
        required=False,
    )

    field_type = forms.ChoiceField(
        label="Tipo de campo",
        choices=ClientField.FieldType.choices,
        widget=forms.Select(
            attrs={
                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900"
            }
        ),
    )

    options_raw = forms.CharField(
        label="Opciones (una por línea)",
        widget=forms.Textarea(
            attrs={
                "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900",
                "rows": 4,
                "placeholder": "Ej:\nGoogle\nInstagram\nReferido",
            }
        ),
        help_text="Introduce las opciones que aparecerán en el selector (solo para selects).",
        required=False,
    )

    class Meta:
        model = ClientField
        fields = ["name", "slug", "field_type", "is_required", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900",
                    "placeholder": "Cómo nos ha conocido",
                }
            ),
            "is_required": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"}
            ),
        }

    def clean_slug(self):
        slug_value = self.cleaned_data.get("slug") or self.cleaned_data.get("name", "")
        slug_value = slugify(slug_value)
        if not slug_value:
            raise forms.ValidationError("Introduce un identificador para el campo")
        return slug_value

    def clean_options_raw(self):
        options_raw = self.cleaned_data.get("options_raw", "")
        field_type = self.cleaned_data.get("field_type")
        if field_type == ClientField.FieldType.SELECT and not options_raw.strip():
            raise forms.ValidationError("Añade al menos una opción para un campo de tipo selección")
        return options_raw

class ClientFieldOptionForm(forms.ModelForm):
    class Meta:
        model = ClientFieldOption
        fields = ['label', 'value', 'order']
        widgets = {
            'label': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]',
                'placeholder': 'Ej: Google'
            }),
            'value': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]',
                'placeholder': 'google'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)] focus:ring-[var(--brand-color)]',
                'min': '0'
            }),
        }


class ClientHealthRecordForm(forms.ModelForm):
    """Formulario para datos de salud del cliente"""
    class Meta:
        model = ClientHealthRecord
        fields = [
            'notes', 'has_medical_clearance', 'medical_clearance_date',
            'allergies', 'medical_conditions', 'medications',
            'emergency_contact_name', 'emergency_contact_phone'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500 placeholder-slate-400',
                'rows': 4,
                'placeholder': 'Notas generales sobre la salud del cliente...'
            }),
            'has_medical_clearance': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-rose-600 bg-slate-100 border-slate-300 rounded focus:ring-rose-500'
            }),
            'medical_clearance_date': forms.DateInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500',
                'type': 'date'
            }),
            'allergies': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500 placeholder-slate-400',
                'rows': 2,
                'placeholder': 'Ej: Alergia a frutos secos, látex...'
            }),
            'medical_conditions': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500 placeholder-slate-400',
                'rows': 2,
                'placeholder': 'Ej: Diabetes tipo 2, hipertensión...'
            }),
            'medications': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500 placeholder-slate-400',
                'rows': 2,
                'placeholder': 'Ej: Metformina 500mg, Losartan 50mg...'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500 placeholder-slate-400',
                'placeholder': 'Nombre completo del contacto'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500 placeholder-slate-400',
                'placeholder': '+34 666 123 456'
            }),
        }
        labels = {
            'notes': 'Notas de Salud',
            'has_medical_clearance': 'Tiene autorización médica',
            'medical_clearance_date': 'Fecha de autorización',
            'allergies': 'Alergias',
            'medical_conditions': 'Condiciones médicas',
            'medications': 'Medicamentos actuales',
            'emergency_contact_name': 'Contacto de emergencia',
            'emergency_contact_phone': 'Teléfono de emergencia',
        }


class ClientHealthDocumentForm(forms.ModelForm):
    """Formulario para subir documentos de salud"""
    class Meta:
        model = ClientHealthDocument
        fields = ['name', 'document_type', 'file', 'notes', 'document_date', 'expires_at']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500 placeholder-slate-400',
                'placeholder': 'Ej: Certificado médico Dr. García'
            }),
            'document_type': forms.Select(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500'
            }),
            'file': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-rose-50 file:text-rose-700 hover:file:bg-rose-100 transition-colors'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500 placeholder-slate-400',
                'rows': 2,
                'placeholder': 'Notas adicionales sobre el documento...'
            }),
            'document_date': forms.DateInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500',
                'type': 'date'
            }),
            'expires_at': forms.DateInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-rose-500',
                'type': 'date'
            }),
        }
        labels = {
            'name': 'Nombre del documento',
            'document_type': 'Tipo de documento',
            'file': 'Archivo',
            'notes': 'Notas',
            'document_date': 'Fecha del documento',
            'expires_at': 'Fecha de caducidad',
        }