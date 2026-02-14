"""
Servicio de Políticas de Actividades

Este servicio centraliza toda la lógica de validación y aplicación de políticas
para reservas, cancelaciones, listas de espera y penalizaciones.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Tuple, Optional, Dict, Any, List
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q

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


class MembershipAccessService:
    """
    Servicio para verificar restricciones de acceso según la membresía del cliente.
    Verifica límites por día, semana, mes y reservas simultáneas.
    """
    
    @classmethod
    def get_access_rules_for_activity(cls, client, activity: Activity) -> List:
        """
        Obtiene las reglas de acceso aplicables para esta actividad
        según las membresías activas del cliente.
        """
        from clients.models import ClientMembership
        from memberships.models import PlanAccessRule
        
        # Obtener membresías activas del cliente
        today = timezone.now().date()
        active_memberships = ClientMembership.objects.filter(
            client=client,
            gym=activity.gym,
            status='ACTIVE',
            start_date__lte=today
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).select_related('plan')
        
        if not active_memberships.exists():
            return []
        
        # Buscar reglas que apliquen a esta actividad
        plan_ids = [m.plan_id for m in active_memberships]
        
        rules = PlanAccessRule.objects.filter(
            plan_id__in=plan_ids
        ).filter(
            # Regla específica para esta actividad
            Q(activity=activity) |
            # O regla para la categoría de esta actividad
            Q(activity_category=activity.category, activity__isnull=True) |
            # O regla genérica (sin actividad ni categoría = acceso a todo)
            Q(activity__isnull=True, activity_category__isnull=True, service__isnull=True, service_category__isnull=True)
        ).select_related('plan')
        
        return list(rules)
    
    @classmethod
    def get_early_access_hours(cls, client, activity: Activity) -> int:
        """
        Retorna las horas de acceso anticipado que tiene el cliente
        según la mejor PlanAccessRule de sus membresías activas.
        """
        rules = cls.get_access_rules_for_activity(client, activity)
        if not rules:
            return 0
        return max(r.early_access_hours for r in rules)
    
    @classmethod
    def check_booking_limits(cls, client, session: ActivitySession) -> PolicyValidationResult:
        """
        Verifica si el cliente cumple con los límites de reserva de su membresía.
        
        Verifica:
        - Límite por día
        - Límite por semana
        - Límite por ciclo/total
        - Reservas simultáneas
        - Ventana de reserva anticipada
        """
        activity = session.activity
        rules = cls.get_access_rules_for_activity(client, activity)
        
        if not rules:
            # Sin reglas = sin membresía válida o actividad no incluida
            return PolicyValidationResult(
                False,
                "Tu membresía no incluye acceso a esta actividad",
                {'requires_membership': True}
            )
        
        # Usar la regla más permisiva (la mejor para el cliente)
        # Ordenar por prioridad de reserva (mayor = mejor)
        rules = sorted(rules, key=lambda r: r.booking_priority, reverse=True)
        best_rule = rules[0]
        
        now = timezone.now()
        today = now.date()
        
        # === VERIFICAR LÍMITE DE USO (campo combinado) ===
        if best_rule.usage_limit > 0 and best_rule.usage_limit_period:
            session_date = session.start_datetime.date()
            
            if best_rule.usage_limit_period == 'PER_DAY':
                date_start = session_date
                date_end = session_date
                limit_label = "día"
                limit_type = "daily"
            elif best_rule.usage_limit_period == 'PER_WEEK':
                date_start = session_date - timedelta(days=session_date.weekday())
                date_end = date_start + timedelta(days=6)
                limit_label = "semana"
                limit_type = "weekly"
            elif best_rule.usage_limit_period == 'PER_MONTH':
                date_start = session_date.replace(day=1)
                if session_date.month == 12:
                    date_end = session_date.replace(year=session_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    date_end = session_date.replace(month=session_date.month + 1, day=1) - timedelta(days=1)
                limit_label = "mes"
                limit_type = "monthly"
            else:
                date_start = date_end = None
            
            if date_start is not None:
                bookings_count = ActivitySessionBooking.objects.filter(
                    client=client,
                    session__start_datetime__date__gte=date_start,
                    session__start_datetime__date__lte=date_end,
                    session__activity__gym=activity.gym,
                    status='CONFIRMED'
                ).count()
                
                if bookings_count >= best_rule.usage_limit:
                    return PolicyValidationResult(
                        False,
                        f"Has alcanzado el límite de {best_rule.usage_limit} reservas para este {limit_label}",
                        {'limit_type': limit_type, 'limit': best_rule.usage_limit, 'current': bookings_count}
                    )
        
        # === Fallback: verificar campos legacy max_per_day/week/month ===
        if best_rule.max_per_day > 0:
            session_date = session.start_datetime.date()
            bookings_today = ActivitySessionBooking.objects.filter(
                client=client,
                session__start_datetime__date=session_date,
                session__activity__gym=activity.gym,
                status='CONFIRMED'
            ).count()
            if bookings_today >= best_rule.max_per_day:
                return PolicyValidationResult(
                    False,
                    f"Has alcanzado el límite de {best_rule.max_per_day} reservas para este día",
                    {'limit_type': 'daily', 'limit': best_rule.max_per_day, 'current': bookings_today}
                )
        
        if best_rule.max_per_week > 0:
            session_date = session.start_datetime.date()
            week_start = session_date - timedelta(days=session_date.weekday())
            week_end = week_start + timedelta(days=6)
            bookings_week = ActivitySessionBooking.objects.filter(
                client=client,
                session__start_datetime__date__gte=week_start,
                session__start_datetime__date__lte=week_end,
                session__activity__gym=activity.gym,
                status='CONFIRMED'
            ).count()
            if bookings_week >= best_rule.max_per_week:
                return PolicyValidationResult(
                    False,
                    f"Has alcanzado el límite de {best_rule.max_per_week} reservas para esta semana",
                    {'limit_type': 'weekly', 'limit': best_rule.max_per_week, 'current': bookings_week}
                )
        
        if best_rule.max_per_month > 0:
            session_date = session.start_datetime.date()
            month_start = session_date.replace(day=1)
            if session_date.month == 12:
                month_end = session_date.replace(year=session_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = session_date.replace(month=session_date.month + 1, day=1) - timedelta(days=1)
            bookings_month = ActivitySessionBooking.objects.filter(
                client=client,
                session__start_datetime__date__gte=month_start,
                session__start_datetime__date__lte=month_end,
                session__activity__gym=activity.gym,
                status='CONFIRMED'
            ).count()
            if bookings_month >= best_rule.max_per_month:
                return PolicyValidationResult(
                    False,
                    f"Has alcanzado el límite de {best_rule.max_per_month} reservas para este mes",
                    {'limit_type': 'monthly', 'limit': best_rule.max_per_month, 'current': bookings_month}
                )
        
        # === VERIFICAR DÍAS CONSECUTIVOS ===
        if best_rule.no_consecutive_days:
            session_date = session.start_datetime.date()
            # Verificar si hay reservas el día anterior o el día siguiente
            day_before = session_date - timedelta(days=1)
            day_after = session_date + timedelta(days=1)
            
            has_adjacent = ActivitySessionBooking.objects.filter(
                client=client,
                session__activity__gym=activity.gym,
                status='CONFIRMED'
            ).filter(
                Q(session__start_datetime__date=day_before) |
                Q(session__start_datetime__date=day_after)
            ).exists()
            
            if has_adjacent:
                return PolicyValidationResult(
                    False,
                    "Tu plan no permite reservar en días consecutivos. Deja al menos un día de descanso entre sesiones.",
                    {'limit_type': 'no_consecutive'}
                )
        
        # === VERIFICAR RESERVAS SIMULTÁNEAS ===
        if best_rule.max_simultaneous > 0:
            future_bookings = ActivitySessionBooking.objects.filter(
                client=client,
                session__start_datetime__gt=now,
                session__activity__gym=activity.gym,
                status='CONFIRMED'
            ).count()
            
            if future_bookings >= best_rule.max_simultaneous:
                return PolicyValidationResult(
                    False,
                    f"Ya tienes {future_bookings} reservas futuras. Máximo permitido: {best_rule.max_simultaneous}",
                    {'limit_type': 'simultaneous', 'limit': best_rule.max_simultaneous, 'current': future_bookings}
                )
        
        # === VERIFICAR VENTANA DE RESERVA ANTICIPADA ===
        if best_rule.advance_booking_days > 0:
            max_date = today + timedelta(days=best_rule.advance_booking_days)
            if session.start_datetime.date() > max_date:
                return PolicyValidationResult(
                    False,
                    f"Solo puedes reservar hasta {best_rule.advance_booking_days} días en el futuro",
                    {'limit_type': 'advance_days', 'max_days': best_rule.advance_booking_days}
                )
        
        # === VERIFICAR FRANJA HORARIA ===
        if best_rule.access_time_start or best_rule.access_time_end:
            session_time = session.start_datetime.time()
            if best_rule.access_time_start and session_time < best_rule.access_time_start:
                return PolicyValidationResult(
                    False,
                    f"Tu plan solo permite reservar a partir de las {best_rule.access_time_start.strftime('%H:%M')}",
                    {'limit_type': 'access_time', 'allowed_from': str(best_rule.access_time_start)}
                )
            if best_rule.access_time_end and session_time >= best_rule.access_time_end:
                return PolicyValidationResult(
                    False,
                    f"Tu plan solo permite reservar antes de las {best_rule.access_time_end.strftime('%H:%M')}",
                    {'limit_type': 'access_time', 'allowed_until': str(best_rule.access_time_end)}
                )
        
        # === NOTA: scheduling_open_day fue migrado al sistema de early_access_hours ===
        # La apertura de reservas ahora se gestiona desde ActivityPolicy (ventana de reserva)
        # y PlanAccessRule.early_access_hours (privilegio de acceso anticipado por plan).
        
        # === VERIFICAR CANTIDAD TOTAL (BONOS) ===
        if best_rule.quantity > 0:
            from clients.models import ClientMembership
            
            # Obtener membresía activa con esta regla
            membership = ClientMembership.objects.filter(
                client=client,
                plan=best_rule.plan,
                status='ACTIVE'
            ).first()
            
            if membership:
                used_count = cls._count_used_sessions(client, best_rule, membership)
                
                if used_count >= best_rule.quantity:
                    period_label = dict(best_rule.PERIODS).get(best_rule.period, '')
                    return PolicyValidationResult(
                        False,
                        f"Has usado {used_count}/{best_rule.quantity} sesiones ({period_label})",
                        {'limit_type': 'quantity', 'limit': best_rule.quantity, 'used': used_count}
                    )
        
        # Todo OK
        return PolicyValidationResult(
            True,
            "Acceso permitido",
            {
                'rule_id': best_rule.id,
                'plan_name': best_rule.plan.name,
                'priority': best_rule.booking_priority
            }
        )
    
    @staticmethod
    def _count_used_sessions(client, rule, membership) -> int:
        """Cuenta las sesiones usadas según el período de la regla"""
        from clients.models import ClientMembership
        
        now = timezone.now()
        
        base_filter = {
            'client': client,
            'session__activity__gym': rule.plan.gym,
            'status': 'CONFIRMED'
        }
        
        # Filtrar por actividad/categoría si está especificada
        if rule.activity:
            base_filter['session__activity'] = rule.activity
        elif rule.activity_category:
            base_filter['session__activity__category'] = rule.activity_category
        
        if rule.period == 'TOTAL':
            # Total desde inicio de membresía
            base_filter['session__start_datetime__gte'] = membership.start_date
            if membership.end_date:
                base_filter['session__start_datetime__lte'] = membership.end_date
        
        elif rule.period == 'PER_CYCLE':
            # Calcular el ciclo actual basado en la frecuencia del plan
            plan = rule.plan
            cycle_start = MembershipAccessService._calculate_current_cycle_start(membership, plan)
            base_filter['session__start_datetime__gte'] = cycle_start
        
        elif rule.period == 'PER_DAY':
            base_filter['session__start_datetime__date'] = now.date()
        
        elif rule.period == 'PER_WEEK':
            week_start = now.date() - timedelta(days=now.weekday())
            base_filter['session__start_datetime__date__gte'] = week_start
        
        return ActivitySessionBooking.objects.filter(**base_filter).count()
    
    @staticmethod
    def _calculate_current_cycle_start(membership, plan):
        """Calcula el inicio del ciclo actual de la membresía"""
        from dateutil.relativedelta import relativedelta
        
        start = membership.start_date
        now = timezone.now().date()
        
        # Calcular duración del ciclo
        if plan.frequency_unit == 'DAY':
            delta = timedelta(days=plan.frequency_amount)
        elif plan.frequency_unit == 'WEEK':
            delta = timedelta(weeks=plan.frequency_amount)
        elif plan.frequency_unit == 'MONTH':
            delta = relativedelta(months=plan.frequency_amount)
        elif plan.frequency_unit == 'YEAR':
            delta = relativedelta(years=plan.frequency_amount)
        else:
            delta = relativedelta(months=1)
        
        # Encontrar el ciclo actual
        cycle_start = start
        while True:
            if hasattr(delta, 'days'):
                next_cycle = cycle_start + delta
            else:
                next_cycle = cycle_start + delta
            
            if next_cycle > now:
                break
            cycle_start = next_cycle
        
        return timezone.make_aware(datetime.combine(cycle_start, datetime.min.time()))


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
        #    La ActivityPolicy define CUÁNDO abre la reserva para todos.
        #    PlanAccessRule.early_access_hours otorga un PRIVILEGIO de acceso anticipado.
        if policy:
            booking_opens_at = cls._calculate_booking_open_time(session, policy)
            
            if booking_opens_at and now < booking_opens_at:
                # Verificar si el cliente tiene privilegio de acceso anticipado
                early_hours = MembershipAccessService.get_early_access_hours(
                    client, session.activity
                )
                adjusted_opens_at = booking_opens_at
                if early_hours > 0:
                    adjusted_opens_at = booking_opens_at - timedelta(hours=early_hours)
                
                if now < adjusted_opens_at:
                    time_until_open = adjusted_opens_at - now
                    if time_until_open.days > 0:
                        msg = f"Las reservas abren en {time_until_open.days} días"
                    else:
                        hours = time_until_open.seconds // 3600
                        minutes = (time_until_open.seconds % 3600) // 60
                        if hours > 0:
                            msg = f"Las reservas abren en {hours}h {minutes}min"
                        else:
                            msg = f"Las reservas abren en {minutes} minutos"
                    return PolicyValidationResult(
                        False,
                        msg,
                        {
                            'opens_at': adjusted_opens_at.isoformat(),
                            'general_opens_at': booking_opens_at.isoformat(),
                            'early_access_hours': early_hours,
                        }
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
        
        # 6. NUEVO: Verificar restricciones de membresía (límites por día/semana/etc)
        membership_check = MembershipAccessService.check_booking_limits(client, session)
        if not membership_check.success:
            return membership_check
        
        return PolicyValidationResult(
            True,
            "Reserva disponible",
            {
                'spots_available': capacity - confirmed_count if capacity else None,
                'policy_name': policy.name if policy else None,
                'plan_name': membership_check.data.get('plan_name'),
                'booking_priority': membership_check.data.get('priority', 0)
            }
        )
    
    @classmethod
    def _calculate_booking_open_time(cls, session: ActivitySession, policy: ActivityPolicy) -> Optional[datetime]:
        """
        Calcula cuándo se abre la reserva según el modo de política.
        Delega al método del modelo que ya soporta los 4 modos:
        OPEN, RELATIVE_START, FIXED_TIME, WEEKLY_FIXED.
        """
        return policy.get_booking_opens_at(session.start_datetime)
    
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
            # Promover al primero en la lista (VIPs primero, luego por orden de llegada)
            next_in_line = WaitlistEntry.objects.filter(
                session=session,
                status='WAITING'
            ).order_by('-is_vip', 'joined_at').first()
            
            if next_in_line:
                WaitlistPolicyService.promote_from_waitlist(next_in_line)


class WaitlistPolicyService:
    """
    Servicio para gestionar listas de espera.
    """
    
    @staticmethod
    def _is_client_vip(client, session: ActivitySession, policy: Optional[ActivityPolicy]) -> bool:
        """
        Determina si el cliente tiene prioridad VIP según la política de la actividad.
        
        Un cliente es VIP si:
        - Su membresía activa está en policy.vip_membership_plans, o
        - Pertenece a un grupo en policy.vip_groups
        """
        if not policy:
            return False
        
        # Verificar planes VIP
        if policy.vip_membership_plans.exists():
            from clients.models import ClientMembership
            today = timezone.now().date()
            has_vip_plan = ClientMembership.objects.filter(
                client=client,
                plan__in=policy.vip_membership_plans.all(),
                status='ACTIVE',
                start_date__lte=today,
            ).filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            ).exists()
            if has_vip_plan:
                return True
        
        # Verificar grupos VIP
        if policy.vip_groups.exists():
            client_group_ids = client.groups.values_list('id', flat=True)
            if policy.vip_groups.filter(id__in=client_group_ids).exists():
                return True
        
        return False
    
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
        
        # Determinar si el cliente es VIP según la política
        is_vip = cls._is_client_vip(client, session, policy)
        
        # Crear entrada en lista de espera
        entry = WaitlistEntry.objects.create(
            session=session,
            client=client,
            gym=session.gym,
            status='WAITING',
            is_vip=is_vip,
        )
        
        position = WaitlistEntry.objects.filter(
            session=session,
            status='WAITING',
            joined_at__lte=entry.joined_at
        ).exclude(
            # Los VIP que entraron después no cuentan para la posición visible
            is_vip=True, joined_at__gt=entry.joined_at
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
