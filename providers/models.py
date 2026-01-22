from django.db import models
from django.utils import timezone
from organizations.models import Gym
from accounts.models import User
from finance.models import TaxRate
from products.models import Product


class Provider(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="providers")
    name = models.CharField(max_length=150)
    legal_name = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=3, default="EUR")
    payment_terms_days = models.PositiveSmallIntegerField(default=30)
    early_payment_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=50, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("gym", "name")

    def __str__(self):
        return self.name


class ProviderContact(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "name"]

    def __str__(self):
        return f"{self.name} ({self.provider.name})"


class ProviderDocument(models.Model):
    class DocumentType(models.TextChoices):
        CONTRACT = "CONTRACT", "Contrato"
        CERT = "CERT", "Certificado"
        INSURANCE = "INSURANCE", "Seguro"
        OTHER = "OTHER", "Otro"

    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(max_length=150)
    doc_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER)
    file = models.FileField(upload_to="providers/documents/", null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.provider.name})"


class ProviderRating(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="ratings")
    score = models.PositiveSmallIntegerField(default=0)
    otif_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    issues_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider.name} score {self.score}"


class ProviderItem(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="provider_items")
    sku_provider = models.CharField(max_length=100, blank=True)
    sku_internal = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=200, blank=True)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="EUR")
    lead_time_days = models.PositiveIntegerField(default=0)
    min_order_qty = models.PositiveIntegerField(default=1)
    lot_size = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "product"]
        unique_together = ("provider", "product")

    def __str__(self):
        return f"{self.provider.name} - {self.product.name}"


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        APPROVED = "APPROVED", "Aprobada"
        SENT = "SENT", "Enviada"
        PARTIAL = "PARTIAL", "Parcial"
        RECEIVED = "RECEIVED", "Recibida"
        INVOICED = "INVOICED", "Facturada"
        CANCELED = "CANCELED", "Cancelada"

    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="purchase_orders")
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="purchase_orders")
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    issue_date = models.DateField(default=timezone.now)
    expected_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="EUR")
    payment_terms_days = models.PositiveSmallIntegerField(default=30)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PO {self.id or ''} - {self.provider.name}"


class PurchaseOrderLine(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    provider_item = models.ForeignKey(ProviderItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_lines")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_order_lines")
    description = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.SET_NULL, null=True, blank=True)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_line = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["purchase_order", "id"]

    def __str__(self):
        return f"{self.description or (self.product.name if self.product else 'Línea')}"
