from django.core.management.base import BaseCommand
from accounts.models_memberships import Permission


DEFAULT_PERMS = [
    ("dashboard.view", "Ver dashboard"),
    ("clients.view", "Ver clientes"),
    ("clients.create", "Crear clientes"),
    ("clients.edit", "Editar clientes"),
    ("staff.view", "Ver staff"),
    ("staff.manage", "Gestionar staff y permisos"),
    ("marketing.view", "Ver marketing"),
    ("marketing.create", "Crear campañas"),
]


class Command(BaseCommand):
    def handle(self, *args, **options):
        created = 0
        for code, label in DEFAULT_PERMS:
            obj, was_created = Permission.objects.get_or_create(code=code, defaults={"label": label})
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Permisos creados: {created}"))
