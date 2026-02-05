"""
Servicio de Analíticas Comparativas Avanzadas.
Inspirado en: Mindbody, Glofox, WellnessLiving, ABC Fitness, Wodify.

Métricas implementadas:
- Revenue (facturación total, por categoría, MRR, ARPC)
- Membresías (altas, bajas, churn, retention)
- Asistencias (check-ins, ocupación, no-shows)
- Productos (ventas, top productos)
- Engagement (visitas por cliente, LTV)
"""
from django.db.models import Sum, Count, Avg, Q, F, Min, Max
from django.db.models.functions import TruncMonth, TruncYear, ExtractMonth, ExtractYear, Coalesce
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, date, timedelta
from decimal import Decimal
from collections import defaultdict
import calendar

from sales.models import Order, OrderItem
from clients.models import Client, ClientVisit
from memberships.models import MembershipPlan
from activities.models import ActivitySession
from products.models import Product


class ComparativeAnalyticsService:
    """
    Servicio principal para generar analíticas comparativas por mes y año.
    
    Uso:
        service = ComparativeAnalyticsService(gym)
        data = service.get_full_comparative_report(years=[2024, 2025, 2026])
    """
    
    CACHE_TIMEOUT = 600  # 10 minutos
    MONTH_NAMES_ES = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]
    
    def __init__(self, gym, cache_enabled=True):
        self.gym = gym
        self.cache_enabled = cache_enabled
        self._cache_prefix = f"analytics_{gym.id}"
        self.current_year = timezone.now().year
        self.current_month = timezone.now().month
    
    def _cache_key(self, key):
        return f"{self._cache_prefix}_{key}"
    
    def _get_cached(self, key, func):
        """Helper para obtener datos de caché o calcularlos."""
        if not self.cache_enabled:
            return func()
        
        cache_key = self._cache_key(key)
        result = cache.get(cache_key)
        if result is None:
            result = func()
            cache.set(cache_key, result, self.CACHE_TIMEOUT)
        return result
    
    def clear_cache(self):
        """Limpia toda la caché de este gimnasio."""
        # En producción, usar cache.delete_pattern si el backend lo soporta
        pass
    
    # =========================================================================
    # REVENUE / FACTURACIÓN
    # =========================================================================
    
    def get_revenue_by_month(self, years=None):
        """
        Obtiene la facturación mensual comparativa por años.
        
        Returns:
            {
                'months': ['Enero', 'Febrero', ...],
                'data': {
                    2024: [1200.50, 1350.00, ...],
                    2025: [1400.00, 1500.00, ...],
                },
                'totals': {2024: 15000.00, 2025: 17000.00},
                'growth_yoy': {2025: 13.33, 2026: 8.5}  # % crecimiento año vs año anterior
            }
        """
        if years is None:
            years = [self.current_year - 2, self.current_year - 1, self.current_year]
        
        def _calculate():
            result = {
                'months': self.MONTH_NAMES_ES,
                'data': {year: [Decimal('0.00')] * 12 for year in years},
                'totals': {year: Decimal('0.00') for year in years},
                'growth_yoy': {},
                'taxes': {year: [Decimal('0.00')] * 12 for year in years},
                'net_revenue': {year: [Decimal('0.00')] * 12 for year in years},
            }
            
            # Query optimizada: una sola consulta para todos los años
            revenue_data = Order.objects.filter(
                gym=self.gym,
                status='PAID',
                created_at__year__in=years
            ).annotate(
                month=ExtractMonth('created_at'),
                year=ExtractYear('created_at')
            ).values('month', 'year').annotate(
                total=Sum('total_amount'),
                total_tax=Sum('total_tax'),
                total_base=Sum('total_base'),
                order_count=Count('id')
            ).order_by('year', 'month')
            
            for entry in revenue_data:
                year = entry['year']
                month_idx = entry['month'] - 1  # 0-indexed
                if year in result['data']:
                    result['data'][year][month_idx] = entry['total'] or Decimal('0.00')
                    result['taxes'][year][month_idx] = entry['total_tax'] or Decimal('0.00')
                    result['net_revenue'][year][month_idx] = entry['total_base'] or Decimal('0.00')
                    result['totals'][year] += entry['total'] or Decimal('0.00')
            
            # Calcular crecimiento YoY
            sorted_years = sorted(years)
            for i, year in enumerate(sorted_years[1:], 1):
                prev_year = sorted_years[i - 1]
                if result['totals'][prev_year] > 0:
                    growth = ((result['totals'][year] - result['totals'][prev_year]) / result['totals'][prev_year]) * 100
                    result['growth_yoy'][year] = round(float(growth), 2)
                else:
                    result['growth_yoy'][year] = 100.0 if result['totals'][year] > 0 else 0.0
            
            # Convertir Decimals a float para JSON
            for year in years:
                result['data'][year] = [float(v) for v in result['data'][year]]
                result['taxes'][year] = [float(v) for v in result['taxes'][year]]
                result['net_revenue'][year] = [float(v) for v in result['net_revenue'][year]]
                result['totals'][year] = float(result['totals'][year])
            
            return result
        
        cache_key = f"revenue_monthly_{'_'.join(map(str, years))}"
        return self._get_cached(cache_key, _calculate)
    
    def get_revenue_by_category(self, years=None):
        """
        Desglose de facturación por categoría (membresías, productos, servicios).
        """
        if years is None:
            years = [self.current_year - 1, self.current_year]
        
        def _calculate():
            from django.contrib.contenttypes.models import ContentType
            from memberships.models import MembershipPlan
            from products.models import Product
            from services.models import Service
            
            result = {
                'categories': ['Membresías', 'Productos', 'Servicios', 'Otros'],
                'data': {year: {'Membresías': 0, 'Productos': 0, 'Servicios': 0, 'Otros': 0} for year in years}
            }
            
            # Obtener ContentTypes
            try:
                membership_ct = ContentType.objects.get_for_model(MembershipPlan)
                product_ct = ContentType.objects.get_for_model(Product)
                service_ct = ContentType.objects.get_for_model(Service)
            except:
                return result
            
            # Query por categoría
            items = OrderItem.objects.filter(
                order__gym=self.gym,
                order__status='PAID',
                order__created_at__year__in=years
            ).annotate(
                year=ExtractYear('order__created_at')
            ).values('year', 'content_type').annotate(
                total=Sum('subtotal')
            )
            
            for item in items:
                year = item['year']
                ct_id = item['content_type']
                total = float(item['total'] or 0)
                
                if year in result['data']:
                    if ct_id == membership_ct.id:
                        result['data'][year]['Membresías'] += total
                    elif ct_id == product_ct.id:
                        result['data'][year]['Productos'] += total
                    elif ct_id == service_ct.id:
                        result['data'][year]['Servicios'] += total
                    else:
                        result['data'][year]['Otros'] += total
            
            return result
        
        cache_key = f"revenue_category_{'_'.join(map(str, years))}"
        return self._get_cached(cache_key, _calculate)
    
    def get_mrr_arr(self, years=None):
        """
        Monthly Recurring Revenue (MRR) y Annual Recurring Revenue (ARR).
        Calcula el MRR basado en membresías activas recurrentes.
        """
        if years is None:
            years = [self.current_year - 1, self.current_year]
        
        def _calculate():
            from clients.models import ClientMembership
            
            result = {
                'months': self.MONTH_NAMES_ES,
                'mrr': {year: [0.0] * 12 for year in years},
                'arr': {year: 0.0 for year in years},
                'active_subscriptions': {year: [0] * 12 for year in years}
            }
            
            # Para cada mes, contar membresías activas recurrentes
            for year in years:
                for month in range(1, 13):
                    # Fecha de referencia: último día del mes
                    last_day = calendar.monthrange(year, month)[1]
                    ref_date = date(year, month, last_day)
                    
                    # No calcular meses futuros
                    if ref_date > timezone.now().date():
                        continue
                    
                    # Membresías activas y recurrentes en esa fecha
                    active_memberships = ClientMembership.objects.filter(
                        gym=self.gym,
                        status='ACTIVE',
                        plan__is_recurring=True,
                        start_date__lte=ref_date
                    ).filter(
                        Q(end_date__gte=ref_date) | Q(end_date__isnull=True)
                    ).select_related('plan').values(
                        'plan__base_price', 'plan__frequency_amount', 'plan__frequency_unit'
                    )
                    
                    monthly_total = Decimal('0.00')
                    count = 0
                    
                    for m in active_memberships:
                        # Normalizar a precio mensual
                        price = m['plan__base_price'] or Decimal('0.00')
                        freq_amount = m['plan__frequency_amount'] or 1
                        freq_unit = m['plan__frequency_unit'] or 'MONTH'
                        
                        if freq_unit == 'MONTH':
                            monthly_price = price / freq_amount
                        elif freq_unit == 'YEAR':
                            monthly_price = price / (freq_amount * 12)
                        elif freq_unit == 'WEEK':
                            monthly_price = (price / freq_amount) * 4.33
                        else:  # DAY
                            monthly_price = (price / freq_amount) * 30
                        
                        monthly_total += monthly_price
                        count += 1
                    
                    result['mrr'][year][month - 1] = float(monthly_total)
                    result['active_subscriptions'][year][month - 1] = count
                
                # ARR = MRR del último mes disponible * 12
                last_mrr = next((v for v in reversed(result['mrr'][year]) if v > 0), 0)
                result['arr'][year] = last_mrr * 12
            
            return result
        
        cache_key = f"mrr_arr_{'_'.join(map(str, years))}"
        return self._get_cached(cache_key, _calculate)
    
    def get_arpc(self, years=None):
        """
        Average Revenue Per Client (ARPC) mensual.
        """
        if years is None:
            years = [self.current_year - 1, self.current_year]
        
        def _calculate():
            result = {
                'months': self.MONTH_NAMES_ES,
                'arpc': {year: [0.0] * 12 for year in years},
                'total_arpc': {year: 0.0 for year in years}
            }
            
            # Revenue por mes con conteo de clientes únicos
            data = Order.objects.filter(
                gym=self.gym,
                status='PAID',
                created_at__year__in=years,
                client__isnull=False
            ).annotate(
                month=ExtractMonth('created_at'),
                year=ExtractYear('created_at')
            ).values('month', 'year').annotate(
                total_revenue=Sum('total_amount'),
                unique_clients=Count('client', distinct=True)
            )
            
            year_totals = {year: {'revenue': 0, 'clients': set()} for year in years}
            
            for entry in data:
                year = entry['year']
                month_idx = entry['month'] - 1
                
                if year in result['arpc']:
                    revenue = float(entry['total_revenue'] or 0)
                    clients = entry['unique_clients'] or 1
                    result['arpc'][year][month_idx] = round(revenue / clients, 2)
                    year_totals[year]['revenue'] += revenue
            
            # ARPC anual
            for year in years:
                total_clients = Order.objects.filter(
                    gym=self.gym,
                    status='PAID',
                    created_at__year=year,
                    client__isnull=False
                ).values('client').distinct().count() or 1
                
                result['total_arpc'][year] = round(year_totals[year]['revenue'] / total_clients, 2)
            
            return result
        
        cache_key = f"arpc_{'_'.join(map(str, years))}"
        return self._get_cached(cache_key, _calculate)
    
    # =========================================================================
    # MEMBRESÍAS / CLIENTES
    # =========================================================================
    
    def get_membership_metrics(self, years=None):
        """
        Métricas de membresías: altas, bajas, churn rate, net growth.
        """
        if years is None:
            years = [self.current_year - 1, self.current_year]
        
        def _calculate():
            from clients.models import ClientMembership
            
            result = {
                'months': self.MONTH_NAMES_ES,
                'new_memberships': {year: [0] * 12 for year in years},
                'cancellations': {year: [0] * 12 for year in years},
                'net_growth': {year: [0] * 12 for year in years},
                'total_active': {year: [0] * 12 for year in years},
                'churn_rate': {year: [0.0] * 12 for year in years},
                'retention_rate': {year: [0.0] * 12 for year in years},
                'yearly_totals': {
                    year: {
                        'new': 0, 'cancelled': 0, 'net': 0, 
                        'avg_churn': 0, 'avg_retention': 0
                    } for year in years
                }
            }
            
            # Altas (nuevas membresías)
            new_data = ClientMembership.objects.filter(
                gym=self.gym,
                created_at__year__in=years,
                plan__is_membership=True
            ).annotate(
                month=ExtractMonth('created_at'),
                year=ExtractYear('created_at')
            ).values('month', 'year').annotate(
                count=Count('id')
            )
            
            for entry in new_data:
                year = entry['year']
                month_idx = entry['month'] - 1
                if year in result['new_memberships']:
                    result['new_memberships'][year][month_idx] = entry['count']
                    result['yearly_totals'][year]['new'] += entry['count']
            
            # Bajas (membresías que terminaron o fueron canceladas)
            # Usamos end_date para las que expiraron/cancelaron
            cancelled_data = ClientMembership.objects.filter(
                gym=self.gym,
                status__in=['CANCELLED', 'EXPIRED'],
                end_date__year__in=years,
                plan__is_membership=True
            ).annotate(
                month=ExtractMonth('end_date'),
                year=ExtractYear('end_date')
            ).values('month', 'year').annotate(
                count=Count('id')
            )
            
            for entry in cancelled_data:
                year = entry['year']
                month_idx = entry['month'] - 1
                if year in result['cancellations']:
                    result['cancellations'][year][month_idx] = entry['count']
                    result['yearly_totals'][year]['cancelled'] += entry['count']
            
            # Calcular net growth, churn y retention
            for year in years:
                for month in range(12):
                    new = result['new_memberships'][year][month]
                    cancelled = result['cancellations'][year][month]
                    result['net_growth'][year][month] = new - cancelled
                    result['yearly_totals'][year]['net'] += (new - cancelled)
                    
                    # Churn rate = cancelaciones / activos al inicio del mes
                    # Para simplicidad, usar el mes anterior como base
                    if month > 0:
                        prev_active = result['total_active'][year][month - 1]
                    else:
                        prev_active = ClientMembership.objects.filter(
                            gym=self.gym,
                            status='ACTIVE',
                            plan__is_membership=True,
                            start_date__lt=date(year, 1, 1)
                        ).count()
                    
                    if prev_active > 0:
                        churn = (cancelled / prev_active) * 100
                        result['churn_rate'][year][month] = round(churn, 2)
                        result['retention_rate'][year][month] = round(100 - churn, 2)
                    
                    # Total activo al final del mes
                    last_day = calendar.monthrange(year, month + 1)[1]
                    ref_date = date(year, month + 1, last_day)
                    
                    if ref_date <= timezone.now().date():
                        active_count = ClientMembership.objects.filter(
                            gym=self.gym,
                            status='ACTIVE',
                            plan__is_membership=True,
                            start_date__lte=ref_date
                        ).filter(
                            Q(end_date__gte=ref_date) | Q(end_date__isnull=True)
                        ).count()
                        result['total_active'][year][month] = active_count
                
                # Promedios anuales
                valid_churns = [c for c in result['churn_rate'][year] if c > 0]
                valid_retentions = [r for r in result['retention_rate'][year] if r > 0]
                
                result['yearly_totals'][year]['avg_churn'] = round(
                    sum(valid_churns) / len(valid_churns), 2
                ) if valid_churns else 0
                
                result['yearly_totals'][year]['avg_retention'] = round(
                    sum(valid_retentions) / len(valid_retentions), 2
                ) if valid_retentions else 0
            
            return result
        
        cache_key = f"membership_metrics_{'_'.join(map(str, years))}"
        return self._get_cached(cache_key, _calculate)
    
    def get_client_metrics(self, years=None):
        """
        Métricas de clientes: nuevos registros, estados, conversión lead->active.
        """
        if years is None:
            years = [self.current_year - 1, self.current_year]
        
        def _calculate():
            result = {
                'months': self.MONTH_NAMES_ES,
                'new_clients': {year: [0] * 12 for year in years},
                'new_leads': {year: [0] * 12 for year in years},
                'conversions': {year: [0] * 12 for year in years},
                'conversion_rate': {year: [0.0] * 12 for year in years},
                'total_clients': {year: 0 for year in years},
                'by_status': {year: {} for year in years}
            }
            
            # Nuevos clientes (activos)
            new_clients = Client.objects.filter(
                gym=self.gym,
                status='ACTIVE',
                created_at__year__in=years
            ).annotate(
                month=ExtractMonth('created_at'),
                year=ExtractYear('created_at')
            ).values('month', 'year').annotate(count=Count('id'))
            
            for entry in new_clients:
                year = entry['year']
                month_idx = entry['month'] - 1
                if year in result['new_clients']:
                    result['new_clients'][year][month_idx] = entry['count']
            
            # Nuevos leads
            new_leads = Client.objects.filter(
                gym=self.gym,
                status='LEAD',
                created_at__year__in=years
            ).annotate(
                month=ExtractMonth('created_at'),
                year=ExtractYear('created_at')
            ).values('month', 'year').annotate(count=Count('id'))
            
            for entry in new_leads:
                year = entry['year']
                month_idx = entry['month'] - 1
                if year in result['new_leads']:
                    result['new_leads'][year][month_idx] = entry['count']
            
            # Totales por año y estado
            for year in years:
                last_day = date(year, 12, 31) if year < self.current_year else timezone.now().date()
                
                status_counts = Client.objects.filter(
                    gym=self.gym,
                    created_at__year__lte=year
                ).values('status').annotate(count=Count('id'))
                
                result['by_status'][year] = {s['status']: s['count'] for s in status_counts}
                result['total_clients'][year] = sum(s['count'] for s in status_counts)
            
            return result
        
        cache_key = f"client_metrics_{'_'.join(map(str, years))}"
        return self._get_cached(cache_key, _calculate)
    
    # =========================================================================
    # ASISTENCIAS / CHECK-INS
    # =========================================================================
    
    def get_attendance_metrics(self, years=None):
        """
        Métricas de asistencias: check-ins, promedio por cliente, ocupación.
        """
        if years is None:
            years = [self.current_year - 1, self.current_year]
        
        def _calculate():
            result = {
                'months': self.MONTH_NAMES_ES,
                'total_checkins': {year: [0] * 12 for year in years},
                'unique_visitors': {year: [0] * 12 for year in years},
                'avg_visits_per_client': {year: [0.0] * 12 for year in years},
                'noshow_count': {year: [0] * 12 for year in years},
                'noshow_rate': {year: [0.0] * 12 for year in years},
                'yearly_totals': {
                    year: {'checkins': 0, 'unique': 0, 'noshows': 0}
                    for year in years
                }
            }
            
            # Check-ins totales
            checkins = ClientVisit.objects.filter(
                client__gym=self.gym,
                status='ATTENDED',
                date__year__in=years
            ).annotate(
                month=ExtractMonth('date'),
                year=ExtractYear('date')
            ).values('month', 'year').annotate(
                total=Count('id'),
                unique_clients=Count('client', distinct=True)
            )
            
            for entry in checkins:
                year = entry['year']
                month_idx = entry['month'] - 1
                if year in result['total_checkins']:
                    result['total_checkins'][year][month_idx] = entry['total']
                    result['unique_visitors'][year][month_idx] = entry['unique_clients']
                    result['yearly_totals'][year]['checkins'] += entry['total']
                    
                    if entry['unique_clients'] > 0:
                        avg = entry['total'] / entry['unique_clients']
                        result['avg_visits_per_client'][year][month_idx] = round(avg, 2)
            
            # No-shows
            noshows = ClientVisit.objects.filter(
                client__gym=self.gym,
                status='NOSHOW',
                date__year__in=years
            ).annotate(
                month=ExtractMonth('date'),
                year=ExtractYear('date')
            ).values('month', 'year').annotate(count=Count('id'))
            
            for entry in noshows:
                year = entry['year']
                month_idx = entry['month'] - 1
                if year in result['noshow_count']:
                    result['noshow_count'][year][month_idx] = entry['count']
                    result['yearly_totals'][year]['noshows'] += entry['count']
                    
                    # Calcular no-show rate
                    total_visits = result['total_checkins'][year][month_idx] + entry['count']
                    if total_visits > 0:
                        rate = (entry['count'] / total_visits) * 100
                        result['noshow_rate'][year][month_idx] = round(rate, 2)
            
            # Visitantes únicos anuales
            for year in years:
                unique = ClientVisit.objects.filter(
                    client__gym=self.gym,
                    status='ATTENDED',
                    date__year=year
                ).values('client').distinct().count()
                result['yearly_totals'][year]['unique'] = unique
            
            return result
        
        cache_key = f"attendance_metrics_{'_'.join(map(str, years))}"
        return self._get_cached(cache_key, _calculate)
    
    def get_class_occupancy(self, years=None):
        """
        Ocupación de clases grupales.
        """
        if years is None:
            years = [self.current_year - 1, self.current_year]
        
        def _calculate():
            result = {
                'months': self.MONTH_NAMES_ES,
                'avg_occupancy': {year: [0.0] * 12 for year in years},
                'total_sessions': {year: [0] * 12 for year in years},
                'total_attendees': {year: [0] * 12 for year in years},
                'yearly_avg_occupancy': {year: 0.0 for year in years}
            }
            
            # Query separada para sesiones y capacidad
            sessions = ActivitySession.objects.filter(
                gym=self.gym,
                status='COMPLETED',
                start_datetime__year__in=years,
                max_capacity__gt=0
            ).annotate(
                month=ExtractMonth('start_datetime'),
                year=ExtractYear('start_datetime'),
            ).values('month', 'year').annotate(
                total_sessions=Count('id'),
                total_capacity=Sum('max_capacity'),
                total_attendance=Count('attendees')  # Cuenta total de asistentes
            )
            
            for entry in sessions:
                year = entry['year']
                month_idx = entry['month'] - 1
                if year in result['avg_occupancy']:
                    result['total_sessions'][year][month_idx] = entry['total_sessions']
                    result['total_attendees'][year][month_idx] = entry['total_attendance'] or 0
                    
                    if entry['total_capacity'] and entry['total_capacity'] > 0:
                        occupancy = (entry['total_attendance'] or 0) / entry['total_capacity'] * 100
                        result['avg_occupancy'][year][month_idx] = round(occupancy, 2)
            
            # Promedio anual
            for year in years:
                valid_occupancies = [o for o in result['avg_occupancy'][year] if o > 0]
                if valid_occupancies:
                    result['yearly_avg_occupancy'][year] = round(
                        sum(valid_occupancies) / len(valid_occupancies), 2
                    )
            
            return result
        
        cache_key = f"class_occupancy_{'_'.join(map(str, years))}"
        return self._get_cached(cache_key, _calculate)
    
    # =========================================================================
    # PRODUCTOS / VENTAS
    # =========================================================================
    
    def get_product_sales(self, years=None, top_n=10):
        """
        Ventas de productos: total mensual y top productos.
        """
        if years is None:
            years = [self.current_year - 1, self.current_year]
        
        def _calculate():
            from django.contrib.contenttypes.models import ContentType
            
            result = {
                'months': self.MONTH_NAMES_ES,
                'sales': {year: [0.0] * 12 for year in years},
                'quantity': {year: [0] * 12 for year in years},
                'top_products': {year: [] for year in years},
                'yearly_totals': {year: {'revenue': 0.0, 'units': 0} for year in years}
            }
            
            try:
                product_ct = ContentType.objects.get_for_model(Product)
            except:
                return result
            
            # Ventas mensuales
            sales_data = OrderItem.objects.filter(
                order__gym=self.gym,
                order__status='PAID',
                content_type=product_ct,
                order__created_at__year__in=years
            ).annotate(
                month=ExtractMonth('order__created_at'),
                year=ExtractYear('order__created_at')
            ).values('month', 'year').annotate(
                total=Sum('subtotal'),
                units=Sum('quantity')
            )
            
            for entry in sales_data:
                year = entry['year']
                month_idx = entry['month'] - 1
                if year in result['sales']:
                    result['sales'][year][month_idx] = float(entry['total'] or 0)
                    result['quantity'][year][month_idx] = entry['units'] or 0
                    result['yearly_totals'][year]['revenue'] += float(entry['total'] or 0)
                    result['yearly_totals'][year]['units'] += entry['units'] or 0
            
            # Top productos por año
            for year in years:
                top = OrderItem.objects.filter(
                    order__gym=self.gym,
                    order__status='PAID',
                    content_type=product_ct,
                    order__created_at__year=year
                ).values('description').annotate(
                    total=Sum('subtotal'),
                    units=Sum('quantity')
                ).order_by('-total')[:top_n]
                
                result['top_products'][year] = [
                    {
                        'name': p['description'],
                        'revenue': float(p['total'] or 0),
                        'units': p['units'] or 0
                    }
                    for p in top
                ]
            
            return result
        
        cache_key = f"product_sales_{top_n}_{'_'.join(map(str, years))}"
        return self._get_cached(cache_key, _calculate)
    
    # =========================================================================
    # MÉTODOS DE PAGO
    # =========================================================================
    
    def get_payment_method_breakdown(self, years=None):
        """
        Desglose por método de pago.
        """
        if years is None:
            years = [self.current_year - 1, self.current_year]
        
        def _calculate():
            from sales.models import OrderPayment
            
            result = {
                'methods': [],
                'data': {year: {} for year in years},
                'percentages': {year: {} for year in years}
            }
            
            try:
                payments = OrderPayment.objects.filter(
                    order__gym=self.gym,
                    order__status='PAID',
                    order__created_at__year__in=years
                ).annotate(
                    year=ExtractYear('order__created_at')
                ).values('year', 'method__name').annotate(
                    total=Sum('amount'),
                    count=Count('id')
                )
                
                methods_set = set()
                for p in payments:
                    method_name = p['method__name'] or 'Sin especificar'
                    methods_set.add(method_name)
                    year = p['year']
                    if year in result['data']:
                        result['data'][year][method_name] = float(p['total'] or 0)
                
                result['methods'] = sorted(list(methods_set))
                
                # Calcular porcentajes
                for year in years:
                    total = sum(result['data'][year].values())
                    if total > 0:
                        for method in result['methods']:
                            amount = result['data'][year].get(method, 0)
                            result['percentages'][year][method] = round((amount / total) * 100, 2)
            except:
                pass
            
            return result
        
        cache_key = f"payment_methods_{'_'.join(map(str, years))}"
        return self._get_cached(cache_key, _calculate)
    
    # =========================================================================
    # MÉTRICAS AVANZADAS
    # =========================================================================
    
    def get_ltv_metrics(self, years=None):
        """
        Customer Lifetime Value (LTV) estimado.
        LTV = ARPC * Vida promedio del cliente (en meses)
        """
        if years is None:
            years = [self.current_year - 1, self.current_year]
        
        def _calculate():
            result = {
                'ltv': {year: 0.0 for year in years},
                'avg_customer_lifespan_months': {year: 0.0 for year in years},
                'arpc_monthly': {year: 0.0 for year in years}
            }
            
            for year in years:
                # ARPC mensual promedio
                arpc_data = self.get_arpc([year])
                valid_arpc = [a for a in arpc_data['arpc'][year] if a > 0]
                avg_arpc = sum(valid_arpc) / len(valid_arpc) if valid_arpc else 0
                result['arpc_monthly'][year] = round(avg_arpc, 2)
                
                # Vida promedio del cliente (meses entre primera y última compra)
                from django.db.models.functions import Coalesce
                
                client_lifespans = Order.objects.filter(
                    gym=self.gym,
                    status='PAID',
                    client__isnull=False,
                    created_at__year__lte=year
                ).values('client').annotate(
                    first_order=Min('created_at'),
                    last_order=Max('created_at')
                )
                
                total_months = 0
                count = 0
                for c in client_lifespans:
                    if c['first_order'] and c['last_order']:
                        diff = (c['last_order'] - c['first_order']).days / 30
                        total_months += max(1, diff)  # Mínimo 1 mes
                        count += 1
                
                avg_lifespan = total_months / count if count > 0 else 12
                result['avg_customer_lifespan_months'][year] = round(avg_lifespan, 2)
                
                # LTV = ARPC * Lifespan
                result['ltv'][year] = round(avg_arpc * avg_lifespan, 2)
            
            return result
        
        cache_key = f"ltv_metrics_{'_'.join(map(str, years))}"
        return self._get_cached(cache_key, _calculate)
    
    def get_peak_hours_analysis(self, year=None):
        """
        Análisis de horas pico de asistencia.
        """
        if year is None:
            year = self.current_year
        
        def _calculate():
            from django.db.models.functions import ExtractHour, ExtractWeekDay
            
            result = {
                'heatmap': {},  # {day: {hour: count}}
                'peak_hours': [],
                'peak_days': []
            }
            
            visits = ClientVisit.objects.filter(
                client__gym=self.gym,
                status='ATTENDED',
                date__year=year,
                check_in_time__isnull=False
            ).annotate(
                hour=ExtractHour('check_in_time'),
                weekday=ExtractWeekDay('date')
            ).values('weekday', 'hour').annotate(count=Count('id'))
            
            # Construir heatmap
            days = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
            heatmap = {day: {h: 0 for h in range(6, 23)} for day in days}
            
            hour_totals = defaultdict(int)
            day_totals = defaultdict(int)
            
            for v in visits:
                day_name = days[v['weekday'] - 1]  # Django weekday: 1=Sunday
                hour = v['hour']
                if 6 <= hour <= 22:
                    heatmap[day_name][hour] = v['count']
                    hour_totals[hour] += v['count']
                    day_totals[day_name] += v['count']
            
            result['heatmap'] = heatmap
            
            # Top 5 horas pico
            result['peak_hours'] = sorted(
                [{'hour': f"{h}:00", 'visits': c} for h, c in hour_totals.items()],
                key=lambda x: x['visits'],
                reverse=True
            )[:5]
            
            # Días más concurridos
            result['peak_days'] = sorted(
                [{'day': d, 'visits': c} for d, c in day_totals.items()],
                key=lambda x: x['visits'],
                reverse=True
            )
            
            return result
        
        cache_key = f"peak_hours_{year}"
        return self._get_cached(cache_key, _calculate)
    
    # =========================================================================
    # REPORTE COMPLETO
    # =========================================================================
    
    def get_full_comparative_report(self, years=None):
        """
        Genera el reporte comparativo completo con todas las métricas.
        """
        if years is None:
            years = [self.current_year - 2, self.current_year - 1, self.current_year]
        
        return {
            'gym': {
                'id': self.gym.id,
                'name': self.gym.name,
                'commercial_name': self.gym.commercial_name,
            },
            'years': years,
            'current_year': self.current_year,
            'current_month': self.current_month,
            'generated_at': timezone.now().isoformat(),
            
            # Métricas de Revenue
            'revenue': self.get_revenue_by_month(years),
            'revenue_by_category': self.get_revenue_by_category(years),
            'mrr_arr': self.get_mrr_arr(years),
            'arpc': self.get_arpc(years),
            
            # Métricas de Membresías
            'memberships': self.get_membership_metrics(years),
            'clients': self.get_client_metrics(years),
            
            # Métricas de Asistencia
            'attendance': self.get_attendance_metrics(years),
            'class_occupancy': self.get_class_occupancy(years),
            
            # Métricas de Productos
            'products': self.get_product_sales(years),
            
            # Métricas de Pagos
            'payment_methods': self.get_payment_method_breakdown(years),
            
            # Métricas Avanzadas
            'ltv': self.get_ltv_metrics(years),
            'peak_hours': self.get_peak_hours_analysis(self.current_year),
        }
    
    def get_kpi_summary(self, year=None):
        """
        Resumen de KPIs principales para el dashboard.
        """
        if year is None:
            year = self.current_year
        
        prev_year = year - 1
        
        revenue = self.get_revenue_by_month([prev_year, year])
        membership = self.get_membership_metrics([prev_year, year])
        attendance = self.get_attendance_metrics([prev_year, year])
        ltv = self.get_ltv_metrics([prev_year, year])
        mrr = self.get_mrr_arr([prev_year, year])
        
        # Calcular YTD (Year to Date)
        ytd_months = self.current_month if year == self.current_year else 12
        
        def sum_ytd(data, yr):
            return sum(data[yr][:ytd_months])
        
        def calc_growth(current, previous):
            if previous > 0:
                return round(((current - previous) / previous) * 100, 2)
            return 100.0 if current > 0 else 0.0
        
        current_revenue = sum_ytd(revenue['data'], year)
        prev_revenue = sum_ytd(revenue['data'], prev_year)
        
        current_checkins = sum_ytd(attendance['total_checkins'], year)
        prev_checkins = sum_ytd(attendance['total_checkins'], prev_year)
        
        current_new = sum_ytd(membership['new_memberships'], year)
        prev_new = sum_ytd(membership['new_memberships'], prev_year)
        
        # Último MRR disponible
        current_mrr = next((v for v in reversed(mrr['mrr'][year]) if v > 0), 0)
        prev_mrr = next((v for v in reversed(mrr['mrr'][prev_year]) if v > 0), 0)
        
        return {
            'year': year,
            'ytd_months': ytd_months,
            'kpis': {
                'revenue': {
                    'current': current_revenue,
                    'previous': prev_revenue,
                    'growth': calc_growth(current_revenue, prev_revenue),
                    'label': 'Facturación YTD'
                },
                'mrr': {
                    'current': current_mrr,
                    'previous': prev_mrr,
                    'growth': calc_growth(current_mrr, prev_mrr),
                    'label': 'MRR Actual'
                },
                'arr': {
                    'current': mrr['arr'][year],
                    'previous': mrr['arr'][prev_year],
                    'growth': calc_growth(mrr['arr'][year], mrr['arr'][prev_year]),
                    'label': 'ARR Proyectado'
                },
                'checkins': {
                    'current': current_checkins,
                    'previous': prev_checkins,
                    'growth': calc_growth(current_checkins, prev_checkins),
                    'label': 'Check-ins YTD'
                },
                'new_members': {
                    'current': current_new,
                    'previous': prev_new,
                    'growth': calc_growth(current_new, prev_new),
                    'label': 'Nuevas Altas YTD'
                },
                'churn_rate': {
                    'current': membership['yearly_totals'][year]['avg_churn'],
                    'previous': membership['yearly_totals'][prev_year]['avg_churn'],
                    'growth': calc_growth(
                        membership['yearly_totals'][prev_year]['avg_churn'],
                        membership['yearly_totals'][year]['avg_churn']
                    ),  # Invertido: menos churn es mejor
                    'label': 'Churn Rate Promedio'
                },
                'ltv': {
                    'current': ltv['ltv'][year],
                    'previous': ltv['ltv'][prev_year],
                    'growth': calc_growth(ltv['ltv'][year], ltv['ltv'][prev_year]),
                    'label': 'LTV Estimado'
                }
            }
        }
