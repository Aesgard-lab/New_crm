from organizations.models import Gym
from .models import GymSubscription, SubscriptionPlan
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

class MigrationService:
    """
    Service to handle system initialization and migration of legacy data
    to the new billing system.
    """
    
    @staticmethod
    def get_system_status():
        """
        Get counts of gyms and subscription status.
        """
        total_gyms = Gym.objects.count()
        subscribed_gyms = GymSubscription.objects.count()
        orphan_gyms_count = total_gyms - subscribed_gyms
        
        # Determine health
        status = 'HEALTHY'
        if orphan_gyms_count > 0:
            status = 'WARNING'
            
        return {
            'total_gyms': total_gyms,
            'subscribed_gyms': subscribed_gyms,
            'orphan_gyms_count': orphan_gyms_count,
            'status': status
        }
        
    @staticmethod
    def get_orphan_gyms():
        """
        Get list of gyms without a subscription.
        """
        return Gym.objects.filter(subscription__isnull=True)

    @staticmethod
    def initialize_default_plans():
        """
        Create default plans if they don't exist.
        """
        plans_created = []
        
        # Basic Plan
        basic, created = SubscriptionPlan.objects.get_or_create(
            name='Básico',
            defaults={
                'description': 'Plan esencial para pequeños gimnasios',
                'price_monthly': 29.99,
                'max_members': 100,
                'module_pos': True,
                'module_calendar': True,
                'module_marketing': False,
                'is_demo': False
            }
        )
        if created: plans_created.append(basic.name)
        
        # Pro Plan
        pro, created = SubscriptionPlan.objects.get_or_create(
            name='Pro',
            defaults={
                'description': 'Todo incluido para gimnasios en crecimiento',
                'price_monthly': 59.99,
                'max_members': None, # Unlimited
                'module_pos': True,
                'module_calendar': True,
                'module_marketing': True,
                'module_reporting': True,
                'module_automations': True,
                'is_demo': False
            }
        )
        if created: plans_created.append(pro.name)
        
        # Trial/Legacy Plan
        trial, created = SubscriptionPlan.objects.get_or_create(
            name='Trial / Legacy',
            defaults={
                'description': 'Plan de transición para gimnasios existentes',
                'price_monthly': 0.00,
                'max_members': None,
                'is_demo': True,
                'module_pos': True,
                'module_calendar': True,
                'module_marketing': True      
            }
        )
        if created: plans_created.append(trial.name)
        
        return plans_created

    @staticmethod
    def migrate_orphan_gyms(target_plan_id=None):
        """
        Assign a plan to all orphan gyms.
        If no plan specified, looks for 'Trial / Legacy'.
        """
        if target_plan_id:
            plan = SubscriptionPlan.objects.get(id=target_plan_id)
        else:
            plan = SubscriptionPlan.objects.filter(name__icontains='Trial').first()
            if not plan:
                plan = SubscriptionPlan.objects.filter(is_demo=True).first()
                
        if not plan:
            raise ValueError("No se encontró un plan válido para la migración")
            
        orphans = MigrationService.get_orphan_gyms()
        count = 0
        
        from datetime import date, timedelta
        
        for gym in orphans:
            GymSubscription.objects.create(
                gym=gym,
                plan=plan,
                status='ACTIVE',
                billing_frequency='MONTHLY',
                current_period_start=date.today(),
                current_period_end=date.today() + timedelta(days=30),
                auto_renew=False # Manual renewal for migrated legacy
            )
            count += 1
            
        return count
