"""
Script de ejemplo: Crear incentivos con filtros de actividad y horario

Este script demuestra cómo crear reglas de incentivos usando los nuevos filtros:
- Actividades específicas
- Categorías de actividades
- Franjas horarias
- Días de la semana

Ejecutar desde Django shell:
python manage.py shell < create_example_incentives.py
"""

from staff.models import IncentiveRule, StaffProfile
from activities.models import Activity, ActivityCategory
from organizations.models import Gym
from datetime import time

# Obtener gym de ejemplo (ajusta según tu base de datos)
gym = Gym.objects.first()
print(f"🏋️ Gym: {gym.name}")

# Obtener algunas actividades de ejemplo
try:
    spinning = Activity.objects.filter(gym=gym, name__icontains='spinning').first()
    yoga = Activity.objects.filter(gym=gym, name__icontains='yoga').first()
    cardio_category = ActivityCategory.objects.filter(gym=gym, name__icontains='cardio').first()
except Exception as e:
    print(f"⚠️ Asegúrate de tener actividades creadas: {e}")
    spinning, yoga, cardio_category = None, None, None

print("\n" + "="*60)
print("📊 CREANDO INCENTIVOS DE EJEMPLO")
print("="*60 + "\n")

# ========================================
# EJEMPLO 1: Incentivo por Actividad Específica
# ========================================
if spinning:
    incentive1, created = IncentiveRule.objects.get_or_create(
        gym=gym,
        name="Bonus Spinning",
        defaults={
            'type': 'CLASS_FIXED',
            'value': 8.00,
            'activity': spinning,
            'is_active': True,
        }
    )
    if created:
        print("✅ EJEMPLO 1: Bonus Spinning")
        print(f"   - Tipo: Fijo por Clase")
        print(f"   - Valor: 8€")
        print(f"   - Actividad: {spinning.name}")
        print(f"   - Resultado: 8€ por cada clase de Spinning")
        print(f"   - Filtros: {incentive1.get_filters_summary()}")
        print()
else:
    print("⚠️ EJEMPLO 1: Saltado (no hay actividad Spinning)")

# ========================================
# EJEMPLO 2: Incentivo por Franja Horaria
# ========================================
incentive2, created = IncentiveRule.objects.get_or_create(
    gym=gym,
    name="Clases Nocturnas Premium",
    defaults={
        'type': 'CLASS_FIXED',
        'value': 12.00,
        'time_start': time(20, 0),
        'time_end': time(23, 0),
        'is_active': True,
    }
)
if created:
    print("✅ EJEMPLO 2: Clases Nocturnas Premium")
    print(f"   - Tipo: Fijo por Clase")
    print(f"   - Valor: 12€")
    print(f"   - Horario: 20:00 - 23:00")
    print(f"   - Resultado: 12€ por cualquier clase entre 20:00 y 23:00")
    print(f"   - Filtros: {incentive2.get_filters_summary()}")
    print()

# ========================================
# EJEMPLO 3: Combinación Actividad + Horario + Días
# ========================================
if spinning:
    incentive3, created = IncentiveRule.objects.get_or_create(
        gym=gym,
        name="Spinning Fines de Semana Mañana",
        defaults={
            'type': 'CLASS_ATTENDANCE',
            'value': 0.40,
            'activity': spinning,
            'time_start': time(9, 0),
            'time_end': time(13, 0),
            'weekdays': ['SAT', 'SUN'],
            'is_active': True,
        }
    )
    if created:
        print("✅ EJEMPLO 3: Spinning Fines de Semana Mañana")
        print(f"   - Tipo: Variable por Asistente")
        print(f"   - Valor: 0.40€ por persona")
        print(f"   - Actividad: {spinning.name}")
        print(f"   - Horario: 09:00 - 13:00")
        print(f"   - Días: Sábado, Domingo")
        print(f"   - Resultado: 0.40€ por asistente en Spinning sáb/dom 9-13h")
        print(f"   - Filtros: {incentive3.get_filters_summary()}")
        print()
else:
    print("⚠️ EJEMPLO 3: Saltado (no hay actividad Spinning)")

