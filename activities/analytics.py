"""
Analytics y reportes para el sistema de actividades y asistencias.
Inspirado en Mindbody, Glofox, WellnessLiving.
"""
from django.db.models import Count, Avg, Q, F, Sum, Max, Min, FloatField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, ExtractHour, ExtractWeekDay
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from collections import defaultdict

from .models import ActivitySession, Activity, Room
from clients.models import ClientVisit
from staff.models import StaffProfile


class AttendanceAnalytics:
    """Analytics para asistencias a clases"""
    
    def __init__(self, gym, start_date=None, end_date=None):
        self.gym = gym
        self.end_date = end_date or timezone.now()
        self.start_date = start_date or (self.end_date - timedelta(days=30))
    
    def get_heatmap_data(self):
        """
        Genera datos para heatmap de asistencia por día/hora.
        Returns: {day_of_week: {hour: attendance_count}}
        """
        sessions = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            status='COMPLETED'
        ).annotate(
            day_of_week=ExtractWeekDay('start_datetime'),
            hour=ExtractHour('start_datetime'),
            attendance=Count('attendees')
        ).values('day_of_week', 'hour', 'attendance')
        
        # Organizar en estructura de heatmap
        heatmap = defaultdict(lambda: defaultdict(int))
        for session in sessions:
            day = session['day_of_week']
            hour = session['hour']
            heatmap[day][hour] += session['attendance']
        
        return dict(heatmap)
    
    def get_peak_hours(self, top_n=5):
        """
        Identifica las franjas horarias con más asistencia.
        """
        peak_data = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            status='COMPLETED'
        ).annotate(
            hour=ExtractHour('start_datetime')
        ).values('hour').annotate(
            total_attendance=Count('attendees'),
            avg_attendance=Avg('attendees__id', output_field=FloatField()),
            session_count=Count('id')
        ).order_by('-total_attendance')[:top_n]
        
        return list(peak_data)
    
    def get_occupancy_rate(self):
        """
        Calcula tasa de ocupación promedio (% de aforo usado).
        """
        sessions = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            status='COMPLETED',
            max_capacity__gt=0
        ).annotate(
            attendance_count=Count('attendees')
        ).values('attendance_count', 'max_capacity')
        
        total_capacity = 0
        total_attendance = 0
        
        for session in sessions:
            total_capacity += session['max_capacity']
            total_attendance += session['attendance_count']
        
        if total_capacity == 0:
            return 0
        
        return round((total_attendance / total_capacity) * 100, 2)
    
    def get_attendance_trends(self, period='daily'):
        """
        Tendencias de asistencia en el tiempo.
        period: 'daily', 'weekly', 'monthly'
        """
        trunc_func = {
            'daily': TruncDate,
            'weekly': TruncWeek,
            'monthly': TruncMonth
        }.get(period, TruncDate)
        
        trends = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            status='COMPLETED'
        ).annotate(
            period=trunc_func('start_datetime')
        ).values('period').annotate(
            total_sessions=Count('id'),
            total_attendance=Count('attendees'),
            avg_attendance=Avg('attendees__id', output_field=FloatField()),
            occupancy_rate=Avg(
                F('attendees__id') * 100.0 / F('max_capacity'),
                output_field=FloatField()
            )
        ).order_by('period')
        
        return list(trends)
    
    def get_noshow_cancellation_rates(self):
        """
        Tasas de no-show y cancelaciones.
        """
        total_bookings = ClientVisit.objects.filter(
            client__gym=self.gym,
            date__gte=self.start_date.date(),
            date__lte=self.end_date.date()
        ).count()
        
        if total_bookings == 0:
            return {
                'total_bookings': 0,
                'attended': 0,
                'no_shows': 0,
                'cancelled': 0,
                'no_show_rate': 0,
                'cancellation_rate': 0,
                'attendance_rate': 0
            }
        
        stats = ClientVisit.objects.filter(
            client__gym=self.gym,
            date__gte=self.start_date.date(),
            date__lte=self.end_date.date()
        ).aggregate(
            attended=Count('id', filter=Q(status='ATTENDED')),
            no_shows=Count('id', filter=Q(status='NOSHOW')),
            cancelled=Count('id', filter=Q(status='CANCELLED'))
        )
        
        return {
            'total_bookings': total_bookings,
            'attended': stats['attended'],
            'no_shows': stats['no_shows'],
            'cancelled': stats['cancelled'],
            'no_show_rate': round((stats['no_shows'] / total_bookings) * 100, 2),
            'cancellation_rate': round((stats['cancelled'] / total_bookings) * 100, 2),
            'attendance_rate': round((stats['attended'] / total_bookings) * 100, 2)
        }
    
    def get_average_class_size(self):
        """
        Tamaño promedio de clase.
        """
        avg = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            status='COMPLETED'
        ).annotate(
            attendance_count=Count('attendees')
        ).aggregate(
            avg_size=Avg('attendance_count')
        )
        
        return round(avg['avg_size'] or 0, 2)


