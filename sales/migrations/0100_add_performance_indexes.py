"""
Migracion de indices para sales (ordenes y pagos).
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('sales', '0003_gateway_strategy'),  # Última migración antes de ésta
    ]
    
    operations = [
        # ==================== ORDER INDEXES ====================
        # Indice principal para listado: gym + status + fecha
        migrations.AddIndex(
            model_name='order',
            index=models.Index(
                fields=['gym', 'status', '-created_at'],
                name='order_gym_status_date_idx'
            ),
        ),
        # Indice para ordenes por cliente
        migrations.AddIndex(
            model_name='order',
            index=models.Index(
                fields=['client', '-created_at'],
                name='order_client_date_idx'
            ),
        ),
        # Indice para ordenes por sesion de caja
        migrations.AddIndex(
            model_name='order',
            index=models.Index(
                fields=['session', 'status'],
                name='order_cashsession_idx'
            ),
        ),
        # Indice para facturas
        migrations.AddIndex(
            model_name='order',
            index=models.Index(
                fields=['invoice_number'],
                name='order_invoice_idx'
            ),
        ),
    ]
