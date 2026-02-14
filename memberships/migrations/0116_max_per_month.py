from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('memberships', '0115_early_access_hours'),
    ]

    operations = [
        migrations.AddField(
            model_name='planaccessrule',
            name='max_per_month',
            field=models.PositiveIntegerField(
                default=0,
                help_text='0 = Sin límite mensual',
                verbose_name='Máx. reservas por mes',
            ),
        ),
    ]