class StaffAnalytics:
    """Analytics para performance de instructores"""
    
    def __init__(self, gym, start_date=None, end_date=None):
        self.gym = gym
        self.end_date = end_date or timezone.now()
        self.start_date = start_date or (self.end_date - timedelta(days=30))
    
    def get_staff_performance(self, staff_id=None):
        """
        Performance detallado por instructor.
        """
        filters = {
            'gym': self.gym,
            'start_datetime__gte': self.start_date,
            'start_datetime__lte': self.end_date,
            'status': 'COMPLETED',
            'staff__isnull': False
        }
        
        if staff_id:
            filters['staff_id'] = staff_id
        
        staff_stats = ActivitySession.objects.filter(
            **filters
        ).values(
            'staff__id',
            'staff__user__first_name',
            'staff__user__last_name'
        ).annotate(
            classes_taught=Count('id'),
            total_attendance=Count('attendees'),
            avg_attendance=Avg('attendees__id', output_field=FloatField()),
            max_attendance=Max('attendees__id'),
            unique_clients=Count('attendees', distinct=True),
            avg_rating=Avg('reviews__instructor_rating', output_field=FloatField()),
            total_reviews=Count('reviews')
        ).order_by('-total_attendance')
        
        return list(staff_stats)
    
    def get_top_instructors(self, metric='attendance', top_n=10):
        """
        Top instructores por métrica específica.
        metrics: 'attendance', 'rating', 'classes', 'clients'
        """
        order_by_map = {
            'attendance': '-total_attendance',
            'rating': '-avg_rating',
            'classes': '-classes_taught',
            'clients': '-unique_clients'
        }
        
        order_field = order_by_map.get(metric, '-total_attendance')
        
        staff_data = self.get_staff_performance()
        
        # Ordenar y limitar
        sorted_staff = sorted(
            staff_data,
            key=lambda x: x.get(metric.replace('_', '_').replace('classes', 'classes_taught').replace('clients', 'unique_clients'), 0) or 0,
            reverse=True
        )[:top_n]
        
        return sorted_staff
    
    def get_staff_utilization(self):
        """
        Tasa de utilización de instructores (% de clases asignadas).
        """
        total_sessions = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date
        ).count()
        
        assigned_sessions = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            staff__isnull=False
        ).count()
        
        if total_sessions == 0:
            return 0
        
        return round((assigned_sessions / total_sessions) * 100, 2)
    
    def get_instructor_schedule_density(self, staff_id):
        """
        Densidad de clases por instructor (clases por día).
        """
        days = (self.end_date - self.start_date).days
        if days == 0:
            return 0
        
        classes_count = ActivitySession.objects.filter(
            gym=self.gym,
            staff_id=staff_id,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date
        ).count()
        
        return round(classes_count / days, 2)


