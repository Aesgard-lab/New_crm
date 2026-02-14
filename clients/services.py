"""
Servicios de negocio para la gestión de clientes.

Esta capa encapsula la lógica de negocio, separándola de las vistas.
Proporciona una API limpia para operaciones con clientes.
"""
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from core.exception_handler import BusinessLogicError, ResourceNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class ClientCreateData:
    """Datos para crear un cliente."""
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    dni: Optional[str] = None
    birth_date: Optional[date] = None
    gender: str = "X"
    address: str = ""
    status: str = "LEAD"


@dataclass
class MembershipAssignData:
    """Datos para asignar una membresía."""
    plan_id: int
    start_date: date
    end_date: Optional[date] = None
    payment_method: str = "CASH"
    amount_paid: Optional[Decimal] = None


class ClientService:
    """
    Servicio para operaciones con clientes.
    
    Encapsula lógica de negocio y validaciones.
    """
    
    def __init__(self, gym):
        """
        Inicializa el servicio con un gimnasio.
        
        Args:
            gym: Instancia del modelo Gym
        """
        self.gym = gym
    
    def get_client(self, client_id: int):
        """
        Obtiene un cliente por ID.
        
        Args:
            client_id: ID del cliente
            
        Returns:
            Instancia de Client
            
        Raises:
            ResourceNotFoundError: Si el cliente no existe
        """
        from clients.models import Client
        
        try:
            return Client.objects.get(id=client_id, gym=self.gym)
        except Client.DoesNotExist:
            raise ResourceNotFoundError("Cliente", str(client_id))
    
    def list_clients(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        order_by: str = "-created_at",
    ) -> QuerySet:
        """
        Lista clientes con filtros opcionales.
        
        Args:
            status: Filtrar por estado (ACTIVE, INACTIVE, etc.)
            search: Búsqueda por nombre, email o DNI
            order_by: Campo de ordenación
            
        Returns:
            QuerySet de clientes
        """
        from clients.models import Client
        from django.db.models import Q
        
        qs = Client.objects.filter(gym=self.gym)
        
        if status:
            qs = qs.filter(status=status)
        
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(dni__icontains=search)
            )
        
        return qs.order_by(order_by)
    
    @transaction.atomic
    def create_client(self, data: ClientCreateData):
        """
        Crea un nuevo cliente.
        
        Args:
            data: Datos del cliente
            
        Returns:
            Instancia del cliente creado
            
        Raises:
            BusinessLogicError: Si hay errores de validación
        """
        from clients.models import Client
        
        # Validar email único en el gimnasio
        if data.email:
            if Client.objects.filter(gym=self.gym, email=data.email).exists():
                raise BusinessLogicError(
                    f"Ya existe un cliente con email '{data.email}' en este gimnasio",
                    code="DUPLICATE_EMAIL",
                )
        
        # Validar DNI único en el gimnasio
        if data.dni:
            if Client.objects.filter(gym=self.gym, dni=data.dni).exists():
                raise BusinessLogicError(
                    f"Ya existe un cliente con DNI '{data.dni}' en este gimnasio",
                    code="DUPLICATE_DNI",
                )
        
        client = Client.objects.create(
            gym=self.gym,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email or "",
            phone_number=data.phone_number or "",
            dni=data.dni or "",
            birth_date=data.birth_date,
            gender=data.gender,
            address=data.address,
            status=data.status,
        )
        
        logger.info(
            f"Cliente creado: {client.id} ({client.full_name})",
            extra={'client_id': client.id, 'gym_id': self.gym.id},
        )
        
        return client
    
    @transaction.atomic
    def update_client(self, client_id: int, **updates):
        """
        Actualiza un cliente.
        
        Args:
            client_id: ID del cliente
            **updates: Campos a actualizar
            
        Returns:
            Cliente actualizado
        """
        client = self.get_client(client_id)
        
        # Validar email único si se está cambiando
        if 'email' in updates and updates['email'] != client.email:
            from clients.models import Client
            if Client.objects.filter(
                gym=self.gym,
                email=updates['email']
            ).exclude(id=client_id).exists():
                raise BusinessLogicError(
                    f"Ya existe un cliente con email '{updates['email']}'",
                    code="DUPLICATE_EMAIL",
                )
        
        # Aplicar actualizaciones
        allowed_fields = {
            'first_name', 'last_name', 'email', 'phone_number',
            'dni', 'birth_date', 'gender', 'address', 'status',
        }
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(client, field, value)
        
        client.save()
        
        logger.info(
            f"Cliente actualizado: {client.id}",
            extra={'client_id': client.id, 'updates': list(updates.keys())},
        )
        
        return client
    
    def activate_client(self, client_id: int):
        """Activa un cliente."""
        return self.update_client(client_id, status="ACTIVE")
    
    def deactivate_client(self, client_id: int):
        """Desactiva un cliente."""
        return self.update_client(client_id, status="INACTIVE")
    
    @transaction.atomic
    def assign_membership(self, client_id: int, data: MembershipAssignData):
        """
        Asigna una membresía a un cliente.
        
        Args:
            client_id: ID del cliente
            data: Datos de la membresía
            
        Returns:
            Instancia de ClientMembership
        """
        from clients.models import ClientMembership
        from memberships.models import MembershipPlan
        
        client = self.get_client(client_id)
        
        # Obtener plan
        try:
            plan = MembershipPlan.objects.get(id=data.plan_id, gym=self.gym)
        except MembershipPlan.DoesNotExist:
            raise ResourceNotFoundError("Plan de membresía", str(data.plan_id))
        
        # Verificar si ya tiene membresía activa
        active_membership = ClientMembership.objects.filter(
            client=client,
            status="ACTIVE",
        ).first()
        
        if active_membership:
            raise BusinessLogicError(
                "El cliente ya tiene una membresía activa. "
                "Debe cancelarla o esperar a que expire.",
                code="ACTIVE_MEMBERSHIP_EXISTS",
            )
        
        # Calcular fecha de fin si no se proporciona
        end_date = data.end_date
        if not end_date:
            # Usar pack_validity_days o calcular desde frequency
            if plan.pack_validity_days:
                end_date = data.start_date + timedelta(days=plan.pack_validity_days)
            elif plan.frequency_unit == 'MONTH':
                end_date = data.start_date + timedelta(days=30 * plan.frequency_amount)
            elif plan.frequency_unit == 'YEAR':
                end_date = data.start_date + timedelta(days=365 * plan.frequency_amount)
            elif plan.frequency_unit == 'WEEK':
                end_date = data.start_date + timedelta(days=7 * plan.frequency_amount)
            else:  # DAY
                end_date = data.start_date + timedelta(days=plan.frequency_amount)
        
        # Determinar estado inicial según el modo de activación del plan
        initial_status = "ACTIVE"
        effective_start_date = data.start_date
        
        if plan.activation_mode == 'ON_FIRST_VISIT':
            # La membresía queda pendiente hasta la primera visita/check-in
            initial_status = "PENDING"
            effective_start_date = None  # Se establecerá en el primer check-in
            end_date = None  # Se calculará desde la primera visita
        elif plan.activation_mode == 'ON_SPECIFIC_DATE':
            # Si la fecha de inicio es futura, dejar como pendiente
            from django.utils import timezone
            if data.start_date > timezone.now().date():
                initial_status = "PENDING"
        
        # Crear membresía con todos los campos del plan
        membership = ClientMembership.objects.create(
            client=client,
            plan=plan,
            gym=self.gym,
            name=plan.name,
            price=plan.final_price,
            is_recurring=plan.is_recurring,
            start_date=effective_start_date or data.start_date,
            end_date=end_date,
            status=initial_status,
            current_period_start=effective_start_date or data.start_date if initial_status == 'ACTIVE' else None,
            current_period_end=end_date if initial_status == 'ACTIVE' else None,
            next_billing_date=end_date if initial_status == 'ACTIVE' and plan.is_recurring else None,
        )
        
        # Activar cliente si estaba como lead
        if client.status == "LEAD":
            client.status = "ACTIVE"
            client.save()
        
        logger.info(
            f"Membresía asignada: cliente={client.id}, plan={plan.name}",
            extra={'client_id': client.id, 'membership_id': membership.id},
        )
        
        return membership
    
    def get_active_membership(self, client_id: int):
        """
        Obtiene la membresía activa de un cliente.
        
        Returns:
            ClientMembership o None
        """
        from clients.models import ClientMembership
        
        client = self.get_client(client_id)
        
        return ClientMembership.objects.filter(
            client=client,
            status="ACTIVE",
        ).select_related('plan').first()
    
    def get_membership_history(self, client_id: int) -> QuerySet:
        """
        Obtiene el historial de membresías de un cliente.
        
        Returns:
            QuerySet de ClientMembership ordenado por fecha
        """
        from clients.models import ClientMembership
        
        client = self.get_client(client_id)
        
        return ClientMembership.objects.filter(
            client=client,
        ).select_related('plan').order_by('-start_date')
    
    def get_statistics(self, client_id: int) -> dict:
        """
        Obtiene estadísticas de un cliente.
        
        Returns:
            dict con estadísticas
        """
        from activities.models import ActivitySessionBooking
        
        client = self.get_client(client_id)
        
        # Reservas
        bookings = ActivitySessionBooking.objects.filter(client=client)
        total_bookings = bookings.count()
        attended = bookings.filter(status="ATTENDED").count()
        cancelled = bookings.filter(status="CANCELLED").count()
        no_show = bookings.filter(status="NO_SHOW").count()
        
        # Membresías
        memberships = client.memberships.all()
        total_memberships = memberships.count()
        
        # Calcular tasa de asistencia
        attendance_rate = 0
        if total_bookings > 0:
            attendance_rate = round((attended / total_bookings) * 100, 1)
        
        return {
            'total_bookings': total_bookings,
            'attended': attended,
            'cancelled': cancelled,
            'no_show': no_show,
            'attendance_rate': attendance_rate,
            'total_memberships': total_memberships,
            'member_since': client.created_at,
            'last_visit': client.last_app_access,
        }


