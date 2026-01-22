from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, date
from organizations.models import Franchise, Gym, GymGoal
from clients.models import Client, ClientSale
import calendar
import json

class IsFranchiseOwner(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.franchises_owned.exists() or self.request.user.is_superuser

class FranchiseDashboardView(LoginRequiredMixin, IsFranchiseOwner, TemplateView):
    template_name = "organizations/dashboard_franchise.html"

    def handle_no_permission(self):
        return redirect('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Determine Franchise(s)
        if user.is_superuser:
            franchises = Franchise.objects.all()
        else:
            franchises = user.franchises_owned.all()
            
        # For simplicity, focus on the first franchise if multiple, or aggregate all 
        # (This MVP assumes owner usually has one Franchise Group)
        gyms = Gym.objects.filter(franchise__in=franchises)
        
        # --- Time Ranges ---
        today = timezone.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # --- KPIs ---
        
        # 1. Total Active Members
        total_active_members = Client.objects.filter(
            gym__in=gyms, 
            status=Client.Status.ACTIVE
        ).count()
        
        # 2. Total Revenue (Current Month)
        revenue_month = ClientSale.objects.filter(
            client__gym__in=gyms,
            date__gte=start_of_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # 3. Churn Rate (Simplified: Inactive / Total * 100)
        # In a real scenario, this calculation is more complex over a period.
        total_clients = Client.objects.filter(gym__in=gyms).exclude(status=Client.Status.LEAD).count()
        inactive_clients = Client.objects.filter(gym__in=gyms, status=Client.Status.INACTIVE).count()
        
        churn_rate = 0
        if total_clients > 0:
            churn_rate = round((inactive_clients / total_clients) * 100, 1)

        # 4. Total Gyms
        total_gyms = gyms.count()
        
        # --- Charts Data (Revenue Trends - Last 6 Months) ---
        months = []
        revenue_data = [] # Global or Per Gym? Let's do Global for the big chart
        
        for i in range(5, -1, -1):
            date = today - timedelta(days=i*30) # Approx
            month_name = date.strftime("%b")
            months.append(month_name)
            
            # Start/End date for that month
            # Calculate properly
            import calendar
            last_day = calendar.monthrange(date.year, date.month)[1]
            m_start = date.replace(day=1, hour=0, minute=0, second=0)
            m_end = date.replace(day=last_day, hour=23, minute=59, second=59)
            
            total = ClientSale.objects.filter(
                client__gym__in=gyms,
                date__range=(m_start, m_end)
            ).aggregate(total=Sum('amount'))['total'] or 0
            revenue_data.append(float(total))

        # --- Top Gyms Performance ---
        today_date = date.today()
        gyms_performance = []
        for gym in gyms:
            g_revenue = ClientSale.objects.filter(
                client__gym=gym,
                date__gte=start_of_month
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            g_active = Client.objects.filter(gym=gym, status=Client.Status.ACTIVE).count()
            
            # Get current active goals for this gym
            current_goals = GymGoal.objects.filter(
                gym=gym,
                is_active=True,
                start_date__lte=today_date,
                end_date__gte=today_date
            ).first()
            
            goal_data = {
                'has_goals': False,
                'members_progress': None,
                'revenue_progress': None,
                'target_members': None,
                'target_revenue': None,
            }
            
            if current_goals:
                goal_data['has_goals'] = True
                if current_goals.target_members:
                    goal_data['target_members'] = current_goals.target_members
                    goal_data['members_progress'] = current_goals.get_progress_members(g_active)
                if current_goals.target_revenue:
                    goal_data['target_revenue'] = float(current_goals.target_revenue)
                    goal_data['revenue_progress'] = current_goals.get_progress_revenue(g_revenue)
            
            gyms_performance.append({
                'id': gym.id,
                'name': gym.commercial_name or gym.name,
                'revenue': float(g_revenue),
                'active_members': g_active,
                'location': f"{gym.city}, {gym.country}" if gym.city else "N/A",
                'goals': goal_data,
            })
            
        # Sort by revenue
        gyms_performance.sort(key=lambda x: x['revenue'], reverse=True)

        context.update({
            'kpi': {
                'active_members': total_active_members,
                'revenue_month': revenue_month,
                'churn_rate': churn_rate,
                'total_gyms': total_gyms
            },
            'chart_data': json.dumps({
                'labels': months,
                'data': revenue_data
            }),
            'gyms_performance': gyms_performance,
            'franchise_name': franchises.first().name if franchises.exists() else "Franquicia"
        })
        return context
