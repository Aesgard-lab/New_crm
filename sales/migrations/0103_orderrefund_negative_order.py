# Generated migration for negative_order field

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0102_orderrefund_refund_method_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderrefund',
            name='negative_order',
            field=models.ForeignKey(
                blank=True,
                help_text='Orden con importe negativo creada para esta devolución',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='refund_source',
                to='sales.order',
            ),
        ),
    ]
