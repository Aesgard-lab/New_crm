"""
Plan Limits Validation Service.

Validates that gyms don't exceed their plan limits:
- Maximum members (active clients)
- Maximum staff users
- Maximum locations (for franchises)

Provides warnings and enforcement options.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import logging

from django.db.models import Count

from saas_billing.models import GymSubscription, SubscriptionPlan
from organizations.models import Gym

logger = logging.getLogger(__name__)


@dataclass
class LimitStatus:
    """Status of a plan limit."""
    limit_name: str
    current_value: int
    max_value: Optional[int]  # None = unlimited
    is_exceeded: bool
    is_near_limit: bool  # >80% of limit
    percentage_used: Decimal
    
    @property
    def is_unlimited(self) -> bool:
        return self.max_value is None


@dataclass
class GymLimitsReport:
    """Complete limits report for a gym."""
    gym_id: int
    gym_name: str
    plan_name: str
    members: LimitStatus
    staff: LimitStatus
    has_exceeded_limits: bool
    has_near_limits: bool


class PlanLimitsService:
    """
    Service for checking and enforcing plan limits.
    """
    
    NEAR_LIMIT_THRESHOLD = Decimal('80.0')  # Alert when usage >80%
    
    def check_limit(
        self, 
        current: int, 
        limit: Optional[int], 
        limit_name: str
    ) -> LimitStatus:
        """Check a single limit."""
        if limit is None:
            # Unlimited
            return LimitStatus(
                limit_name=limit_name,
                current_value=current,
                max_value=None,
                is_exceeded=False,
                is_near_limit=False,
                percentage_used=Decimal('0.0')
            )
        
        percentage = Decimal(current / limit * 100) if limit > 0 else Decimal('0.0')
        
        return LimitStatus(
            limit_name=limit_name,
            current_value=current,
            max_value=limit,
            is_exceeded=current > limit,
            is_near_limit=percentage >= self.NEAR_LIMIT_THRESHOLD and not current > limit,
            percentage_used=percentage.quantize(Decimal('0.1'))
        )
    
    def get_gym_limits(self, gym: Gym) -> Optional[GymLimitsReport]:
        """
        Get complete limits report for a gym.
        Returns None if gym has no subscription.
        """
        try:
            subscription = gym.subscription
        except GymSubscription.DoesNotExist:
            return None
        
        plan = subscription.plan
        
        # Count current usage
        from clients.models import Client
        from staff.models import StaffProfile
        
        active_members = Client.objects.filter(
            gym=gym, 
            status='ACTIVE'
        ).count()
        
        # Staff = StaffProfile entries for this gym
        staff_count = StaffProfile.objects.filter(
            gym=gym,
            is_active=True
        ).count()
        
        # Check limits
        members_status = self.check_limit(
            current=active_members,
            limit=plan.max_members,
            limit_name='members'
        )
        
        staff_status = self.check_limit(
            current=staff_count,
            limit=plan.max_staff,
            limit_name='staff'
        )
        
        return GymLimitsReport(
            gym_id=gym.id,
            gym_name=gym.name,
            plan_name=plan.name,
            members=members_status,
            staff=staff_status,
            has_exceeded_limits=members_status.is_exceeded or staff_status.is_exceeded,
            has_near_limits=members_status.is_near_limit or staff_status.is_near_limit
        )
    
    def validate_can_add_member(self, gym: Gym) -> tuple[bool, str]:
        """
        Check if a new member can be added to the gym.
        
        Returns:
            (can_add, message)
        """
        report = self.get_gym_limits(gym)
        
        if report is None:
            return False, "El gimnasio no tiene suscripción activa"
        
        if report.members.is_unlimited:
            return True, "OK"
        
        if report.members.is_exceeded:
            return False, f"Límite de socios excedido ({report.members.current_value}/{report.members.max_value})"
        
        # Check if adding one more would exceed
        if report.members.current_value + 1 > report.members.max_value:
            return False, f"No se pueden añadir más socios. Límite: {report.members.max_value}"
        
        return True, "OK"
    
    def validate_can_add_staff(self, gym: Gym) -> tuple[bool, str]:
        """
        Check if a new staff member can be added to the gym.
        
        Returns:
            (can_add, message)
        """
        report = self.get_gym_limits(gym)
        
        if report is None:
            return False, "El gimnasio no tiene suscripción activa"
        
        if report.staff.is_unlimited:
            return True, "OK"
        
        if report.staff.is_exceeded:
            return False, f"Límite de personal excedido ({report.staff.current_value}/{report.staff.max_value})"
        
        if report.staff.current_value + 1 > report.staff.max_value:
            return False, f"No se puede añadir más personal. Límite: {report.staff.max_value}"
        
        return True, "OK"
    
    def get_all_gyms_near_limits(self) -> list[GymLimitsReport]:
        """
        Get all gyms that are near or exceeding their limits.
        Useful for proactive upselling.
        """
        results = []
        
        gyms_with_subs = Gym.objects.filter(
            subscription__isnull=False
        ).select_related('subscription__plan')
        
        for gym in gyms_with_subs:
            report = self.get_gym_limits(gym)
            if report and (report.has_exceeded_limits or report.has_near_limits):
                results.append(report)
        
        return results
    
    def alert_gyms_near_limits(self) -> int:
        """
        Send alerts for gyms approaching their limits.
        Returns number of alerts sent.
        """
        from .alerts import alert_service
        
        near_limits = self.get_all_gyms_near_limits()
        
        if not near_limits:
            return 0
        
        # Group into exceeded vs near limit
        exceeded = [r for r in near_limits if r.has_exceeded_limits]
        approaching = [r for r in near_limits if r.has_near_limits and not r.has_exceeded_limits]
        
        if exceeded:
            exceeded_list = "\n".join([
                f"- {r.gym_name} ({r.plan_name}): "
                f"Socios {r.members.current_value}/{r.members.max_value or '∞'}, "
                f"Staff {r.staff.current_value}/{r.staff.max_value or '∞'}"
                for r in exceeded
            ])
            
            alert_service.send_alert(
                subject=f"{len(exceeded)} gimnasios exceden límites de plan",
                message=f"""
