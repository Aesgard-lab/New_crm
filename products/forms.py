from django import forms
from .models import Product, ProductCategory, detect_barcode_type, validate_ean13, validate_ean8
from finance.models import TaxRate
from organizations.models import Gym

class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'code', 'parent', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'code': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]',
                'placeholder': 'Ej: BEB, SUP, ROA',
                'maxlength': '5'
            }),
            'parent': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        if gym:
            self.fields['parent'].queryset = ProductCategory.objects.filter(gym=gym)

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'barcode', 'barcode_type', 'sku', 'category', 'description', 'receipt_notes', 'image',
            'cost_price', 'supplier_name', 'supplier_reference',
            'base_price', 'tax_rate', 'additional_tax_rates', 'price_strategy',
            'track_stock', 'stock_quantity', 'low_stock_threshold',
            'is_active', 'is_visible_online'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'barcode': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]',
                'placeholder': 'Escanea o introduce el código EAN',
                'autocomplete': 'off',
                'data-barcode-input': 'true'
            }),
            'barcode_type': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'sku': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]',
                'placeholder': 'Auto-generado si se deja vacío'
            }),
            'category': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'description': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'rows': 3}),
            'receipt_notes': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'rows': 3, 'placeholder': 'Ej: Producto no retornable. Conservar en frío.'}),
            
            # Financials
            'cost_price': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'step': '0.01'}),
            'supplier_name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'supplier_reference': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
            'base_price': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200', 'step': '0.01'}),
            'tax_rate': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'additional_tax_rates': forms.CheckboxSelectMultiple(attrs={'class': 'space-y-1'}),
            'price_strategy': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
            # Stock
            'track_stock': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
            # Visibility
            'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'is_visible_online': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
        }
    
    def clean_barcode(self):
        """Validar código de barras."""
        barcode = self.cleaned_data.get('barcode', '').strip()
        
        if not barcode:
            return barcode
        
        # Detectar tipo
        detected_type = detect_barcode_type(barcode)
        
        # Validar EAN-13
        if detected_type == 'INVALID_EAN13':
            raise forms.ValidationError(
                'El código EAN-13 tiene un dígito de control incorrecto. '
                'Verifica que los 13 dígitos sean correctos.'
            )
        
        # Validar EAN-8
        if detected_type == 'INVALID_EAN8':
            raise forms.ValidationError(
                'El código EAN-8 tiene un dígito de control incorrecto. '
                'Verifica que los 8 dígitos sean correctos.'
            )
        
        # Verificar duplicados en el mismo gym
        gym = getattr(self, '_gym', None)
        if gym:
            existing = Product.objects.filter(gym=gym, barcode=barcode)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(
                    f'Ya existe un producto con este código de barras: {existing.first().name}'
                )
        
        return barcode

    propagate_to_gyms = forms.ModelMultipleChoiceField(
        queryset=Gym.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
        label="Propagar a otros gimnasios",
        help_text="Selecciona los gimnasios donde quieres copiar/actualizar este producto."
    )
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Guardar gym para validación de barcode
        self._gym = gym
        
        if gym:
            self.fields['category'].queryset = ProductCategory.objects.filter(gym=gym)
            tax_qs = TaxRate.objects.filter(gym=gym)
            self.fields['tax_rate'].queryset = tax_qs
            self.fields['additional_tax_rates'].queryset = tax_qs

            # Franchise Propagation Logic
            is_owner = user and gym.franchise and (user.is_superuser or user in gym.franchise.owners.all())
            
            if is_owner:
                franchise_gyms = gym.franchise.gyms.all()
                self.fields['propagate_to_gyms'].queryset = franchise_gyms
                
                # Pre-select gyms that already have this product (by name)
                if self.instance and self.instance.pk:
                    from products.models import Product
                    gyms_with_product = list(Product.objects.filter(
                        gym__in=franchise_gyms,
                        name=self.instance.name
                    ).exclude(gym=gym).values_list('gym_id', flat=True))
                    
                    if gyms_with_product:
                        self.initial['propagate_to_gyms'] = gyms_with_product
            else:
                del self.fields['propagate_to_gyms']
