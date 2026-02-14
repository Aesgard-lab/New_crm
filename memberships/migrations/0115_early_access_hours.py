"""
Añade early_access_hours a PlanAccessRule.

Este campo permite que ciertos planes de membresía otorguen un privilegio
de acceso anticipado a la reserva de actividades. Por ejemplo, si una
actividad abre reservas 48h antes y un plan tiene early_access_hours=24,
los clientes con ese plan pueden reservar 72h antes.

Reemplaza al antiguo scheduling_open_day como mecanismo de control de apertura.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('memberships', '0114_additional_tax_rates'),
    ]

    operations = [
        migrations.AddField(
            model_name='planaccessrule',
            name='early_access_hours',
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    'Horas antes de la apertura normal en que este plan puede reservar. '
                    'Ej: si la actividad abre reservas 48h antes y este campo es 24, '
                    'los clientes con este plan pueden reservar 72h antes.'
                ),
                verbose_name='Horas de acceso anticipado',
            ),
        ),
    ]