GIMNASIOS QUE EXCEDEN SUS LÍMITES

Estos gimnasios necesitan hacer upgrade o reducir uso:

{exceeded_list}

Acciones recomendadas:
1. Contactar para ofrecer upgrade
2. Revisar si hay abuso del sistema
""",
                level='critical'
            )
        
        if approaching:
            approaching_list = "\n".join([
                f"- {r.gym_name} ({r.plan_name}): "
                f"Socios al {r.members.percentage_used}%, "
                f"Staff al {r.staff.percentage_used}%"
                for r in approaching
            ])
            
            alert_service.send_alert(
                subject=f"{len(approaching)} gimnasios cerca del límite",
                message=f"""
GIMNASIOS ACERCÁNDOSE A SUS LÍMITES (>80%)

Oportunidad de upselling:

{approaching_list}

Considerar contactar para upgrade proactivo.
""",
                level='info'
            )
        
        return len(near_limits)


# Singleton instance
limits_service = PlanLimitsService()


# ==================== Decorators for enforcement ====================

def enforce_member_limit(view_func):
    """
    Decorator to enforce member limits on views that create clients.
    Use on views that create new Client objects.
    """
    from functools import wraps
    from django.http import JsonResponse
    from django.contrib import messages
    from django.shortcuts import redirect
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get gym from request (adjust based on your implementation)
        gym = getattr(request, 'current_gym', None)
        if not gym:
            gym_id = request.session.get('current_gym_id')
            if gym_id:
                try:
                    gym = Gym.objects.get(id=gym_id)
                except Gym.DoesNotExist:
                    pass
        
        if gym:
            can_add, message = limits_service.validate_can_add_member(gym)
            if not can_add:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': message,
                        'code': 'MEMBER_LIMIT_EXCEEDED'
                    }, status=403)
                else:
                    messages.error(request, message)
                    return redirect(request.META.get('HTTP_REFERER', '/'))
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def enforce_staff_limit(view_func):
    """
    Decorator to enforce staff limits on views that create staff users.
    """
    from functools import wraps
    from django.http import JsonResponse
    from django.contrib import messages
    from django.shortcuts import redirect
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        gym = getattr(request, 'current_gym', None)
        if not gym:
            gym_id = request.session.get('current_gym_id')
            if gym_id:
                try:
                    gym = Gym.objects.get(id=gym_id)
                except Gym.DoesNotExist:
                    pass
        
        if gym:
            can_add, message = limits_service.validate_can_add_staff(gym)
            if not can_add:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': message,
                        'code': 'STAFF_LIMIT_EXCEEDED'
                    }, status=403)
                else:
                    messages.error(request, message)
                    return redirect(request.META.get('HTTP_REFERER', '/'))
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
