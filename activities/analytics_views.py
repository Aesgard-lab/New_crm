"""
Vistas de reportes y analytics para actividades.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q

from .analytics import AttendanceAnalytics, StaffAnalytics, ActivityAnalytics, AdvancedAnalytics
from .models import Activity, ActivitySession
from staff.models import StaffProfile
from accounts.decorators import require_gym_permission


@login_required
@require_gym_permission('activities.view_activitysession')
def analytics_dashboard(request):
    """
    Dashboard principal de analytics.
    """
    gym = request.gym
    
    # Período por defecto: últimos 30 días
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    # Obtener parámetros de filtro
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
        start_date = timezone.make_aware(start_date)
    
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
        end_date = timezone.make_aware(end_date)
    
    # Inicializar analytics
    attendance_analytics = AttendanceAnalytics(gym, start_date, end_date)
    staff_analytics = StaffAnalytics(gym, start_date, end_date)
    activity_analytics = ActivityAnalytics(gym, start_date, end_date)
    
    # Datos principales
    context = {
        'gym': gym,
        'start_date': start_date,
        'end_date': end_date,
        
        # KPIs principales
        'occupancy_rate': attendance_analytics.get_occupancy_rate(),
        'avg_class_size': attendance_analytics.get_average_class_size(),
        'staff_utilization': staff_analytics.get_staff_utilization(),
        
        # Datos para gráficas
        'peak_hours': attendance_analytics.get_peak_hours(top_n=10),
        'popular_activities': activity_analytics.get_popular_activities(top_n=10),
        'top_instructors': staff_analytics.get_top_instructors(metric='attendance', top_n=10),
        
        # Tasas
        'noshow_rates': attendance_analytics.get_noshow_cancellation_rates(),
        
        # Listas para filtros
        'activities': Activity.objects.filter(gym=gym),
        'staff_list': StaffProfile.objects.filter(gym=gym, is_active=True)
    }
    
    return render(request, 'activities/analytics_dashboard.html', context)


@login_required
@require_gym_permission('activities.view_activitysession')
def attendance_report(request):
    """
    Reporte detallado de asistencias.
    """
    gym = request.gym
    
    # Parámetros de filtro
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
        start_date = timezone.make_aware(start_date)
    
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
        end_date = timezone.make_aware(end_date)
    
    period = request.GET.get('period', 'daily')  # daily, weekly, monthly
    
    analytics = AttendanceAnalytics(gym, start_date, end_date)
    
    context = {
        'gym': gym,
        'start_date': start_date,
        'end_date': end_date,
        'period': period,
        
        # Datos de asistencia
        'heatmap_data': analytics.get_heatmap_data(),
        'trends': analytics.get_attendance_trends(period=period),
        'peak_hours': analytics.get_peak_hours(top_n=10),
        'occupancy_rate': analytics.get_occupancy_rate(),
        'avg_class_size': analytics.get_average_class_size(),
        'noshow_rates': analytics.get_noshow_cancellation_rates(),
    }
    
    return render(request, 'activities/reports/attendance_report.html', context)


@login_required
@require_gym_permission('activities.view_activitysession')
def staff_report(request):
    """
    Reporte de performance de instructores.
    """
    gym = request.gym
    
    # Parámetros
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
        start_date = timezone.make_aware(start_date)
    
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
        end_date = timezone.make_aware(end_date)
    
    staff_id = request.GET.get('staff_id')
    
    analytics = StaffAnalytics(gym, start_date, end_date)
    
    context = {
        'gym': gym,
        'start_date': start_date,
        'end_date': end_date,
        'selected_staff_id': staff_id,
        
        # Datos de staff
        'staff_performance': analytics.get_staff_performance(staff_id=staff_id),
        'top_by_attendance': analytics.get_top_instructors(metric='attendance', top_n=10),
        'top_by_rating': analytics.get_top_instructors(metric='rating', top_n=10),
        'staff_utilization': analytics.get_staff_utilization(),
        
        # Lista de staff para filtro
        'staff_list': StaffProfile.objects.filter(gym=gym, is_active=True)
    }
    
    return render(request, 'activities/reports/staff_report.html', context)


@login_required
@require_gym_permission('activities.view_activitysession')
def activity_report(request):
    """
    Reporte de actividades/clases.
    """
    gym = request.gym
    
    # Parámetros
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
        start_date = timezone.make_aware(start_date)
    
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
        end_date = timezone.make_aware(end_date)
    
    activity_id = request.GET.get('activity_id')
    period = request.GET.get('period', 'weekly')
    
    analytics = ActivityAnalytics(gym, start_date, end_date)
    
    context = {
        'gym': gym,
        'start_date': start_date,
        'end_date': end_date,
        'selected_activity_id': activity_id,
        'period': period,
        
        # Datos de actividades
        'popular_activities': analytics.get_popular_activities(top_n=15),
        'time_slot_performance': analytics.get_time_slot_performance(),
        'room_utilization': analytics.get_room_utilization(),
        'cross_class_patterns': analytics.get_cross_class_patterns(top_n=10),
        
        # Si hay actividad seleccionada, mostrar tendencias
        'activity_trends': analytics.get_activity_trends(activity_id, period) if activity_id else None,
        
        # Lista de actividades para filtro
        'activities': Activity.objects.filter(gym=gym)
    }
    
    return render(request, 'activities/reports/activity_report.html', context)


@login_required
@require_gym_permission('activities.view_activitysession')
def advanced_analytics(request):
    """
    Analytics avanzados y predictivos.
    """
    gym = request.gym
    
    # Período más amplio para análisis avanzado
    end_date = timezone.now()
    start_date = end_date - timedelta(days=90)
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
        start_date = timezone.make_aware(start_date)
    
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
        end_date = timezone.make_aware(end_date)
    
    analytics = AdvancedAnalytics(gym, start_date, end_date)
    
    context = {
        'gym': gym,
        'start_date': start_date,
        'end_date': end_date,
        
        # Analytics avanzados
        'booking_lead_time': analytics.get_booking_lead_time(),
        'seasonal_patterns': analytics.get_seasonal_patterns(),
        'member_retention': analytics.get_member_retention_by_class(),
        
        # Lista de actividades para predicción
        'activities': Activity.objects.filter(gym=gym)
    }
    
    return render(request, 'activities/reports/advanced_analytics.html', context)


# === API Endpoints para gráficas AJAX ===

@login_required
@require_gym_permission('activities.view_activitysession')
def api_heatmap_data(request):
    """
    API endpoint para datos de heatmap.
    """
    gym = request.gym
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
        start_date = timezone.make_aware(start_date)
    
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
        end_date = timezone.make_aware(end_date)
    
    analytics = AttendanceAnalytics(gym, start_date, end_date)
    heatmap_data = analytics.get_heatmap_data()
    
    # Formatear para Chart.js/heatmap library
    formatted_data = []
    day_names = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
    
    for day, hours in heatmap_data.items():
        for hour, count in hours.items():
            formatted_data.append({
                'x': f"{hour}:00",
                'y': day_names[day - 1] if 1 <= day <= 7 else 'Unknown',
                'value': count
            })
    
    return JsonResponse({'data': formatted_data})


@login_required
@require_gym_permission('activities.view_activitysession')
def api_attendance_trends(request):
    """
    API endpoint para tendencias de asistencia.
    """
    gym = request.gym
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    period = request.GET.get('period', 'daily')
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
        start_date = timezone.make_aware(start_date)
    
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
        end_date = timezone.make_aware(end_date)
    
    analytics = AttendanceAnalytics(gym, start_date, end_date)
    trends = analytics.get_attendance_trends(period=period)
    
    # Formatear para Chart.js
    labels = [str(t['period']) for t in trends]
    datasets = [
        {
            'label': 'Total Asistencia',
            'data': [t['total_attendance'] for t in trends],
            'borderColor': 'rgb(75, 192, 192)',
            'tension': 0.1
        },
        {
            'label': 'Promedio por Clase',
            'data': [round(t['avg_attendance'] or 0, 1) for t in trends],
            'borderColor': 'rgb(255, 99, 132)',
            'tension': 0.1
        }
    ]
    
    return JsonResponse({'labels': labels, 'datasets': datasets})


@login_required
@require_gym_permission('activities.view_activitysession')
def api_predict_attendance(request):
    """
    API endpoint para predicción de asistencia.
    """
    gym = request.gym
    
    activity_id = request.GET.get('activity_id')
    day_of_week = int(request.GET.get('day_of_week', 1))
    hour = int(request.GET.get('hour', 10))
    
    if not activity_id:
        return JsonResponse({'error': 'activity_id required'}, status=400)
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=90)
    
    analytics = AdvancedAnalytics(gym, start_date, end_date)
    prediction = analytics.predict_attendance(activity_id, day_of_week, hour)
    
    return JsonResponse(prediction)


@login_required
@require_gym_permission('activities.view_activitysession')
def export_report_csv(request):
    """
    Exportar reporte a CSV.
    """
    import csv
    from django.http import HttpResponse
    
    gym = request.gym
    report_type = request.GET.get('type', 'attendance')
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
        start_date = timezone.make_aware(start_date)
    
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
        end_date = timezone.make_aware(end_date)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{start_date.date()}_to_{end_date.date()}.csv"'
    
    writer = csv.writer(response)
    
    if report_type == 'staff':
        analytics = StaffAnalytics(gym, start_date, end_date)
        data = analytics.get_staff_performance()
        
        writer.writerow(['Instructor', 'Clases Impartidas', 'Asistencia Total', 'Promedio Asistencia', 'Clientes Únicos', 'Rating Promedio'])
        for row in data:
            writer.writerow([
                f"{row['staff__user__first_name']} {row['staff__user__last_name']}",
                row['classes_taught'],
                row['total_attendance'],
                round(row['avg_attendance'] or 0, 2),
                row['unique_clients'],
                round(row['avg_rating'] or 0, 2)
            ])
    
    elif report_type == 'activities':
        analytics = ActivityAnalytics(gym, start_date, end_date)
        data = analytics.get_popular_activities(top_n=50)
        
        writer.writerow(['Actividad', 'Categoría', 'Sesiones', 'Asistencia Total', 'Promedio Asistencia', 'Ocupación %', 'Rating'])
        for row in data:
            writer.writerow([
                row['activity__name'],
                row['activity__category__name'] or 'Sin categoría',
                row['sessions_count'],
                row['total_attendance'],
                round(row['avg_attendance'] or 0, 2),
                round(row['occupancy_rate'] or 0, 2),
                round(row['avg_rating'] or 0, 2)
            ])
    
    else:  # attendance
        analytics = AttendanceAnalytics(gym, start_date, end_date)
        trends = analytics.get_attendance_trends(period='daily')
        
        writer.writerow(['Fecha', 'Sesiones', 'Asistencia Total', 'Promedio por Clase', 'Ocupación %'])
        for row in trends:
            writer.writerow([
                row['period'],
                row['total_sessions'],
                row['total_attendance'],
                round(row['avg_attendance'] or 0, 2),
                round(row['occupancy_rate'] or 0, 2)
            ])
    
    return response
