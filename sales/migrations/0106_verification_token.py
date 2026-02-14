"""
Migration to add verification_token UUID to Order.
Three steps: add nullable field → populate existing rows → make unique + non-null.
"""
import uuid
from django.db import migrations, models


def populate_verification_tokens(apps, schema_editor):
    """Generate unique UUID for all existing orders one by one."""
    Order = apps.get_model('sales', 'Order')
    orders = Order.objects.filter(verification_token__isnull=True)
    for order in orders:
        order.verification_token = uuid.uuid4()
    Order.objects.bulk_update(orders, ['verification_token'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0105_receipt_notes'),
    ]

    operations = [
        # Step 1: Add field as nullable, NO default, NO unique
        migrations.AddField(
            model_name='order',
            name='verification_token',
            field=models.UUIDField(
                editable=False,
                help_text='Identificador único para el QR de verificación del recibo/factura',
                null=True,
                blank=True,
                verbose_name='Token de Verificación',
            ),
        ),
        # Step 2: Populate existing rows with unique UUIDs
        migrations.RunPython(populate_verification_tokens, migrations.RunPython.noop),
        # Step 3: Make non-null + unique + add default for future rows
        migrations.AlterField(
            model_name='order',
            name='verification_token',
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                db_index=True,
                help_text='Identificador único para el QR de verificación del recibo/factura',
                verbose_name='Token de Verificación',
            ),
        ),
    ]
