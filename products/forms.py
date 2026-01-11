from django import forms
from .models import Product, ProductCategory
from finance.models import TaxRate

class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'parent', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
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
            'name', 'sku', 'category', 'description', 'image',
            'cost_price', 'supplier_name', 'supplier_reference',
            'base_price', 'tax_rate', 'price_strategy',
            'track_stock', 'stock_quantity', 'low_stock_threshold',
            'is_active', 'is_visible_online'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'sku': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'placeholder': 'EAN / Código Barras'}),
            'category': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]'}),
            'description': forms.Textarea(attrs={'class': 'w-full rounded-xl border-slate-200 focus:border-[var(--brand-color)]', 'rows': 3}),
            
            # Financials
            'cost_price': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'supplier_name': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'supplier_reference': forms.TextInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
            'base_price': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'tax_rate': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'price_strategy': forms.Select(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
            # Stock
            'track_stock': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'w-full rounded-xl border-slate-200'}),
            
            # Visibility
            'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
            'is_visible_online': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]'}),
        }
    
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop('gym', None)
        super().__init__(*args, **kwargs)
        if gym:
            self.fields['category'].queryset = ProductCategory.objects.filter(gym=gym)
            self.fields['tax_rate'].queryset = TaxRate.objects.filter(gym=gym)
