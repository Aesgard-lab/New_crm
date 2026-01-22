from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0007_booking_policy_settings"),
        ("clients", "0009_chatroom_chatmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="is_company_client",
            field=models.BooleanField(
                default=False,
                help_text="Marca si el cliente pertenece a una empresa",
            ),
        ),
        migrations.CreateModel(
            name="ClientField",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=60)),
                (
                    "field_type",
                    models.CharField(
                        choices=[("SELECT", "Selección")],
                        default="SELECT",
                        max_length=20,
                    ),
                ),
                ("is_required", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "gym",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_fields",
                        to="organizations.gym",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
                "unique_together": {("gym", "slug")},
            },
        ),
        migrations.CreateModel(
            name="ClientFieldOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=120)),
                ("value", models.SlugField(max_length=80)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "field",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="options",
                        to="clients.clientfield",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "id"],
                "unique_together": {("field", "value")},
            },
        ),
    ]
