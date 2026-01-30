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
    ("discounts.view", "Ver descuentos y promociones"),
    ("discounts.create", "Crear descuentos"),
    ("discounts.edit", "Editar descuentos"),
    ("discounts.delete", "Eliminar descuentos"),
    ("discounts.apply", "Aplicar descuentos en ventas"),
    ("providers.view", "Ver proveedores"),
    ("providers.manage", "Gestionar proveedores"),
    ("providers.purchase_orders.view", "Ver órdenes de compra"),
    ("providers.purchase_orders.manage", "Gestionar órdenes de compra"),
    # Vacaciones
    ("vacations.view", "Ver calendario de vacaciones"),
    ("vacations.request", "Solicitar vacaciones propias"),
    ("vacations.approve", "Aprobar/rechazar solicitudes de vacaciones"),
    ("vacations.manage_balances", "Gestionar balances de días"),
    ("vacations.settings", "Configurar política de vacaciones"),
    ("vacations.blocked_periods", "Gestionar períodos bloqueados"),
]


class Command(BaseCommand):
    def handle(self, *args, **options):
        created = 0
        for code, label in DEFAULT_PERMS:
            obj, was_created = Permission.objects.get_or_create(code=code, defaults={"label": label})
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Permisos creados: {created}"))
