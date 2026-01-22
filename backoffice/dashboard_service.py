from django.utils import timezone
from django.db.models import Sum, Count, Q, Max, Prefetch, OuterRef, Subquery
from django.db.models.functions import TruncDate, TruncMonth
from django.core.cache import cache
from datetime import timedelta, datetime
from sales.models import Order
from clients.models import Client
from memberships.models import MembershipPlan
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

class DashboardService:
    CACHE_TIMEOUT = 300  # 5 minutos de caché
    
    def __init__(self, gym):
        self.gym = gym
        self.today = timezone.now().date()
        self.first_day_this_month = self.today.replace(day=1)
        self.last_month = self.first_day_this_month - timedelta(days=1)
        self.first_day_last_month = self.last_month.replace(day=1)
        self._cache_key_prefix = f"dashboard_{gym.id if gym else 'none'}"
    
    def _get_cached(self, key, func):
        """Helper para obtener datos de caché o calcularlos."""
        cache_key = f"{self._cache_key_prefix}_{key}"
        result = cache.get(cache_key)
        if result is None:
            result = func()
            cache.set(cache_key, result, self.CACHE_TIMEOUT)
        return result

    def get_kpi_stats(self):
        """
        Calculates main KPIs: Revenue, Members, Churn.
        Optimizado con una única consulta agregada y caché.
        """
        def _calculate():
            # Una sola consulta para revenue este mes y mes pasado
            revenue_data = Order.objects.filter(
                gym=self.gym, 
                status='PAID',
                created_at__gte=self.first_day_last_month
            ).aggregate(
                this_month=Sum('total_amount', filter=Q(created_at__gte=self.first_day_this_month)),
                last_month=Sum('total_amount', filter=Q(
                    created_at__gte=self.first_day_last_month,
                    created_at__lt=self.first_day_this_month
                )),
                taxes_this_month=Sum('total_tax', filter=Q(created_at__gte=self.first_day_this_month))
            )
            
            revenue_this_month = revenue_data['this_month'] or 0
            revenue_last_month = revenue_data['last_month'] or 0
            taxes_this_month = revenue_data['taxes_this_month'] or 0

            # Growth %
            if revenue_last_month > 0:
                growth_revenue = ((revenue_this_month - revenue_last_month) / revenue_last_month) * 100
            else:
                growth_revenue = 100 if revenue_this_month > 0 else 0
            
            # Count clients with active memberships where plan.is_membership=True
            from clients.models import ClientMembership
            
            # Active members = Clients with at least one ACTIVE membership with is_membership=True
            active_members = Client.objects.filter(
                gym=self.gym,
                status='ACTIVE',
                memberships__status='ACTIVE',
                memberships__plan__is_membership=True
            ).distinct().count()
            
            # New members this month = Clients who got their first membership this month
            # where the plan has is_membership=True
            new_members = ClientMembership.objects.filter(
                gym=self.gym,
                plan__is_membership=True,
                created_at__gte=self.first_day_this_month
            ).values('client').distinct().count()
            
            return {
                'revenue_current': "{:.2f}".format(revenue_this_month),
                'revenue_net': "{:.2f}".format(revenue_this_month - taxes_this_month),
                'revenue_growth': round(growth_revenue, 1),
                'active_members': active_members,
                'new_members': new_members,
                'taxes_current': "{:.2f}".format(taxes_this_month)
            }
        
        return self._get_cached('kpi_stats', _calculate)


    def get_risk_clients_enhanced(self):
        """
        ⭐ SISTEMA DE SCORING DE RIESGO ESTRATOSFÉRICO (0-100 puntos):
        
        FACTORES FINANCIEROS (50 pts max):
        - 30 pts: Pagos pendientes (cada orden)
        - 20 pts: Membresía expira en <15 días
        
        FACTORES DE ENGAGEMENT (35 pts max):
        - 25 pts: Sin acceso a app/portal últimos 30 días (si tiene cuenta)
        - 15 pts: Sin pagos/actividad últimos 30 días
        - 10 pts: Usuario registrado pero nunca accedió a la app
        
        FACTORES DE RETENCIÓN (15 pts max):
        - 10 pts: Cliente nuevo (<3 meses)
        - 15 pts: Tasa de asistencia <50% del promedio (si hay datos)
        
        OPTIMIZADO: Una sola consulta con anotaciones + análisis de user.last_login
        """
        def _calculate():
            try:
                from clients.models import ClientMembership
            except:
                ClientMembership = None
            
            # Subconsultas para evitar N+1
            last_order_date = Order.objects.filter(
                client=OuterRef('pk'),
                status='PAID'
            ).order_by('-created_at').values('created_at')[:1]
            
            pending_orders_count = Order.objects.filter(
                client=OuterRef('pk'),
                status__in=['PENDING', 'PARTIAL']
            ).values('client').annotate(cnt=Count('id')).values('cnt')
            
            # Consulta optimizada con anotaciones + datos de usuario
            clients = Client.objects.filter(
                gym=self.gym, 
                status='ACTIVE'
            ).select_related('user').annotate(
                pending_orders=Count('orders', filter=Q(orders__status__in=['PENDING', 'PARTIAL'])),
                last_order_date=Subquery(last_order_date)
            ).only(
                'id', 'first_name', 'last_name', 'email', 'created_at', 
                'last_app_access', 'app_access_count', 'user'
            )[:150]  # Aumentado para mejor análisis
            
            # Pre-cargar membresías expirando
            expiring_memberships = {}
            if ClientMembership:
                expiring = ClientMembership.objects.filter(
                    client__gym=self.gym,
                    client__status='ACTIVE',
                    status='ACTIVE',
                    end_date__lte=self.today + timedelta(days=15),
                    end_date__gte=self.today
                ).select_related('client').order_by('end_date')
                
                for m in expiring:
                    if m.client_id not in expiring_memberships:
                        expiring_memberships[m.client_id] = m.end_date
            
            risk_clients = []
            
            for client in clients:
                score = 0
                factors = []
                
                # ======== FACTORES FINANCIEROS (50 pts max) ========
                
                # Factor 1: Billing Risk (30 pts max)
                if client.pending_orders > 0:
                    billing_score = min(30, client.pending_orders * 10)
                    score += billing_score
                    factors.append({
                        'type': 'billing',
                        'text': f'💳 {client.pending_orders} pagos pendientes',
                        'points': billing_score,
                        'category': 'financial'
                    })
                
                # Factor 2: Membership Expiry Risk (20 pts)
                if client.id in expiring_memberships:
                    score += 20
                    factors.append({
                        'type': 'expiry',
                        'text': f'⏰ Expira {expiring_memberships[client.id].strftime("%d/%m")}',
                        'points': 20,
                        'category': 'financial'
                    })
                
                # ======== FACTORES DE ENGAGEMENT (35 pts max) ========
                
                # Factor 3: App/Portal Inactivity (25 pts) - NUEVO
                if client.user:  # Tiene cuenta en el portal/app
                    if client.user.last_login:
                        days_since_login = (timezone.now() - client.user.last_login).days
                        if days_since_login > 30:
                            # Progresivo: más días = más puntos
                            engagement_score = min(25, 15 + ((days_since_login - 30) // 10) * 5)
                            score += engagement_score
                            factors.append({
                                'type': 'app_inactive',
                                'text': f'📱 Sin acceso app {days_since_login} días',
                                'points': engagement_score,
                                'category': 'engagement'
                            })
                    else:
                        # Cuenta creada pero nunca accedió (10 pts)
                        score += 10
                        factors.append({
                            'type': 'no_app_login',
                            'text': '🔒 Nunca accedió a la app',
                            'points': 10,
                            'category': 'engagement'
                        })
                
                # Factor 4: Order Inactivity (15 pts)
                if client.last_order_date:
                    days_since_order = (self.today - client.last_order_date.date()).days
                    if days_since_order > 30:
                        inactive_score = min(15, (days_since_order // 15) * 5)
                        score += inactive_score
                        factors.append({
                            'type': 'inactive',
                            'text': f'💤 Sin pagos {days_since_order} días',
                            'points': inactive_score,
                            'category': 'engagement'
                        })
                else:
                    # Nunca ha pagado (crítico)
                    score += 15
                    factors.append({
                        'type': 'no_payment',
                        'text': '❌ Sin historial de pagos',
                        'points': 15,
                        'category': 'engagement'
                    })
                
                # ======== FACTORES DE RETENCIÓN (15 pts max) ========
                
                # Factor 5: New Client Risk (10 pts)
                days_as_client = (self.today - client.created_at.date()).days
                if days_as_client < 90:
                    score += 10
                    factors.append({
                        'type': 'new_client',
                        'text': f'🆕 Cliente nuevo ({days_as_client}d)',
                        'points': 10,
                        'category': 'retention'
                    })
                
                # Agregar a lista si score >= 15 (umbral reducido para capturar más casos)
                if score >= 15:
                    # Determinar nivel de riesgo
                    if score >= 70:
                        risk_level = 'CRÍTICO'
                        risk_color = 'red'
                        risk_icon = '🚨'
                    elif score >= 50:
                        risk_level = 'ALTO'
                        risk_color = 'orange'
                        risk_icon = '⚠️'
                    elif score >= 30:
                        risk_level = 'MEDIO'
                        risk_color = 'yellow'
                        risk_icon = '⚡'
                    else:
                        risk_level = 'BAJO'
                        risk_color = 'blue'
                        risk_icon = 'ℹ️'
                    
                    # Categorizar factores
                    financial_factors = [f for f in factors if f.get('category') == 'financial']
                    engagement_factors = [f for f in factors if f.get('category') == 'engagement']
                    retention_factors = [f for f in factors if f.get('category') == 'retention']
                    
                    risk_clients.append({
                        'id': client.id,
                        'name': f"{client.first_name} {client.last_name}",
                        'email': client.email,
                        'score': score,
                        'level': risk_level,
                        'color': risk_color,
                        'icon': risk_icon,
                        'factors': factors,
                        'financial_factors': financial_factors,
                        'engagement_factors': engagement_factors,
                        'retention_factors': retention_factors,
                        'has_app_access': bool(client.user),
                        'action_required': score >= 50,
                        'days_to_action': max(1, 30 - (score // 3)),
                        # Recomendaciones de acción
                        'recommended_actions': self._get_recommended_actions(factors, score)
                    })
            
            return sorted(risk_clients, key=lambda x: x['score'], reverse=True)[:15]
        
        return self._get_cached('risk_clients_enhanced', _calculate)
    
    def _get_recommended_actions(self, factors, score):
        """Genera recomendaciones basadas en los factores de riesgo"""
        actions = []
        
        factor_types = {f['type'] for f in factors}
        
        if 'billing' in factor_types:
            actions.append('💰 Contactar para resolver pagos pendientes')
        
        if 'expiry' in factor_types:
            actions.append('🔄 Ofrecer renovación de membresía')
        
        if 'app_inactive' in factor_types or 'no_app_login' in factor_types:
            actions.append('📲 Incentivar uso de la app (enviar tutorial)')
        
        if 'inactive' in factor_types or 'no_payment' in factor_types:
            actions.append('📞 Llamada personalizada para reenganche')
        
        if 'new_client' in factor_types:
            actions.append('👋 Seguimiento de onboarding y bienvenida')
        
        if score >= 70:
            actions.insert(0, '🚨 URGENTE: Reunión presencial recomendada')
        
        return actions[:3]  # Máximo 3 acciones prioritarias
    def get_risk_clients(self):
        """
        Backwards compatible: returns old format for existing templates.
        """
        enhanced = self.get_risk_clients_enhanced()
        return [
            {
                'client': type('obj', (object,), {
                    'id': c['id'],
                    'first_name': c['name'].split()[0],
                    'last_name': ' '.join(c['name'].split()[1:]),
                    'email': c['email']
                })(),
                'reason': c['factors'][0]['text'] if c['factors'] else 'Riesgo detectado',
                'level': 'CRITICAL' if c['level'] == 'CRÍTICO' else 'HIGH' if c['level'] == 'ALTO' else 'MEDIUM'
            }
            for c in enhanced[:5]
        ]

    def get_top_clients(self):
        """
        Returns top clients by LTV (Total Spent).
        Optimizado con caché.
        """
        def _calculate():
            clients = Client.objects.filter(gym=self.gym).annotate(
                total_spent=Sum('orders__total_amount', filter=Q(orders__status='PAID'))
            ).order_by('-total_spent')[:5]
            
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
        
        return self._get_cached('top_clients', _calculate)

    def get_revenue_chart_data(self, days=30):
        """
        Returns daily revenue data for the last N days.
        Used to power the dashboard chart.
        Optimizado con caché.
        """
        def _calculate():
            start_date = self.today - timedelta(days=days-1)
            
            # Query daily totals
            daily_data = Order.objects.filter(
                gym=self.gym,
                status='PAID',
                created_at__date__gte=start_date,
                created_at__date__lte=self.today
            ).annotate(
                day=TruncDate('created_at')
            ).values('day').annotate(
                total=Sum('total_amount')
            ).order_by('day')
            
            # Create a dictionary for fast lookup
            data_dict = {entry['day']: float(entry['total'] or 0) for entry in daily_data}
            
            # Fill all days (including zeros)
            labels = []
            values = []
            current = start_date
            while current <= self.today:
                labels.append(current.strftime('%d/%m'))
                values.append(data_dict.get(current, 0))
                current += timedelta(days=1)
            
            return {
                'labels': labels,
                'values': values
            }
        
        return self._get_cached(f'revenue_chart_{days}', _calculate)

    def get_membership_stats(self):
        """
        Returns membership statistics for the dashboard.
        Optimizado con una sola consulta agregada y caché.
        """
        def _calculate():
            from clients.models import ClientMembership
            
            # Una sola consulta con múltiples agregaciones
            stats = ClientMembership.objects.filter(
                client__gym=self.gym
            ).aggregate(
                active=Count('id', filter=Q(status='ACTIVE')),
                expiring_soon=Count('id', filter=Q(
                    status='ACTIVE',
                    end_date__lte=self.today + timedelta(days=15),
                    end_date__gte=self.today
                )),
                expired_this_month=Count('id', filter=Q(
                    status='EXPIRED',
                    end_date__gte=self.first_day_this_month
                ))
            )
            
            return {
                'active': stats['active'],
                'expiring_soon': stats['expiring_soon'],
                'expired_this_month': stats['expired_this_month']
            }
        
        return self._get_cached('membership_stats', _calculate)

    def get_revenue_forecast(self, months_ahead=3):
        """
        Forecasting con Moving Average + Linear Regression
        Predice la facturación de los próximos N meses.
        Optimizado con caché (datos no cambian mucho).
        """
        def _calculate():
            try:
                # 1. Recopilar data histórica (últimos 6-12 meses)
                six_months_ago = self.today - timedelta(days=180)
                
                monthly_data = Order.objects.filter(
                    gym=self.gym,
                    status='PAID',
                    created_at__date__gte=six_months_ago
                ).annotate(
                    month=TruncMonth('created_at')
                ).values('month').annotate(
                    total=Sum('total_amount')
                ).order_by('month')
                
                # 2. Convertir a DataFrame
                df = pd.DataFrame(list(monthly_data))
                if df.empty:
                    return self._empty_forecast(months_ahead)
                
                df.columns = ['date', 'revenue']
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
                df['revenue'] = df['revenue'].astype(float)
                
                # 3. Rellenar meses faltantes con interpolación
                date_range = pd.date_range(start=six_months_ago, end=self.today, freq='MS')
                df = df.set_index('date').reindex(date_range, fill_value=0).reset_index()
                df.columns = ['date', 'revenue']
                df['revenue'] = df['revenue'].interpolate(method='linear', fill_value='backfill')
                
                # 4. Calcular Moving Average (suavizar)
                if len(df) >= 3:
                    df['ma_3m'] = df['revenue'].rolling(window=3, center=True, min_periods=1).mean()
                    forecast_values = df['ma_3m'].values
                else:
                    forecast_values = df['revenue'].values
                
                # 5. Linear Regression para tendencia
                X = np.arange(len(df)).reshape(-1, 1)
                y = df['revenue'].values
                
                model = LinearRegression()
                model.fit(X, y)
                slope = float(model.coef_[0])
                
                # 6. Predecir próximos meses
                future_indices = np.arange(len(df), len(df) + months_ahead).reshape(-1, 1)
                forecast = model.predict(future_indices)
                
                # 7. Construir respuesta
                forecast_data = []
                for i in range(months_ahead):
                    future_date = self.today + timedelta(days=30 * (i + 1))
                    predicted_value = max(0, float(forecast[i]))
                    
                    # Determinar confianza basada en cantidad de datos
                    if len(df) >= 12:
                        confidence = 'ALTA'
                        confidence_pct = 85
                    elif len(df) >= 6:
                        confidence = 'MEDIA'
                        confidence_pct = 70
                    else:
                        confidence = 'BAJA'
                        confidence_pct = 55
                    
                    forecast_data.append({
                        'month': future_date.strftime("%b %Y"),
                        'month_short': future_date.strftime("%b"),
                        'predicted': round(predicted_value, 2),
                        'confidence': confidence,
                        'confidence_pct': confidence_pct
                    })
                
                # Histórico promedio - manejar NaN
                positive_revenue = df[df['revenue'] > 0]['revenue']
                if len(positive_revenue) > 0:
                    historical_avg = float(positive_revenue.mean())
                    if pd.isna(historical_avg):
                        historical_avg = 0
                else:
                    historical_avg = 0
                
                # Determinar tendencia
                if slope > 0:
                    trend = 'CRECIENTE'
                    trend_icon = '↑'
                    trend_color = 'green'
                elif slope < 0:
                    trend = 'DECRECIENTE'
                    trend_icon = '↓'
                    trend_color = 'red'
                else:
                    trend = 'ESTABLE'
                    trend_icon = '→'
                    trend_color = 'gray'
                
                return {
                    'forecast': forecast_data,
                    'historical_avg': round(historical_avg, 2) if not pd.isna(historical_avg) else 0,
                    'historical_data_points': len(df),
                    'trend': trend,
                    'trend_icon': trend_icon,
                    'trend_color': trend_color,
                    'trend_strength': round(abs(slope), 2),
                    'total_quarterly': round(sum(f['predicted'] for f in forecast_data), 2),
                    'monthly_avg': round(sum(f['predicted'] for f in forecast_data) / len(forecast_data), 2)
                }
            except Exception as e:
                # Si hay error, retornar forecast vacío pero válido
                return self._empty_forecast(months_ahead)
        
        return self._get_cached(f'revenue_forecast_{months_ahead}', _calculate)
    
    def _empty_forecast(self, months_ahead=3):
        """Helper para retornar estructura válida cuando no hay datos"""
        forecast_data = []
        for i in range(months_ahead):
            future_date = self.today + timedelta(days=30 * (i + 1))
            forecast_data.append({
                'month': future_date.strftime("%b %Y"),
                'month_short': future_date.strftime("%b"),
                'predicted': 0,
                'confidence': 'BAJA',
                'confidence_pct': 0
            })
        
        return {
            'forecast': forecast_data,
            'historical_avg': 0,
            'historical_data_points': 0,
            'trend': 'SIN DATOS',
            'trend_icon': '?',
            'trend_color': 'gray',
            'trend_strength': 0,
            'total_quarterly': 0,
            'monthly_avg': 0
        }

    def get_breakeven_analysis(self):
        """
        Análisis de punto de equilibrio (Break-even):
        - Balance actual: Facturación - Gastos
        - Proyección: Meses hasta alcanzar el equilibrio
        - Basado en tendencia de crecimiento de ingresos vs gastos
        """
        def _calculate():
            from finance.models import Expense
            from decimal import Decimal
            
            # Calcular facturación mensual (últimos 6 meses)
            six_months_ago = self.today - timedelta(days=180)
            
            monthly_revenue = Order.objects.filter(
                gym=self.gym,
                status='PAID',
                created_at__gte=six_months_ago
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                total=Sum('total_amount')
            ).order_by('month')
            
            # Calcular gastos mensuales (últimos 6 meses)
            monthly_expenses = Expense.objects.filter(
                gym=self.gym,
                issue_date__gte=six_months_ago
            ).annotate(
                month=TruncMonth('issue_date')
            ).values('month').annotate(
                total=Sum('total_amount')
            ).order_by('month')
            
            # Convertir a diccionarios
            revenue_by_month = {item['month']: float(item['total'] or 0) for item in monthly_revenue}
            expenses_by_month = {item['month']: float(item['total'] or 0) for item in monthly_expenses}
            
            # Balance del mes actual
            current_month_revenue = float(Order.objects.filter(
                gym=self.gym,
                status='PAID',
                created_at__gte=self.first_day_this_month
            ).aggregate(total=Sum('total_amount'))['total'] or 0)
            
            current_month_expenses = float(Expense.objects.filter(
                gym=self.gym,
                issue_date__gte=self.first_day_this_month
            ).aggregate(total=Sum('total_amount'))['total'] or 0)
            
            current_balance = current_month_revenue - current_month_expenses
            
            # Balance acumulado total (desde el inicio)
            total_revenue = float(Order.objects.filter(
                gym=self.gym,
                status='PAID'
            ).aggregate(total=Sum('total_amount'))['total'] or 0)
            
            total_expenses = float(Expense.objects.filter(
                gym=self.gym
            ).aggregate(total=Sum('total_amount'))['total'] or 0)
            
            accumulated_balance = total_revenue - total_expenses
            
            # Calcular tendencias si hay datos suficientes
            if len(revenue_by_month) >= 3:
                # Crecimiento mensual promedio de ingresos
                revenue_values = list(revenue_by_month.values())
                revenue_growth = []
                for i in range(1, len(revenue_values)):
                    if revenue_values[i-1] > 0:
                        growth = revenue_values[i] - revenue_values[i-1]
                        revenue_growth.append(growth)
                
                avg_revenue_growth = sum(revenue_growth) / len(revenue_growth) if revenue_growth else 0
                
                # Crecimiento mensual promedio de gastos
                expense_values = list(expenses_by_month.values())
                expense_growth = []
                for i in range(1, len(expense_values)):
                    if expense_values[i-1] > 0:
                        growth = expense_values[i] - expense_values[i-1]
                        expense_growth.append(growth)
                
                avg_expense_growth = sum(expense_growth) / len(expense_growth) if expense_growth else 0
                
                # Crecimiento neto mensual
                net_monthly_growth = avg_revenue_growth - avg_expense_growth
                
                # Proyección de meses hasta equilibrio
                months_to_breakeven = None
                breakeven_date = None
                
                if accumulated_balance < 0 and net_monthly_growth > 0:
                    # Deficit actual y crecimiento positivo
                    months_to_breakeven = int(abs(accumulated_balance) / net_monthly_growth) + 1
                    breakeven_date = self.today + timedelta(days=30 * months_to_breakeven)
                elif accumulated_balance < 0 and net_monthly_growth <= 0:
                    # Deficit y crecimiento negativo o nulo = No se alcanzará
                    months_to_breakeven = None
                    breakeven_date = None
                else:
                    # Ya está en equilibrio
                    months_to_breakeven = 0
                    breakeven_date = self.today
                
                # Estado
                if accumulated_balance >= 0:
                    status = 'POSITIVO'
                    status_color = 'green'
                    status_icon = '✅'
                elif months_to_breakeven and months_to_breakeven <= 12:
                    status = 'EN CAMINO'
                    status_color = 'yellow'
                    status_icon = '📈'
                elif months_to_breakeven:
                    status = 'LARGO PLAZO'
                    status_color = 'orange'
                    status_icon = '⏳'
                else:
                    status = 'CRÍTICO'
                    status_color = 'red'
                    status_icon = '🚨'
                
                return {
                    'current_month_revenue': round(current_month_revenue, 2),
                    'current_month_expenses': round(current_month_expenses, 2),
                    'current_balance': round(current_balance, 2),
                    'accumulated_balance': round(accumulated_balance, 2),
                    'avg_revenue_growth': round(avg_revenue_growth, 2),
                    'avg_expense_growth': round(avg_expense_growth, 2),
                    'net_monthly_growth': round(net_monthly_growth, 2),
                    'months_to_breakeven': months_to_breakeven,
                    'breakeven_date': breakeven_date.strftime('%B %Y') if breakeven_date else None,
                    'status': status,
                    'status_color': status_color,
                    'status_icon': status_icon,
                    'has_data': True
                }
            else:
                # No hay datos suficientes
                return {
                    'current_month_revenue': round(current_month_revenue, 2),
                    'current_month_expenses': round(current_month_expenses, 2),
                    'current_balance': round(current_balance, 2),
                    'accumulated_balance': round(accumulated_balance, 2),
                    'avg_revenue_growth': 0,
                    'avg_expense_growth': 0,
                    'net_monthly_growth': 0,
                    'months_to_breakeven': None,
                    'breakeven_date': None,
                    'status': 'SIN DATOS',
                    'status_color': 'gray',
                    'status_icon': '📊',
                    'has_data': False
                }
        
        return self._get_cached('breakeven_analysis', _calculate)
