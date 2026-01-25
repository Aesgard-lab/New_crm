# Generated migration for Refund model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sales', '0100_add_performance_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderRefund',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Cantidad Devuelta')),
                ('reason', models.CharField(blank=True, max_length=255, verbose_name='Motivo')),
                ('notes', models.TextField(blank=True, verbose_name='Notas internas')),
                ('status', models.CharField(choices=[('PENDING', 'Pendiente'), ('COMPLETED', 'Completado'), ('FAILED', 'Fallido')], default='PENDING', max_length=20, verbose_name='Estado')),
                ('gateway', models.CharField(choices=[('NONE', 'Manual'), ('STRIPE', 'Stripe'), ('REDSYS', 'Redsys')], default='NONE', max_length=20, verbose_name='Pasarela')),
                ('gateway_refund_id', models.CharField(blank=True, max_length=255, null=True, verbose_name='ID Reembolso Pasarela')),
                ('error_message', models.TextField(blank=True, verbose_name='Mensaje de Error')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='refunds', to='sales.order')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='refunds', to='sales.orderpayment')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_refunds', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Devolución',
                'verbose_name_plural': 'Devoluciones',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='order',
            name='total_refunded',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Total Devuelto'),
        ),
    ]
