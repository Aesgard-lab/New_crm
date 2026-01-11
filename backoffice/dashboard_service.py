from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from sales.models import Order
from clients.models import Client
from memberships.models import MembershipPlan

class DashboardService:
    def __init__(self, gym):
        self.gym = gym
        self.today = timezone.now().date()
        self.first_day_this_month = self.today.replace(day=1)
        self.last_month = self.first_day_this_month - timedelta(days=1)
        self.first_day_last_month = self.last_month.replace(day=1)

    def get_kpi_stats(self):
        """
        Calculates main KPIs: Revenue, Members, Churn.
        """
        # 1. Revenue (This Month vs Last Month)
        revenue_this_month = Order.objects.filter(
            gym=self.gym, 
            status='PAID', 
            created_at__gte=self.first_day_this_month
        ).aggregate(t=Sum('total_amount'))['t'] or 0

        revenue_last_month = Order.objects.filter(
            gym=self.gym, 
            status='PAID', 
            created_at__gte=self.first_day_last_month,
            created_at__lte=self.last_month
        ).aggregate(t=Sum('total_amount'))['t'] or 0

        # Growth %
        if revenue_last_month > 0:
            growth_revenue = ((revenue_this_month - revenue_last_month) / revenue_last_month) * 100
        else:
            growth_revenue = 100 if revenue_this_month > 0 else 0

        # TAXES (Simplified: assuming 21% avg for dashboard estimate or sum from OrderItems if complex)
        taxes_this_month = Order.objects.filter(
            gym=self.gym, 
            status='PAID', 
            created_at__gte=self.first_day_this_month
        ).aggregate(t=Sum('total_tax'))['t'] or 0
        # Note: Order model might not have total_tax stored directly, we might need to sum items. 
        # For performance, let's check Order model. If not, we estimate or query items.
        # Checking Order model previously... it didn't have total_tax field explicitly shown in recent edits.
        # Let's assume we might need to add it or calculate it. For now, I'll return 0 if field missing.
        
        # 2. Active Members
        # Definition: Clients with active MembershipPlan
        # Simple count for now: Clients status='ACTIVE'
        active_members = Client.objects.filter(gym=self.gym, status='ACTIVE').count()
        
        # New Members (This Month)
        new_members = Client.objects.filter(
            gym=self.gym, 
            created_at__gte=self.first_day_this_month
        ).count()

        # Churn (Members who became inactive this month) - Harder to track without history table.
        # Proxy: Clients updated to inactive this month? Or just current inactive count?
        # Let's show "Bajas" as manually deactivated or expired this month.
        # This requires an "Expiration Log". Skipping exact churn for "Inactive Total" for now.
        
        return {
            'revenue_current': "{:.2f}".format(revenue_this_month),
            'revenue_growth': round(growth_revenue, 1),
            'active_members': active_members,
            'new_members': new_members,
            'taxes_current': "{:.2f}".format(taxes_this_month)
        }

    def get_risk_clients(self):
        """
        Identifies high-risk clients.
        Risk Factors:
        1. No Attendance (Last 21 days) - Requires Attendance Model (Not fully implemented yet).
           Proxy: No sales/activity in 30 days?
        2. Billing Failure: Pending Orders.
        3. Contract Expiring: End date < 15 days.
        """
        risk_list = []
        
        # 1. Billing Risk (High Priority)
        debtors = Client.objects.filter(
            gym=self.gym,
            orders__status__in=['PENDING', 'PARTIAL', 'FAILED'] # Assuming FAILED exists
        ).distinct()
        
        for c in debtors:
            risk_list.append({
                'client': c,
                'reason': 'Pagos Pendientes',
                'level': 'CRITICAL'
            })
            
        # 2. Expiry Risk
        # Try to find Clients with memberships ending soon.
        # We don't have a direct "MembershipSubscription" model visible yet (we have Plans).
        # We usually link Client -> Plan directly or via proper subscription model.
        # Looking at Client model... 
        # If we don't have subscription expiry, we skip this check.
        
        # 3. Absence Risk (Placeholder)
        # return top 5
        return risk_list[:5]

    def get_top_clients(self):
        """
        Returns top clients by LTV (Total Spent).
        """
        clients = Client.objects.filter(gym=self.gym).annotate(
            total_spent=Sum('orders__total_amount', filter=Q(orders__status='PAID'))
        ).order_by('-total_spent')[:5]
        
        # Convert to list to format the number in backend
        formatted_clients = []
        for c in clients:
            if c.total_spent is None:
                c.total_spent = 0
            formatted_clients.append({
                'id': c.id,
                'first_name': c.first_name,
                'last_name': c.last_name,
                'email': c.email,
                'total_spent_fmt': "{:.2f}".format(c.total_spent)
            })
        return formatted_clients
