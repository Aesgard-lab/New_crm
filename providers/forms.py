from django import forms
from django.forms import inlineformset_factory
from .models import Provider, PurchaseOrder, PurchaseOrderLine, ProviderItem


class ProviderForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = [
            "name",
            "logo",
            "legal_name",
            "tax_id",
            "email",
            "phone",
            "currency",
            "payment_terms_days",
            "early_payment_discount",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "country",
            "postal_code",
            "is_active",
            "is_blocked",
            "notes",
        ]
        labels = {
            "name": "Nombre",
            "logo": "Logo",
            "legal_name": "Razón social",
            "tax_id": "NIF/CIF",
            "email": "Email",
            "phone": "Teléfono",
            "currency": "Moneda",
            "payment_terms_days": "Días de pago",
            "early_payment_discount": "Descuento pronto pago",
            "address_line1": "Dirección línea 1",
            "address_line2": "Dirección línea 2",
            "city": "Ciudad",
            "state": "Provincia",
            "country": "País",
            "postal_code": "Código postal",
            "is_active": "Activo",
            "is_blocked": "Bloqueado",
            "notes": "Notas",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "legal_name": forms.TextInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "tax_id": forms.TextInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "email": forms.EmailInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "phone": forms.TextInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "currency": forms.Select(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "payment_terms_days": forms.NumberInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "early_payment_discount": forms.NumberInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]", "step": "0.01"}),
            "address_line1": forms.TextInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "address_line2": forms.TextInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "city": forms.TextInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "state": forms.TextInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "country": forms.TextInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "postal_code": forms.TextInput(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]"}),
            "is_active": forms.CheckboxInput(attrs={"class": "rounded border-slate-300 text-[var(--brand-color)] focus:ring-[var(--brand-color)]"}),
            "is_blocked": forms.CheckboxInput(attrs={"class": "rounded border-slate-300 text-red-600 focus:ring-red-500"}),
            "notes": forms.Textarea(attrs={"class": "w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-color)]", "rows": "4"}),
        }


class PurchaseOrderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        gym = kwargs.pop("gym", None)
        super().__init__(*args, **kwargs)
        if gym is not None:
            self.fields["provider"].queryset = Provider.objects.filter(gym=gym)

    class Meta:
        model = PurchaseOrder
        fields = [
            "provider",
            "reference",
            "status",
            "issue_date",
            "expected_date",
            "currency",
            "payment_terms_days",
            "notes",
        ]
        labels = {
            "provider": "Proveedor",
            "reference": "Referencia",
            "status": "Estado",
            "issue_date": "Fecha emisión",
            "expected_date": "Fecha esperada",
            "currency": "Moneda",
            "payment_terms_days": "Días de pago",
            "notes": "Notas",
        }
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}),
            "expected_date": forms.DateInput(attrs={"type": "date"}),
        }


class PurchaseOrderLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = [
            "provider_item",
            "product",
            "description",
            "quantity",
            "unit_price",
            "tax_rate",
            "tax_percent",
            "tax_amount",
            "total_line",
            "received_quantity",
        ]
        labels = {
            "provider_item": "Artículo proveedor",
            "product": "Producto",
            "description": "Descripción",
            "quantity": "Cantidad",
            "unit_price": "Precio unitario",
            "tax_rate": "Tipo IVA",
            "tax_percent": "% IVA",
            "tax_amount": "Importe IVA",
            "total_line": "Total línea",
            "received_quantity": "Cantidad recibida",
        }
        widgets = {
            "quantity": forms.NumberInput(attrs={"step": "0.01"}),
            "unit_price": forms.NumberInput(attrs={"step": "0.01"}),
            "tax_percent": forms.NumberInput(attrs={"step": "0.01"}),
            "tax_amount": forms.NumberInput(attrs={"step": "0.01"}),
            "total_line": forms.NumberInput(attrs={"step": "0.01"}),
            "received_quantity": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        gym = kwargs.pop("gym", None)
        provider = kwargs.pop("provider", None)
        super().__init__(*args, **kwargs)
        if provider:
            self.fields["provider_item"].queryset = ProviderItem.objects.filter(provider=provider)
        if gym:
            self.fields["product"].queryset = self.fields["product"].queryset.filter(gym=gym)


PurchaseOrderLineFormSet = inlineformset_factory(
    parent_model=PurchaseOrder,
    model=PurchaseOrderLine,
    form=PurchaseOrderLineForm,
    extra=1,
    can_delete=True,
)
