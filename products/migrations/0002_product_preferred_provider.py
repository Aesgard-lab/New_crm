from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
        ("providers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="preferred_provider",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="preferred_products",
                to="providers.provider",
                verbose_name="Proveedor preferente",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="preferred_provider_item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="preferred_products",
                to="providers.provideritem",
                verbose_name="Artículo proveedor preferente",
            ),
        ),
    ]