# ========================================
# EJEMPLO 4: Categoría Completa + Días Laborables
# ========================================
if cardio_category:
    incentive4, created = IncentiveRule.objects.get_or_create(
        gym=gym,
        name="Cardiovascular Entre Semana",
        defaults={
            'type': 'CLASS_FIXED',
            'value': 5.00,
            'activity_category': cardio_category,
            'weekdays': ['MON', 'TUE', 'WED', 'THU', 'FRI'],
            'is_active': True,
        }
    )
    if created:
        print("✅ EJEMPLO 4: Cardiovascular Entre Semana")
        print(f"   - Tipo: Fijo por Clase")
        print(f"   - Valor: 5€")
        print(f"   - Categoría: {cardio_category.name}")
        print(f"   - Días: Lunes a Viernes")
        print(f"   - Resultado: 5€ por clase cardiovascular lunes-viernes")
        print(f"   - Filtros: {incentive4.get_filters_summary()}")
        print()
else:
    print("⚠️ EJEMPLO 4: Saltado (no hay categoría Cardiovascular)")

# ========================================
# EJEMPLO 5: Solo Horario Mañana (Todas las Actividades)
# ========================================
incentive5, created = IncentiveRule.objects.get_or_create(
    gym=gym,
    name="Bonus Madrugador",
    defaults={
        'type': 'CLASS_FIXED',
        'value': 3.00,
        'time_start': time(6, 0),
        'time_end': time(9, 0),
        'is_active': True,
    }
)
if created:
    print("✅ EJEMPLO 5: Bonus Madrugador")
    print(f"   - Tipo: Fijo por Clase")
    print(f"   - Valor: 3€")
    print(f"   - Horario: 06:00 - 09:00")
    print(f"   - Resultado: 3€ extra por cualquier clase 6-9am")
    print(f"   - Filtros: {incentive5.get_filters_summary()}")
    print()

# ========================================
# EJEMPLO 6: Yoga Tardes (Solo Martes y Jueves)
# ========================================
if yoga:
    incentive6, created = IncentiveRule.objects.get_or_create(
        gym=gym,
        name="Yoga Martes/Jueves Tarde",
        defaults={
            'type': 'CLASS_FIXED',
            'value': 7.00,
            'activity': yoga,
            'time_start': time(17, 0),
            'time_end': time(20, 0),
            'weekdays': ['TUE', 'THU'],
            'is_active': True,
        }
    )
    if created:
        print("✅ EJEMPLO 6: Yoga Martes/Jueves Tarde")
        print(f"   - Tipo: Fijo por Clase")
        print(f"   - Valor: 7€")
        print(f"   - Actividad: {yoga.name}")
        print(f"   - Horario: 17:00 - 20:00")
        print(f"   - Días: Martes, Jueves")
        print(f"   - Resultado: 7€ por Yoga mar/jue entre 17-20h")
        print(f"   - Filtros: {incentive6.get_filters_summary()}")
        print()
else:
    print("⚠️ EJEMPLO 6: Saltado (no hay actividad Yoga)")

# ========================================
# RESUMEN FINAL
# ========================================
print("\n" + "="*60)
print("📋 RESUMEN DE INCENTIVOS CREADOS")
print("="*60)

all_incentives = IncentiveRule.objects.filter(gym=gym, is_active=True)
for idx, inc in enumerate(all_incentives, 1):
    print(f"\n{idx}. {inc.name}")
    print(f"   Tipo: {inc.get_type_display()}")
    print(f"   Valor: {inc.value}{'€' if 'FIXED' in inc.type or 'ATTENDANCE' in inc.type else '%'}")
    print(f"   Filtros: {inc.get_filters_summary()}")

print("\n" + "="*60)
print("✅ SCRIPT COMPLETADO")
print("="*60)
print("\nPara probar el sistema:")
print("1. Ve a: Menú → Equipo → Incentivos")
print("2. Verás todas las reglas creadas")
print("3. Edita cualquiera para ver el formulario completo")
print("4. Crea una clase que cumpla los criterios y verifica la comisión")
print("\n💡 Consulta: GUIA_INCENTIVOS_ACTIVIDADES_HORARIOS.md")