class ClientBulkService:
    """
    Servicio para operaciones masivas con clientes.
    """
    
    def __init__(self, gym):
        self.gym = gym
        self.client_service = ClientService(gym)
    
    @transaction.atomic
    def bulk_update_status(self, client_ids: list, new_status: str) -> dict:
        """
        Actualiza el estado de múltiples clientes.
        
        Returns:
            dict con resultados {updated: int, errors: list}
        """
        from clients.models import Client
        
        valid_statuses = ["ACTIVE", "INACTIVE", "BLOCKED", "PAUSED"]
        if new_status not in valid_statuses:
            raise BusinessLogicError(
                f"Estado inválido. Debe ser uno de: {valid_statuses}",
                code="INVALID_STATUS",
            )
        
        updated = Client.objects.filter(
            id__in=client_ids,
            gym=self.gym,
        ).update(status=new_status)
        
        logger.info(
            f"Actualización masiva de estado: {updated} clientes → {new_status}",
            extra={'gym_id': self.gym.id, 'client_ids': client_ids},
        )
        
        return {'updated': updated, 'errors': []}
    
    def expire_memberships(self) -> int:
        """
        Expira membresías que han pasado su fecha de fin.
        
        Returns:
            Número de membresías expiradas
        """
        from clients.models import ClientMembership
        
        today = date.today()
        
        expired = ClientMembership.objects.filter(
            client__gym=self.gym,
            status="ACTIVE",
            end_date__lt=today,
        ).update(status="EXPIRED")
        
        if expired > 0:
            logger.info(
                f"Membresías expiradas automáticamente: {expired}",
                extra={'gym_id': self.gym.id, 'count': expired},
            )
        
        return expired
