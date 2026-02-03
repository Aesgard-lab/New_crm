"""
Servicio de Políticas de Actividades

Este servicio centraliza toda la lógica de validación y aplicación de políticas
para reservas, cancelaciones, listas de espera y penalizaciones.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Tuple, Optional, Dict, Any
from django.utils import timezone
from django.db import transaction
from django.db.models import Count

from .models import (
    Activity, ActivitySession, ActivitySessionBooking,
    ActivityPolicy, WaitlistEntry
)


class PolicyValidationResult:
    """Resultado de una validación de política"""
    
    def __init__(self, success: bool, message: str = "", data: dict = None):
        self.success = success
        self.message = message
        self.data = data or {}
    
    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'message': self.message,
            **self.data
        }


class BookingPolicyService:
    """
    Servicio para validar y aplicar políticas de reservas.
    """
    
    @staticmethod
    def get_policy_for_session(session: ActivitySession) -> Optional[ActivityPolicy]:
        """Obtiene la política aplicable para una sesión"""
        activity = session.activity
        if activity.policy:
            return activity.policy
        # Si no tiene política asignada, buscar política por defecto del gym
        default_policy = ActivityPolicy.objects.filter(
            gym=session.gym,
            name__icontains='default'
        ).first()
        return default_policy
    
    @classmethod
    def can_book(cls, session: ActivitySession, client) -> PolicyValidationResult:
        """
        Valida si un cliente puede reservar una sesión según las políticas.
        
        Valida:
        - Sesión en el futuro
        - Ventana de reserva (no muy adelantado ni muy tarde)
        - Capacidad disponible
        - No tener reserva existente
        - Membresía activa (opcional según config)
        """
        now = timezone.now()
        policy = cls.get_policy_for_session(session)
        
        # 1. Verificar que la sesión está en el futuro
        if session.start_datetime <= now:
            return PolicyValidationResult(
                False, 
                "No se pueden reservar clases que ya han comenzado"
            )
        
        # 2. Verificar ventana de reserva según política
        if policy:
            booking_opens_at = cls._calculate_booking_open_time(session, policy)
            
            if booking_opens_at and now < booking_opens_at:
                time_until_open = booking_opens_at - now
                if time_until_open.days > 0:
                    msg = f"Las reservas abren en {time_until_open.days} días"
                else:
                    hours = time_until_open.seconds // 3600
                    msg = f"Las reservas abren en {hours} horas"
                return PolicyValidationResult(
                    False,
                    msg,
                    {'opens_at': booking_opens_at.isoformat()}
                )
        
        # 3. Verificar capacidad
        confirmed_count = ActivitySessionBooking.objects.filter(
            session=session,
            status='CONFIRMED'
        ).count()
        
        capacity = session.max_capacity or session.activity.base_capacity
        if capacity and confirmed_count >= capacity:
            # Verificar si hay lista de espera
            if policy and policy.waitlist_enabled:
                return PolicyValidationResult(
                    False,
                    "Clase completa. Puedes unirte a la lista de espera.",
                    {'waitlist_available': True, 'position': cls._get_waitlist_position(session)}
                )
            return PolicyValidationResult(False, "Clase completa")
        
        # 4. Verificar reserva existente
        existing = ActivitySessionBooking.objects.filter(
            session=session,
            client=client,
            status__in=['CONFIRMED', 'PENDING']
        ).exists()
        
        if existing:
            return PolicyValidationResult(
                False,
                "Ya tienes una reserva para esta clase"
            )
        
        # 5. Verificar si está en lista de espera
        in_waitlist = WaitlistEntry.objects.filter(
            session=session,
            client=client,
            status='WAITING'
        ).exists()
        
        if in_waitlist:
            return PolicyValidationResult(
                False,
                "Ya estás en la lista de espera para esta clase"
            )
        
        return PolicyValidationResult(
            True,
            "Reserva disponible",
            {
                'spots_available': capacity - confirmed_count if capacity else None,
                'policy_name': policy.name if policy else None
            }
        )
    
    @classmethod
    def _calculate_booking_open_time(cls, session: ActivitySession, policy: ActivityPolicy) -> Optional[datetime]:
        """Calcula cuándo se abre la reserva según el modo de política"""
        if policy.booking_window_mode == 'RELATIVE_START':
            # X horas antes del inicio
            return session.start_datetime - timedelta(hours=policy.booking_window_value)
        
        elif policy.booking_window_mode == 'FIXED_TIME':
            # X días antes a hora fija
            session_date = session.start_datetime.date()
            open_date = session_date - timedelta(days=policy.booking_window_value)
            open_time = policy.booking_time_release or datetime.min.time()
            return timezone.make_aware(datetime.combine(open_date, open_time))
        
        return None
    
    @staticmethod
    def _get_waitlist_position(session: ActivitySession) -> int:
        """Obtiene la posición en lista de espera"""
        return WaitlistEntry.objects.filter(
            session=session,
            status='WAITING'
        ).count() + 1


class CancellationPolicyService:
    """
    Servicio para validar y aplicar políticas de cancelación.
    """
    
    @classmethod
    def can_cancel(cls, booking: ActivitySessionBooking) -> PolicyValidationResult:
        """
        Valida si una reserva puede cancelarse y qué penalización aplica.
        
        Returns:
            PolicyValidationResult con información sobre:
            - Si puede cancelar
            - Si hay penalización
            - Tipo y monto de penalización
        """
        now = timezone.now()
        session = booking.session
        policy = BookingPolicyService.get_policy_for_session(session)
        
        # Verificar que la sesión no haya pasado
        if session.start_datetime <= now:
            return PolicyValidationResult(
                False,
                "No se pueden cancelar clases que ya han comenzado"
            )
        
        # Verificar estado de la reserva
        if booking.status == 'CANCELLED':
            return PolicyValidationResult(
                False,
                "Esta reserva ya está cancelada"
            )
        
        # Calcular si está dentro de la ventana de penalización
        time_until_class = session.start_datetime - now
        hours_until_class = time_until_class.total_seconds() / 3600
        
        cancellation_window = policy.cancellation_window_hours if policy else 2
        
        if hours_until_class >= cancellation_window:
            # Cancelación sin penalización
            return PolicyValidationResult(
                True,
                "Puedes cancelar sin penalización",
                {
                    'has_penalty': False,
                    'hours_until_class': round(hours_until_class, 1)
                }
            )
        else:
            # Cancelación con penalización
            penalty_info = cls._get_penalty_info(policy)
            
            return PolicyValidationResult(
                True,  # Puede cancelar, pero con penalización
                f"Cancelación tardía. Se aplicará: {penalty_info['description']}",
                {
                    'has_penalty': True,
                    'penalty_type': penalty_info['type'],
                    'penalty_amount': penalty_info.get('amount'),
                    'penalty_description': penalty_info['description'],
                    'hours_until_class': round(hours_until_class, 1),
                    'window_hours': cancellation_window
                }
            )
    
    @staticmethod
    def _get_penalty_info(policy: Optional[ActivityPolicy]) -> Dict[str, Any]:
        """Obtiene información de la penalización"""
        if not policy:
            return {
                'type': 'FORFEIT',
                'description': 'Pérdida de crédito de clase'
            }
        
        if policy.penalty_type == 'STRIKE':
            return {
                'type': 'STRIKE',
                'description': 'Se registrará una falta (strike)'
            }
        elif policy.penalty_type == 'FEE':
            amount = policy.fee_amount or Decimal('0.00')
            return {
                'type': 'FEE',
                'amount': float(amount),
                'description': f'Cobro de {amount}€'
            }
        else:  # FORFEIT
            return {
                'type': 'FORFEIT',
                'description': 'Pérdida de crédito de clase'
            }
    
    @classmethod
    @transaction.atomic
    def execute_cancellation(cls, booking: ActivitySessionBooking, cancelled_by=None) -> PolicyValidationResult:
        """
        Ejecuta la cancelación aplicando penalizaciones si corresponde.
        
        Args:
            booking: La reserva a cancelar
            cancelled_by: Usuario que cancela (staff o cliente)
        
        Returns:
            PolicyValidationResult con el resultado
        """
        from clients.models import ClientPenalty  # Import local para evitar circular
        
        validation = cls.can_cancel(booking)
        if not validation.success:
            return validation
        
        session = booking.session
        client = booking.client
        policy = BookingPolicyService.get_policy_for_session(session)
        
        # Actualizar el estado de la reserva
        if validation.data.get('has_penalty'):
            booking.attendance_status = 'LATE_CANCEL'
        booking.status = 'CANCELLED'
        booking.save()
        
        # Aplicar penalización si corresponde
        penalty_applied = None
        if validation.data.get('has_penalty'):
            penalty_type = validation.data.get('penalty_type')
            
            try:
                if penalty_type == 'STRIKE':
                    penalty_applied = ClientPenalty.objects.create(
                        client=client,
                        gym=session.gym,
                        penalty_type='STRIKE',
                        reason=f"Cancelación tardía: {session.activity.name} - {session.start_datetime.strftime('%d/%m/%Y %H:%M')}",
                        session=session,
                        created_by=cancelled_by
                    )
                
                elif penalty_type == 'FEE':
                    amount = validation.data.get('penalty_amount', 0)
                    penalty_applied = ClientPenalty.objects.create(
                        client=client,
                        gym=session.gym,
                        penalty_type='FEE',
                        amount=Decimal(str(amount)),
                        reason=f"Multa por cancelación tardía: {session.activity.name}",
                        session=session,
                        created_by=cancelled_by
                    )
                    # TODO: Crear cargo pendiente en finanzas
                
                elif penalty_type == 'FORFEIT':
                    penalty_applied = ClientPenalty.objects.create(
                        client=client,
                        gym=session.gym,
                        penalty_type='FORFEIT',
                        reason=f"Pérdida de crédito: {session.activity.name}",
                        session=session,
                        created_by=cancelled_by
                    )
                    # TODO: Descontar crédito de membresía si aplica
            
            except Exception:
                # Si el modelo ClientPenalty no existe, solo loguear
                pass
        
        # Procesar lista de espera si hay alguien esperando
        cls._process_waitlist_promotion(session, policy)
        
        return PolicyValidationResult(
            True,
            "Reserva cancelada correctamente",
            {
                'penalty_applied': validation.data.get('has_penalty', False),
                'penalty_type': validation.data.get('penalty_type'),
                'penalty_id': penalty_applied.id if penalty_applied else None
            }
        )
    
    @staticmethod
    def _process_waitlist_promotion(session: ActivitySession, policy: Optional[ActivityPolicy]):
        """Promueve a alguien de la lista de espera si aplica"""
        if not policy or not policy.waitlist_enabled:
            return
        
        # Verificar si estamos dentro del cutoff de auto-promoción
        now = timezone.now()
        hours_until = (session.start_datetime - now).total_seconds() / 3600
        
        if hours_until < policy.auto_promote_cutoff_hours:
            # Ya no hay auto-promoción, se manejará manualmente o por broadcast
            return
        
        if policy.waitlist_mode == 'AUTO_PROMOTE':
            # Promover al primero en la lista
            next_in_line = WaitlistEntry.objects.filter(
                session=session,
                status='WAITING'
            ).order_by('joined_at').first()
            
            if next_in_line:
                WaitlistPolicyService.promote_from_waitlist(next_in_line)


class WaitlistPolicyService:
    """
    Servicio para gestionar listas de espera.
    """
    
    @classmethod
    def join_waitlist(cls, session: ActivitySession, client) -> PolicyValidationResult:
        """Añade un cliente a la lista de espera"""
        policy = BookingPolicyService.get_policy_for_session(session)
        
        if not policy or not policy.waitlist_enabled:
            return PolicyValidationResult(
                False,
                "La lista de espera no está habilitada para esta actividad"
            )
        
        # Verificar límite
        current_count = WaitlistEntry.objects.filter(
            session=session,
            status='WAITING'
        ).count()
        
        if policy.waitlist_limit > 0 and current_count >= policy.waitlist_limit:
            return PolicyValidationResult(
                False,
                f"La lista de espera está llena (máx. {policy.waitlist_limit})"
            )
        
        # Verificar que no esté ya en la lista
        existing = WaitlistEntry.objects.filter(
            session=session,
            client=client,
            status='WAITING'
        ).exists()
        
        if existing:
            return PolicyValidationResult(
                False,
                "Ya estás en la lista de espera"
            )
        
        # Verificar que no tenga reserva
        has_booking = ActivitySessionBooking.objects.filter(
            session=session,
            client=client,
            status='CONFIRMED'
        ).exists()
        
        if has_booking:
            return PolicyValidationResult(
                False,
                "Ya tienes una reserva confirmada para esta clase"
            )
        
        # Crear entrada en lista de espera
        entry = WaitlistEntry.objects.create(
            session=session,
            client=client,
            status='WAITING'
        )
        
        position = WaitlistEntry.objects.filter(
            session=session,
            status='WAITING',
            joined_at__lte=entry.joined_at
        ).count()
        
        return PolicyValidationResult(
            True,
            f"Añadido a la lista de espera en posición #{position}",
            {
                'entry_id': entry.id,
                'position': position
            }
        )
    
    @classmethod
    @transaction.atomic
    def promote_from_waitlist(cls, entry: WaitlistEntry) -> PolicyValidationResult:
        """Promueve una entrada de lista de espera a reserva confirmada"""
        session = entry.session
        client = entry.client
        
        # Verificar que aún hay espacio
        confirmed_count = ActivitySessionBooking.objects.filter(
            session=session,
            status='CONFIRMED'
        ).count()
        
        capacity = session.max_capacity or session.activity.base_capacity
        if capacity and confirmed_count >= capacity:
            return PolicyValidationResult(
                False,
                "No hay espacio disponible"
            )
        
        # Crear la reserva
        booking = ActivitySessionBooking.objects.create(
            session=session,
            client=client,
            status='CONFIRMED'
        )
        
        # Actualizar entrada de waitlist
        entry.status = 'PROMOTED'
        entry.promoted_at = timezone.now()
        entry.save()
        
        # TODO: Enviar notificación al cliente
        
        return PolicyValidationResult(
            True,
            "Promovido desde lista de espera",
            {
                'booking_id': booking.id,
                'entry_id': entry.id
            }
        )
    
    @classmethod
    def leave_waitlist(cls, entry: WaitlistEntry) -> PolicyValidationResult:
        """Salir de la lista de espera"""
        if entry.status != 'WAITING':
            return PolicyValidationResult(
                False,
                "Esta entrada ya no está activa"
            )
        
        entry.status = 'CANCELLED'
        entry.save()
        
        return PolicyValidationResult(
            True,
            "Has salido de la lista de espera"
        )


class NoShowPolicyService:
    """
    Servicio para gestionar no-shows y sus penalizaciones.
    """
    
    @classmethod
    def process_no_show(cls, booking: ActivitySessionBooking, marked_by=None) -> PolicyValidationResult:
        """
        Procesa un no-show aplicando la penalización correspondiente.
        """
        from clients.models import ClientPenalty
        
        session = booking.session
        client = booking.client
        policy = BookingPolicyService.get_policy_for_session(session)
        
        # Marcar como no-show
        booking.attendance_status = 'NO_SHOW'
        booking.attended = False
        booking.marked_by = marked_by
        booking.marked_at = timezone.now()
        booking.save()
        
        # Aplicar penalización (similar a cancelación tardía)
        penalty_info = CancellationPolicyService._get_penalty_info(policy)
        
        try:
            penalty = ClientPenalty.objects.create(
                client=client,
                gym=session.gym,
                penalty_type=penalty_info['type'],
                amount=Decimal(str(penalty_info.get('amount', 0))) if penalty_info.get('amount') else None,
                reason=f"No-show: {session.activity.name} - {session.start_datetime.strftime('%d/%m/%Y %H:%M')}",
                session=session,
                created_by=marked_by
            )
            
            return PolicyValidationResult(
                True,
                f"No-show registrado. {penalty_info['description']}",
                {'penalty_id': penalty.id}
            )
        except Exception:
            return PolicyValidationResult(
                True,
                "No-show registrado",
                {'penalty_applied': False}
            )
