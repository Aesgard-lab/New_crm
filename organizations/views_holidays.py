"""
Views para gestión de horarios y festivos
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
import json

from organizations.models import Gym, GymOpeningHours, GymHoliday
from finance.forms import GymOpeningHoursForm
from django import forms


class GymHolidayForm(forms.ModelForm):
    """Formulario para agregar/editar festivos"""
    
    class Meta:
        model = GymHoliday
        fields = ['date', 'name', 'is_closed', 'allow_classes', 'special_open', 'special_close']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'name': forms.TextInput(attrs={'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500', 'placeholder': 'ej: Navidad'}),
            'is_closed': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-blue-600'}),
            'allow_classes': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-blue-600'}),
            'special_open': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
            'special_close': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded-lg border-slate-200 focus:ring-blue-500'}),
        }
        labels = {
            'date': 'Fecha del Festivo',
            'name': 'Nombre del Festivo',
            'is_closed': '¿Gym Cerrado?',
            'allow_classes': 'Permitir Clases Forzadas',
            'special_open': 'Hora de Apertura (si abre)',
            'special_close': 'Hora de Cierre (si abre)',
        }


@login_required
def gym_holidays_list(request):
    """
    Lista los festivos configurados para el gym actual.
    """
    gym = getattr(request, 'gym', None)
    if not gym:
        messages.error(request, 'Gym no encontrado')
        return redirect('backoffice_dashboard')
    
    # Obtener festivos del año actual y próximo
    today = datetime.now().date()
    holidays = GymHoliday.objects.filter(
        gym=gym,
        date__gte=today - timedelta(days=30)  # Últimos 30 días
    ).order_by('date')
    
    context = {
        'title': 'Gestión de Festivos',
        'gym': gym,
        'holidays': holidays,
        'today': today,
    }
    
    return render(request, 'backoffice/gym/holidays_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def gym_holiday_create(request):
    """
    Crear un nuevo festivo.
    """
    gym = getattr(request, 'gym', None)
    if not gym:
        messages.error(request, 'Gym no encontrado')
        return redirect('backoffice_dashboard')
    
    if request.method == 'POST':
        form = GymHolidayForm(request.POST)
        if form.is_valid():
            holiday = form.save(commit=False)
            holiday.gym = gym
            holiday.save()
            messages.success(request, f'✅ Festivo "{holiday.name}" creado correctamente')
            return redirect('gym_holidays_list')
    else:
        form = GymHolidayForm()
    
    context = {
        'title': 'Agregar Festivo',
        'form': form,
        'gym': gym,
    }
    
    return render(request, 'backoffice/gym/holiday_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def gym_holiday_edit(request, holiday_id):
    """
    Editar un festivo existente.
    """
    gym = getattr(request, 'gym', None)
    if not gym:
        messages.error(request, 'Gym no encontrado')
        return redirect('backoffice_dashboard')
    
    try:
        holiday = GymHoliday.objects.get(id=holiday_id, gym=gym)
    except GymHoliday.DoesNotExist:
        messages.error(request, 'Festivo no encontrado')
        return redirect('gym_holidays_list')
    
    if request.method == 'POST':
        form = GymHolidayForm(request.POST, instance=holiday)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Festivo actualizado correctamente')
            return redirect('gym_holidays_list')
    else:
        form = GymHolidayForm(instance=holiday)
    
    context = {
        'title': f'Editar Festivo: {holiday.name}',
        'form': form,
        'gym': gym,
        'holiday': holiday,
    }
    
    return render(request, 'backoffice/gym/holiday_form.html', context)


@login_required
@require_http_methods(["POST"])
def gym_holiday_delete(request, holiday_id):
    """
    Eliminar un festivo.
    """
    gym = getattr(request, 'gym', None)
    if not gym:
        messages.error(request, 'Gym no encontrado')
        return redirect('backoffice_dashboard')
    
    try:
        holiday = GymHoliday.objects.get(id=holiday_id, gym=gym)
        holiday_name = holiday.name
        holiday.delete()
        messages.success(request, f'✅ Festivo "{holiday_name}" eliminado correctamente')
    except GymHoliday.DoesNotExist:
        messages.error(request, 'Festivo no encontrado')
    
    return redirect('gym_holidays_list')


@login_required
def gym_opening_hours(request):
    """
    Vista para editar horarios de apertura del gym
    (Versión mejorada que usa el modelo)
    """
    gym = getattr(request, 'gym', None)
    if not gym:
        messages.error(request, 'Gym no encontrado')
        return redirect('backoffice_dashboard')
    
    # Obtener o crear horarios (OneToOne relation)
    opening_hours, created = GymOpeningHours.objects.get_or_create(gym=gym)
    
    if request.method == 'POST':
        form = GymOpeningHoursForm(request.POST, instance=opening_hours)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Horarios de apertura actualizados correctamente')
            return redirect('gym_opening_hours')
    else:
        form = GymOpeningHoursForm(instance=opening_hours)
    
    context = {
        'title': 'Horarios de Apertura',
        'form': form,
        'gym': gym,
        'opening_hours': opening_hours,
    }
    
    return render(request, 'backoffice/gym/opening_hours.html', context)
