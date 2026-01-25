# Generated migration for refund_method_name field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0101_add_refund_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderrefund',
            name='refund_method_name',
            field=models.CharField(
                blank=True, 
                help_text='Nombre del método usado para la devolución (manual)',
                max_length=100, 
                verbose_name='Método de Devolución'
            ),
        ),
    ]
