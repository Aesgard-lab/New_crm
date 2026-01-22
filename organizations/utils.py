"""
Utilidades para manejo de horarios de apertura y festivos
"""
from datetime import time
from .models import GymOpeningHours, GymHoliday


def is_gym_open(gym, date, check_time=None):
    """
    Verifica si el gym está abierto en una fecha/hora específica.
    
    Args:
        gym: Instancia de Gym
        date: datetime.date
        check_time: datetime.time (opcional, si no se proporciona verifica todo el día)
    
    Returns:
        dict: {
            'is_open': bool,
            'reason': str,
            'is_holiday': bool,
            'override_allowed': bool,
            'hours': {'open': time, 'close': time} o None
        }
    """
    
    # 1. Verificar si es festivo
    holiday = GymHoliday.objects.filter(gym=gym, date=date).first()
    
    if holiday:
        if holiday.is_closed:
            return {
                'is_open': False,
                'reason': f'Gym cerrado: {holiday.name}',
                'is_holiday': True,
                'override_allowed': holiday.allow_classes,
                'hours': None,
            }
        elif holiday.special_open and holiday.special_close:
            # Horario especial en festivo
            if check_time:
                is_open_today = holiday.special_open <= check_time <= holiday.special_close
            else:
                is_open_today = True
            
            return {
                'is_open': is_open_today,
                'reason': 'Horario especial en festivo',
                'is_holiday': True,
                'override_allowed': False,
                'hours': {'open': holiday.special_open, 'close': holiday.special_close},
            }
    
    # 2. Si no es festivo, usar horarios regulares
    try:
        opening_hours = gym.opening_hours
    except GymOpeningHours.DoesNotExist:
        return {
            'is_open': True,  # Sin configuración = siempre abierto
            'reason': 'Sin horarios configurados',
            'is_holiday': False,
            'override_allowed': False,
            'hours': None,
        }
    
    # Obtener horas del día
    day_of_week = date.weekday()  # 0=Lunes, 6=Domingo
    hours = opening_hours.get_hours_for_day(day_of_week)
    
    if not hours:
        return {
            'is_open': False,
            'reason': 'Gym cerrado este día',
            'is_holiday': False,
            'override_allowed': False,
            'hours': None,
        }
    
    # Verificar hora específica si se proporciona
    if check_time:
        is_open_now = hours['open'] <= check_time <= hours['close']
    else:
        is_open_now = True
    
    return {
        'is_open': is_open_now,
        'reason': f"Abierto {hours['open'].strftime('%H:%M')} - {hours['close'].strftime('%H:%M')}",
        'is_holiday': False,
        'override_allowed': False,
        'hours': hours,
    }


def can_schedule_class(gym, date, start_time, end_time=None, force=False):
    """
    Verifica si se puede programar una clase en una fecha/hora.
    
    Args:
        gym: Instancia de Gym
        date: datetime.date
        start_time: datetime.time (hora de inicio)
        end_time: datetime.time (hora de fin, opcional)
        force: bool (si True, intenta forzar en festivos con allow_classes=True)
    
    Returns:
        dict: {
            'can_schedule': bool,
            'message': str,
            'is_forced': bool,
            'is_holiday': bool
        }
    """
    
    # Verificar apertura del gym
    check_result = is_gym_open(gym, date, start_time)
    
    if check_result['is_open']:
        # Gym abierto en esa hora
        return {
            'can_schedule': True,
            'message': 'OK - Gym abierto',
            'is_forced': False,
            'is_holiday': False,
        }
    
    # Gym cerrado
    if check_result['is_holiday']:
        if force and check_result['override_allowed']:
            # Se permite forzar en este festivo
            return {
                'can_schedule': True,
                'message': '⚠️ Clase forzada en festivo',
                'is_forced': True,
                'is_holiday': True,
            }
        else:
            return {
                'can_schedule': False,
                'message': f"❌ {check_result['reason']}",
                'is_forced': False,
                'is_holiday': True,
            }
    
    # Horario regular cerrado
    return {
        'can_schedule': False,
        'message': f"❌ Fuera de horario: {check_result['reason']}",
        'is_forced': False,
        'is_holiday': False,
    }