class ActivityAnalytics:
    """Analytics para actividades/clases"""
    
    def __init__(self, gym, start_date=None, end_date=None):
        self.gym = gym
        self.end_date = end_date or timezone.now()
        self.start_date = start_date or (self.end_date - timedelta(days=30))
    
    def get_popular_activities(self, top_n=10):
        """
        Actividades más populares por asistencia.
        """
        activities = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            status='COMPLETED'
        ).values(
            'activity__id',
            'activity__name',
            'activity__category__name'
        ).annotate(
            sessions_count=Count('id'),
            total_attendance=Count('attendees'),
            avg_attendance=Avg('attendees__id', output_field=FloatField()),
            unique_clients=Count('attendees', distinct=True),
            avg_rating=Avg('reviews__class_rating', output_field=FloatField()),
            occupancy_rate=Avg(
                F('attendees__id') * 100.0 / F('max_capacity'),
                output_field=FloatField()
            )
        ).order_by('-total_attendance')[:top_n]
        
        return list(activities)
    
    def get_activity_trends(self, activity_id, period='weekly'):
        """
        Tendencias de una actividad específica en el tiempo.
        """
        trunc_func = {
            'daily': TruncDate,
            'weekly': TruncWeek,
            'monthly': TruncMonth
        }.get(period, TruncWeek)
        
        trends = ActivitySession.objects.filter(
            gym=self.gym,
            activity_id=activity_id,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            status='COMPLETED'
        ).annotate(
            period=trunc_func('start_datetime')
        ).values('period').annotate(
            sessions=Count('id'),
            attendance=Count('attendees'),
            avg_attendance=Avg('attendees__id', output_field=FloatField())
        ).order_by('period')
        
        return list(trends)
    
    def get_time_slot_performance(self):
        """
        Performance por franja horaria para todas las actividades.
        """
        time_slots = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            status='COMPLETED'
        ).annotate(
            hour=ExtractHour('start_datetime')
        ).values('hour', 'activity__name').annotate(
            sessions=Count('id'),
            attendance=Count('attendees'),
            avg_attendance=Avg('attendees__id', output_field=FloatField())
        ).order_by('hour', '-attendance')
        
        return list(time_slots)
    
    def get_room_utilization(self):
        """
        Utilización de salas.
        """
        room_stats = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            room__isnull=False
        ).values(
            'room__id',
            'room__name'
        ).annotate(
            sessions_count=Count('id'),
            total_attendance=Count('attendees'),
            avg_attendance=Avg('attendees__id', output_field=FloatField()),
            occupancy_rate=Avg(
                F('attendees__id') * 100.0 / F('max_capacity'),
                output_field=FloatField()
            )
        ).order_by('-sessions_count')
        
        return list(room_stats)
    
    def get_cross_class_patterns(self, top_n=10):
        """
        Patrones de asistencia cruzada: qué clases suelen asistir los mismos clientes.
        """
        from django.db.models import Subquery, OuterRef
        
        # Obtener clientes que asisten a múltiples tipos de clases
        client_activities = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            status='COMPLETED'
        ).values('attendees', 'activity__name').distinct()
        
        # Agrupar por combinaciones de actividades
        patterns = defaultdict(int)
        client_classes = defaultdict(set)
        
        for record in client_activities:
            if record['attendees'] and record['activity__name']:
                client_classes[record['attendees']].add(record['activity__name'])
        
        # Contar combinaciones
        for client_id, classes in client_classes.items():
            if len(classes) > 1:
                classes_list = sorted(list(classes))
                for i, class1 in enumerate(classes_list):
                    for class2 in classes_list[i+1:]:
                        pair = f"{class1} + {class2}"
                        patterns[pair] += 1
        
        # Ordenar y tomar top N
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        return [{'combination': pair, 'count': count} for pair, count in sorted_patterns]


