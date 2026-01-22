from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0006_posdevice'),
    ]

    operations = [
        migrations.AddField(
            model_name='financesettings',
            name='allow_client_delete_card',
            field=models.BooleanField(default=False, help_text='Permitir que el cliente elimine sus tarjetas guardadas desde la app.'),
        ),
    ]
