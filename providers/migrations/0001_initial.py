# Generated manually for providers app
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        ("accounts", "0001_initial"),
        ("finance", "0001_initial"),
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Provider",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("legal_name", models.CharField(blank=True, max_length=200)),
                ("tax_id", models.CharField(blank=True, max_length=50)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("currency", models.CharField(default="EUR", max_length=3)),
                ("payment_terms_days", models.PositiveSmallIntegerField(default=30)),
                ("early_payment_discount", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("address_line1", models.CharField(blank=True, max_length=200)),
                ("address_line2", models.CharField(blank=True, max_length=200)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(blank=True, max_length=50)),
                ("postal_code", models.CharField(blank=True, max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("is_blocked", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("gym", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="providers", to="organizations.gym")),
            ],
            options={"ordering": ["name"], "unique_together": {("gym", "name")}},
        ),
        migrations.CreateModel(
            name="PurchaseOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(blank=True, max_length=100)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Borrador"),
                            ("APPROVED", "Aprobada"),
                            ("SENT", "Enviada"),
                            ("PARTIAL", "Parcial"),
                            ("RECEIVED", "Recibida"),
                            ("INVOICED", "Facturada"),
                            ("CANCELED", "Cancelada"),
                        ],
                        default="DRAFT",
                        max_length=20,
                    ),
                ),
                ("issue_date", models.DateField(default=django.utils.timezone.now)),
                ("expected_date", models.DateField(blank=True, null=True)),
                ("currency", models.CharField(default="EUR", max_length=3)),
                ("payment_terms_days", models.PositiveSmallIntegerField(default=30)),
                ("subtotal", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("tax_total", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="accounts.user")),
                ("gym", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="purchase_orders", to="organizations.gym")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ProviderContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("role", models.CharField(blank=True, max_length=80)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contacts", to="providers.provider")),
            ],
            options={"ordering": ["-is_primary", "name"]},
        ),
        migrations.CreateModel(
            name="ProviderDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                (
                    "doc_type",
                    models.CharField(
                        choices=[
                            ("CONTRACT", "Contrato"),
                            ("CERT", "Certificado"),
                            ("INSURANCE", "Seguro"),
                            ("OTHER", "Otro"),
                        ],
                        default="OTHER",
                        max_length=20,
                    ),
                ),
                ("file", models.FileField(blank=True, null=True, upload_to="providers/documents/")),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="providers.provider")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ProviderRating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveSmallIntegerField(default=0)),
                ("otif_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("quality_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("issues_count", models.PositiveIntegerField(default=0)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ratings", to="providers.provider")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ProviderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku_provider", models.CharField(blank=True, max_length=100)),
                ("sku_internal", models.CharField(blank=True, max_length=100)),
                ("name", models.CharField(blank=True, max_length=200)),
                ("unit_cost", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("currency", models.CharField(default="EUR", max_length=3)),
                ("lead_time_days", models.PositiveIntegerField(default=0)),
                ("min_order_qty", models.PositiveIntegerField(default=1)),
                ("lot_size", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="provider_items", to="products.product")),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="providers.provider")),
            ],
            options={"ordering": ["provider", "product"], "unique_together": {("provider", "product")}},
        ),
        migrations.CreateModel(
            name="PurchaseOrderLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, max_length=255)),
                ("quantity", models.DecimalField(decimal_places=2, default=1, max_digits=10)),
                ("unit_price", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("tax_percent", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("tax_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total_line", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("received_quantity", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="purchase_order_lines", to="products.product")),
                ("provider_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="purchase_lines", to="providers.provideritem")),
                ("purchase_order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="providers.purchaseorder")),
                ("tax_rate", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="finance.taxrate")),
            ],
            options={"ordering": ["purchase_order", "id"]},
        ),
    ]