class AdvancedAnalytics:
    """Analytics avanzados y predictivos"""
    
    def __init__(self, gym, start_date=None, end_date=None):
        self.gym = gym
        self.end_date = end_date or timezone.now()
        self.start_date = start_date or (self.end_date - timedelta(days=90))  # 90 días para análisis avanzado
    
    def get_booking_lead_time(self):
        """
        Análisis de anticipación de reservas.
        ¿Con cuánta anticipación reservan los clientes?
        """
        # Requeriría un campo booking_datetime en ClientVisit
        # Por ahora, aproximación con created_at
        visits = ClientVisit.objects.filter(
            client__gym=self.gym,
            date__gte=self.start_date.date(),
            date__lte=self.end_date.date(),
            status__in=['ATTENDED', 'SCHEDULED']
        ).values('created_at', 'date')
        
        lead_times = []
        for visit in visits:
            if visit['created_at'] and visit['date']:
                lead_time_days = (visit['date'] - visit['created_at'].date()).days
                if lead_time_days >= 0:  # Solo adelantadas
                    lead_times.append(lead_time_days)
        
        if not lead_times:
            return {
                'avg_lead_days': 0,
                'median_lead_days': 0,
                'same_day_bookings': 0,
                'advance_bookings': 0
            }
        
        lead_times.sort()
        median_idx = len(lead_times) // 2
        
        return {
            'avg_lead_days': round(sum(lead_times) / len(lead_times), 2),
            'median_lead_days': lead_times[median_idx],
            'same_day_bookings': lead_times.count(0),
            'advance_bookings': len([lt for lt in lead_times if lt > 0]),
            'distribution': {
                'same_day': lead_times.count(0),
                'days_1_3': len([lt for lt in lead_times if 1 <= lt <= 3]),
                'days_4_7': len([lt for lt in lead_times if 4 <= lt <= 7]),
                'days_8_plus': len([lt for lt in lead_times if lt > 7])
            }
        }
    
    def get_seasonal_patterns(self):
        """
        Patrones estacionales: qué días de la semana y meses son más populares.
        Calcula correctamente el promedio de asistencia por día de la semana.
        """
        # Primero obtenemos cada sesión con su día de semana y cuenta de asistentes
        sessions_with_attendance = ActivitySession.objects.filter(
            gym=self.gym,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            status='COMPLETED'
        ).annotate(
            day_of_week=ExtractWeekDay('start_datetime'),
            attendance_count=Count('attendees')
        ).values('day_of_week', 'attendance_count')
        
        # Agrupar por día de la semana
        from collections import defaultdict
        day_stats = defaultdict(lambda: {'sessions': 0, 'total_attendance': 0})
        
        for session in sessions_with_attendance:
            dow = session['day_of_week']
            day_stats[dow]['sessions'] += 1
            day_stats[dow]['total_attendance'] += session['attendance_count']
        
        day_names = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
        
        results = []
        for day_num in sorted(day_stats.keys()):
            stats = day_stats[day_num]
            avg = stats['total_attendance'] / stats['sessions'] if stats['sessions'] > 0 else 0
            results.append({
                'day_of_week': day_num,
                'day_name': day_names[day_num - 1] if 1 <= day_num <= 7 else 'Unknown',
                'sessions': stats['sessions'],
                'attendance': stats['total_attendance'],
                'avg_attendance': round(avg, 1)
            })
        
        # Ordenar por promedio de asistencia descendente para mostrar el mejor día primero
        results.sort(key=lambda x: x['avg_attendance'], reverse=True)
        
        return results
    
    def predict_attendance(self, activity_id, day_of_week, hour):
        """
        Predicción de asistencia basada en históricos.
        Usa el promedio de sesiones con condiciones similares (misma actividad, día, hora).
        """
        # Obtener sesiones similares con su conteo de asistentes
        similar_sessions = ActivitySession.objects.filter(
            gym=self.gym,
            activity_id=activity_id,
            start_datetime__gte=self.start_date,
            start_datetime__lte=self.end_date,
            status='COMPLETED'
        ).annotate(
            dow=ExtractWeekDay('start_datetime'),
            hr=ExtractHour('start_datetime'),
            attendance_count=Count('attendees')
        ).filter(
            dow=day_of_week,
            hr=hour
        ).values('attendance_count')
        
        attendance_values = [s['attendance_count'] for s in similar_sessions]
        
        if not attendance_values:
            # Si no hay datos exactos, buscar con condiciones más amplias
            # Solo por actividad y día de la semana
            broader_sessions = ActivitySession.objects.filter(
                gym=self.gym,
                activity_id=activity_id,
                start_datetime__gte=self.start_date,
                start_datetime__lte=self.end_date,
                status='COMPLETED'
            ).annotate(
                dow=ExtractWeekDay('start_datetime'),
                attendance_count=Count('attendees')
            ).filter(
                dow=day_of_week
            ).values('attendance_count')
            
            attendance_values = [s['attendance_count'] for s in broader_sessions]
        
        if not attendance_values:
            return {
                'predicted_attendance': 0,
                'min_expected': 0,
                'max_expected': 0,
                'confidence': 'low'
            }
        
        avg_attendance = sum(attendance_values) / len(attendance_values)
        min_attendance = min(attendance_values)
        max_attendance = max(attendance_values)
        
        # Calcular confianza basada en la variabilidad y cantidad de datos
        variance = max_attendance - min_attendance
        confidence = 'low'
        if len(attendance_values) >= 10 and variance <= 5:
            confidence = 'high'
        elif len(attendance_values) >= 5 and variance <= 8:
            confidence = 'medium'
        
        return {
            'predicted_attendance': round(avg_attendance, 1),
            'min_expected': min_attendance,
            'max_expected': max_attendance,
            'confidence': confidence
        }
    
    def get_member_retention_by_class(self):
        """
        Retención de clientes por tipo de clase.
        ¿Qué clases tienen clientes más fieles?
        """
        # Clientes que han asistido más de una vez a cada actividad
        repeat_attendance = ClientVisit.objects.filter(
            client__gym=self.gym,
            date__gte=self.start_date.date(),
            date__lte=self.end_date.date(),
            status='ATTENDED'
        ).values('client_id', 'concept').annotate(
            visits=Count('id')
        ).filter(visits__gt=1)
        
        # Agrupar por concepto (actividad)
        retention_by_activity = defaultdict(lambda: {'total_clients': 0, 'repeat_clients': 0})
        
        for record in repeat_attendance:
            concept = record['concept']
            retention_by_activity[concept]['repeat_clients'] += 1
        
        # Total de clientes únicos por actividad
        all_clients = ClientVisit.objects.filter(
            client__gym=self.gym,
            date__gte=self.start_date.date(),
            date__lte=self.end_date.date(),
            status='ATTENDED'
        ).values('concept').annotate(
            unique_clients=Count('client_id', distinct=True)
        )
        
        for record in all_clients:
            concept = record['concept']
            retention_by_activity[concept]['total_clients'] = record['unique_clients']
        
        # Calcular tasas de retención
        results = []
        for concept, stats in retention_by_activity.items():
            if stats['total_clients'] > 0 and concept:  # Ignorar conceptos vacíos
                retention_rate = (stats['repeat_clients'] / stats['total_clients']) * 100
                results.append({
                    'activity__name': concept,  # Nombre esperado por el template
                    'total_clients': stats['total_clients'],
                    'repeat_clients': stats['repeat_clients'],
                    'repeat_rate': round(retention_rate, 2)  # Nombre esperado por el template
                })
        
        results.sort(key=lambda x: x['repeat_rate'], reverse=True)
        return results
