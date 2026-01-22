"""
URLs para widgets embebibles
"""

from django.urls import path
from . import views

app_name = 'embed'

urlpatterns = [
    # Widget de horario embebible (Vista de Lista - PRINCIPAL)
    path('<slug:slug>/schedule/', views.embed_schedule, name='schedule'),
    
    # Widget de horario embebible (Vista de Calendario FullCalendar - Alternativa)
    path('<slug:slug>/schedule/calendar/', views.embed_schedule_calendar, name='schedule_calendar'),
]