def get_gym_holidays(gym, year=None, month=None):
    """
    Obtiene los festivos de un gym.
    
    Args:
        gym: Instancia de Gym
        year: int (opcional, filtro por año)
        month: int (opcional, filtro por mes)
    
    Returns:
        QuerySet de GymHoliday
    """
    queryset = GymHoliday.objects.filter(gym=gym)
    
    if year:
        queryset = queryset.filter(date__year=year)
    
    if month:
        queryset = queryset.filter(date__month=month)
    
    return queryset.order_by('date')


def get_gym_hours(gym):
    """
    Obtiene los horarios de un gym en formato legible.
    
    Args:
        gym: Instancia de Gym
    
    Returns:
        dict: {
            'lunes': '6:00 - 22:00',
            'martes': '6:00 - 22:00',
            ...
        }
    """
    
    try:
        opening_hours = gym.opening_hours
    except GymOpeningHours.DoesNotExist:
        return None
    
    days = [
        ('monday', 'Lunes'),
        ('tuesday', 'Martes'),
        ('wednesday', 'Miércoles'),
        ('thursday', 'Jueves'),
        ('friday', 'Viernes'),
        ('saturday', 'Sábado'),
        ('sunday', 'Domingo'),
    ]
    
    result = {}
    for day_code, day_label in days:
        hours = opening_hours.get_hours_for_day(days.index((day_code, day_label)))
        if hours:
            result[day_label] = f"{hours['open'].strftime('%H:%M')} - {hours['close'].strftime('%H:%M')}"
        else:
            result[day_label] = 'Cerrado'
    
    return result


def get_occupancy_stats(gym, staff_member, start_date, end_date):
    """
    Obtiene estadísticas de ocupación de un instructor en un periodo.
    
    Args:
        gym: Instancia de Gym
        staff_member: Instancia de StaffMember
        start_date: datetime.date
        end_date: datetime.date
    
    Returns:
        dict: {
            'total_classes': int,
            'total_hours': float,
            'total_students': int,
            'avg_occupancy': float (0-100%),
            'classes': [{...}]
        }
    """
    from activities.models import Schedule
    from django.db.models import Q
    from datetime import datetime
    
    # Obtener clases del instructor en el periodo
    classes = Schedule.objects.filter(
        gym=gym,
        instructor=staff_member,
        date__gte=start_date,
        date__lte=end_date
    ).select_related('activity')
    
    total_classes = classes.count()
    total_hours = 0
    total_students = 0
    total_capacity = 0
    
    classes_list = []
    
    for cls in classes:
        # Calcular duración
        if hasattr(cls, 'duration'):
            duration = cls.duration
        else:
            duration = 1  # 1 hora por defecto
        
        total_hours += duration
        
        # Contar estudiantes inscritos
        enrolled = cls.members.count()
        total_students += enrolled
        
        capacity = cls.activity.max_capacity if hasattr(cls.activity, 'max_capacity') else 20
        total_capacity += capacity
        occupancy = (enrolled / capacity * 100) if capacity > 0 else 0
        
        classes_list.append({
            'date': cls.date,
            'time': str(cls.start_time),
            'activity': cls.activity.name if hasattr(cls, 'activity') else 'N/A',
            'room': cls.room if hasattr(cls, 'room') else 'N/A',
            'capacity': capacity,
            'enrolled': enrolled,
            'occupancy': round(occupancy, 1),
        })
    
    avg_occupancy = (total_students / total_capacity * 100) if total_capacity > 0 else 0
    
    return {
        'total_classes': total_classes,
        'total_hours': total_hours,
        'total_students': total_students,
        'avg_occupancy': round(avg_occupancy, 1),
        'classes': classes_list,
    }
