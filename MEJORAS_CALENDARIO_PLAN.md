# 📊 Plan de Mejoras del Calendario

## 🎯 Las 3 Mejoras Solicitadas

### ✅ 1. Grid Más Alargado (Ancho de Clases)
### ✅ 2. Filtro por Staff con Datos Reales y Conteo
### ✅ 3. Gestión de Festivos (✅ YA IMPLEMENTADO)

---

## 📐 Mejora 1: Grid Más Alargado

### **Problema Actual:**
- Las columnas de días son demasiado estrechas
- Los nombres de clases se truncan
- No hay espacio para información adicional

### **Soluciones Disponibles:**

#### **Opción A: CSS Grid Expandible (RECOMENDADA)**

Encuentra en `templates/activities/calendar.html` y modifica:

```css
.calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, minmax(240px, 1fr));  /* Aumentar de 180px a 240px */
    gap: 12px;
    overflow-x: auto;
    padding: 16px;
}

.day-column {
    min-width: 240px;  /* Aumentar ancho mínimo */
    background: white;
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.class-card {
    padding: 10px;  /* Aumentar de 6px */
    min-height: 50px;  /* Aumentar altura */
    margin-bottom: 8px;
    border-radius: 6px;
    font-size: 13px;
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
}
```

#### **Opción B: Selector de Ancho (INTERACTIVO)**

Agrega en `templates/activities/calendar.html` (al inicio del calendar):

```html
<!-- Control de Ancho de Grid -->
<div class="mb-4 flex items-center gap-3">
    <label class="text-sm font-semibold text-slate-700">Ancho del calendario:</label>
    <div class="flex gap-2">
        <button onclick="setGridWidth('compact')" class="px-3 py-1 rounded bg-slate-200 hover:bg-slate-300 text-xs font-semibold">
            Compacto (180px)
        </button>
        <button onclick="setGridWidth('normal')" class="px-3 py-1 rounded bg-blue-200 hover:bg-blue-300 text-xs font-semibold">
            Normal (220px)
        </button>
        <button onclick="setGridWidth('expanded')" class="px-3 py-1 rounded bg-green-200 hover:bg-green-300 text-xs font-semibold">
            Expandido (280px)
        </button>
    </div>
</div>

<script>
    function setGridWidth(mode) {
        const grid = document.querySelector('.calendar-grid');
        const widths = {
            'compact': '180px',
            'normal': '220px',
            'expanded': '280px',
        };
        
        grid.style.gridTemplateColumns = `repeat(7, minmax(${widths[mode]}, 1fr))`;
        
        // Guardar preferencia en localStorage
        localStorage.setItem('calendarGridWidth', mode);
        
        // Actualizar visualmente
        document.querySelectorAll('[onclick^="setGridWidth"]').forEach(btn => {
            btn.classList.remove('bg-blue-200', 'hover:bg-blue-300');
            btn.classList.add('bg-slate-200', 'hover:bg-slate-300');
        });
        event.target.classList.add('bg-blue-200', 'hover:bg-blue-300');
    }
    
    // Cargar preferencia guardada
    window.addEventListener('load', () => {
        const saved = localStorage.getItem('calendarGridWidth') || 'normal';
        setGridWidth(saved);
    });
</script>
```

#### **Opción C: Auto-Zoom (RESPONSIVO)**

Modifica CSS existente:

```css
@media (min-width: 1920px) {
    .calendar-grid {
        grid-template-columns: repeat(7, minmax(280px, 1fr));
    }
}

@media (min-width: 1600px) {
    .calendar-grid {
        grid-template-columns: repeat(7, minmax(240px, 1fr));
    }
}

@media (min-width: 1024px) {
    .calendar-grid {
        grid-template-columns: repeat(7, minmax(200px, 1fr));
    }
}

@media (max-width: 1023px) {
    .calendar-grid {
        grid-template-columns: repeat(4, minmax(150px, 1fr));
    }
}
```

### **Implementación (Paso a Paso):**

1. Abre `templates/activities/calendar.html` (si existe) o `templates/backoffice/activities/calendar.html`
2. Busca `.calendar-grid` en el `<style>` o archivo CSS
3. Cambia `grid-template-columns: repeat(7, 1fr)` a `repeat(7, minmax(240px, 1fr))`
4. Aumenta padding/margin en `.day-column` y `.class-card`
5. Prueba en navegador (F5 para refrescar)

---

## 👥 Mejora 2: Filtro por Staff con Datos Reales

### **Problema Actual:**
- No se muestran datos reales del instructor
- No hay conteo de clases en el rango de tiempo
- Sin información de ocupación

### **Solución Completa:**

#### **Paso 1: Crear API de Datos (activities/views.py)**

```python
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from datetime import datetime, timedelta
import json

@require_POST
@login_required
def get_staff_stats(request):
    """
    AJAX para obtener estadísticas de un instructor en rango de fechas.
    
    POST: {
        'staff_id': 1,
        'start_date': '2026-01-14',
        'end_date': '2026-01-20'
    }
    """
    try:
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
        
        gym = request.gym
        staff = StaffMember.objects.get(id=staff_id, gym=gym)
        
        # Obtener clases en el rango
        from activities.models import Schedule
        classes = Schedule.objects.filter(
            gym=gym,
            instructor=staff,
            date__gte=start_date,
            date__lte=end_date
        ).select_related('activity', 'room')
        
        total_classes = classes.count()
        total_students = sum(c.members.count() for c in classes)
        total_hours = sum(getattr(c, 'duration', 1) for c in classes)
        
        # Calcular ocupación
        total_capacity = sum(
            c.activity.max_capacity if hasattr(c.activity, 'max_capacity') else 20 
            for c in classes
        )
        avg_occupancy = (total_students / total_capacity * 100) if total_capacity > 0 else 0
        
        # Detalles por clase
        classes_detail = []
        for cls in classes:
            capacity = cls.activity.max_capacity if hasattr(cls.activity, 'max_capacity') else 20
            enrolled = cls.members.count()
            
            classes_detail.append({
                'date': cls.date.strftime('%a %d/%m'),  # "Tue 14/01"
                'time': str(cls.start_time)[:5],  # "07:00"
                'activity': cls.activity.name if hasattr(cls, 'activity') else 'Unknown',
                'enrolled': enrolled,
                'capacity': capacity,
                'occupancy': round(enrolled / capacity * 100, 1) if capacity > 0 else 0,
            })
        
        return JsonResponse({
            'success': True,
            'instructor': {
                'name': str(staff),
                'photo': staff.photo.url if hasattr(staff, 'photo') and staff.photo else None,
            },
            'stats': {
                'total_classes': total_classes,
                'total_hours': total_hours,
                'total_students': total_students,
                'avg_occupancy': round(avg_occupancy, 1),
            },
            'classes': classes_detail,
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
```

#### **Paso 2: Agregar URL (activities/urls.py)**

```python
from django.urls import path
from . import views

urlpatterns = [
    # ... URLs existentes ...
    path('api/staff-stats/', views.get_staff_stats, name='api_staff_stats'),
]
```

#### **Paso 3: UI en Calendario (templates/activities/calendar.html)**

```html
<!-- Filtro de Staff -->
<div class="mb-6 bg-white rounded-lg shadow p-4">
    <label class="block text-sm font-semibold text-slate-900 mb-3">Filtrar por Instructor</label>
    
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Select de Instructor -->
        <div class="md:col-span-1">
            <select id="staffFilter" class="w-full rounded-lg border-slate-200 focus:ring-blue-500">
                <option value="">📋 Ver Todos</option>
                {% for staff in available_staff %}
                    <option value="{{ staff.id }}">👨‍🏫 {{ staff.full_name }}</option>
                {% endfor %}
            </select>
        </div>
        
        <!-- Rango de Fechas -->
        <div class="md:col-span-1">
            <input type="date" id="startDate" class="w-full rounded-lg border-slate-200 focus:ring-blue-500">
        </div>
        <div class="md:col-span-1">
            <input type="date" id="endDate" class="w-full rounded-lg border-slate-200 focus:ring-blue-500">
        </div>
    </div>
</div>

<!-- Card de Estadísticas (mostrar cuando se selecciona instructor) -->
<div id="statsCard" class="hidden mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-lg p-6 border-l-4 border-blue-500">
    <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div class="text-center">
            <p class="text-sm text-slate-600 mb-1">Clases</p>
            <p class="text-3xl font-bold text-blue-600" id="totalClasses">-</p>
        </div>
        <div class="text-center">
            <p class="text-sm text-slate-600 mb-1">Horas</p>
            <p class="text-3xl font-bold text-green-600" id="totalHours">-</p>
        </div>
        <div class="text-center">
            <p class="text-sm text-slate-600 mb-1">Estudiantes</p>
            <p class="text-3xl font-bold text-purple-600" id="totalStudents">-</p>
        </div>
        <div class="text-center">
            <p class="text-sm text-slate-600 mb-1">Ocupación Prom</p>
            <p class="text-3xl font-bold text-orange-600" id="avgOccupancy">-</p>
        </div>
        <div class="text-center">
            <button onclick="clearStaffFilter()" class="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-semibold text-sm transition-colors">
                ✕ Limpiar Filtro
            </button>
        </div>
    </div>
    
    <!-- Tabla de Clases Detalladas -->
    <div class="mt-6 border-t pt-6">
        <h3 class="text-sm font-semibold text-slate-900 mb-4">Clases en el Rango</h3>
        <div class="overflow-x-auto">
            <table class="w-full text-sm">
                <thead class="border-b border-slate-300">
                    <tr>
                        <th class="text-left py-2 px-3 font-semibold">Fecha</th>
                        <th class="text-left py-2 px-3 font-semibold">Hora</th>
                        <th class="text-left py-2 px-3 font-semibold">Clase</th>
                        <th class="text-center py-2 px-3 font-semibold">Inscritos</th>
                        <th class="text-center py-2 px-3 font-semibold">Capacidad</th>
                        <th class="text-center py-2 px-3 font-semibold">Ocupación</th>
                    </tr>
                </thead>
                <tbody id="classesTableBody">
                    <!-- Se llena con JavaScript -->
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
    const staffFilter = document.getElementById('staffFilter');
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    const statsCard = document.getElementById('statsCard');
    
    // Establecer fechas por defecto (semana actual)
    const today = new Date();
    const monday = new Date(today.setDate(today.getDate() - today.getDay() + 1));
    const friday = new Date(today.setDate(today.getDate() + 4));
    
    startDate.valueAsDate = monday;
    endDate.valueAsDate = friday;
    
    // Evento al seleccionar instructor
    staffFilter.addEventListener('change', loadStaffStats);
    startDate.addEventListener('change', loadStaffStats);
    endDate.addEventListener('change', loadStaffStats);
    
    async function loadStaffStats() {
        if (!staffFilter.value) {
            statsCard.classList.add('hidden');
            return;
        }
        
        try {
            const response = await fetch('{% url "api_staff_stats" %}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}'
                },
                body: JSON.stringify({
                    staff_id: staffFilter.value,
                    start_date: startDate.value,
                    end_date: endDate.value,
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Actualizar stats
                document.getElementById('totalClasses').textContent = data.stats.total_classes;
                document.getElementById('totalHours').textContent = data.stats.total_hours.toFixed(1);
                document.getElementById('totalStudents').textContent = data.stats.total_students;
                document.getElementById('avgOccupancy').textContent = data.stats.avg_occupancy.toFixed(0) + '%';
                
                // Llenar tabla de clases
                const tbody = document.getElementById('classesTableBody');
                tbody.innerHTML = '';
                
                data.classes.forEach(cls => {
                    const row = `
                        <tr class="border-b border-slate-200 hover:bg-slate-50">
                            <td class="py-2 px-3">${cls.date}</td>
                            <td class="py-2 px-3">${cls.time}</td>
                            <td class="py-2 px-3 font-semibold">${cls.activity}</td>
                            <td class="py-2 px-3 text-center">${cls.enrolled}</td>
                            <td class="py-2 px-3 text-center">${cls.capacity}</td>
                            <td class="py-2 px-3 text-center">
                                <span class="px-2 py-1 rounded ${cls.occupancy >= 80 ? 'bg-green-100 text-green-800' : cls.occupancy >= 50 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'} font-semibold text-xs">
                                    ${cls.occupancy}%
                                </span>
                            </td>
                        </tr>
                    `;
                    tbody.innerHTML += row;
                });
                
                statsCard.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }
    
    function clearStaffFilter() {
        staffFilter.value = '';
        statsCard.classList.add('hidden');
    }
</script>
```

### **Resultado:**
- ✅ Selecciona instructor
- ✅ Ve estadísticas en tiempo real
- ✅ Tabla detallada de clases
- ✅ Indicador visual de ocupación (colores)

---

## 🎄 Mejora 3: Gestión de Festivos

### **✅ COMPLETADO**

**Lo que ya está implementado:**

- ✅ Modelos GymOpeningHours y GymHoliday
- ✅ Vistas CRUD de festivos
- ✅ Templates de gestión
- ✅ Funciones de validación (is_gym_open, can_schedule_class)
- ✅ Admin panel configurado

**Próximos pasos de integración:**

1. **En la programación de clases**, valida:
```python
from organizations.utils import can_schedule_class

result = can_schedule_class(gym, date, time, force=request.POST.get('force'))
if not result['can_schedule']:
    messages.error(request, result['message'])
```

2. **En el calendario**, marca visualmente:
```html
{% if day.is_holiday %}
    <div class="day-closed" title="{{ day.holiday.name }}">
        🎄 {{ day.holiday.name }}
    </div>
{% endif %}
```

3. **URLs accesibles:**
   - `/gym/horarios/` - Editar horarios
   - `/gym/festivos/` - Listar festivos
   - `/gym/festivos/crear/` - Crear festivo

---

## 📝 Checklist de Implementación

### **Mejora 1 (Grid Expandible):**
- [ ] Localizar `templates/activities/calendar.html`
- [ ] Opción A: Aumentar minmax de 180px a 240px
- [ ] Opción B: Agregar selector de ancho con localStorage
- [ ] Opción C: Auto-zoom responsivo por breakpoints
- [ ] Probar en diferentes pantallas
- [ ] Deploy a producción

### **Mejora 2 (Filtro Staff):**
- [ ] Agregar función `get_staff_stats()` en activities/views.py
- [ ] Registrar URL `/api/staff-stats/`
- [ ] Crear UI con select, inputs de fecha y stats card
- [ ] Agregar JavaScript para AJAX
- [ ] Llenar tabla de clases dinámicamente
- [ ] Estilos con colores de ocupación
- [ ] Testing manual

### **Mejora 3 (Festivos):**
- [ ] ✅ Completado

---

## 🚀 Integración Recomendada

**Orden de implementación:**

1. **Primero:** Mejora 3 - Festivos (ya hecho ✅)
2. **Segundo:** Mejora 1 - Grid expandible (CSS, 5 minutos)
3. **Tercero:** Mejora 2 - Filtro staff (código + UI, 30 minutos)

**Tiempo total de implementación:** ~35 minutos

---

## 💡 Tips y Tricks

### **Para Grid Expandible:**
- Usar `minmax(240px, 1fr)` en lugar de porcentajes
- Agregar `overflow-x: auto` para scroll en móvil
- CSS custom properties para cambiar dinámicamente

### **Para Filtro Staff:**
- Usar AJAX (fetch API) en lugar de página completa
- Cachear resultados en localStorage si no cambian fechas
- Agregar spinner/loader mientras se carga
- Manejar errores con try-catch

### **Para Festivos:**
- Usar color rojo para días cerrados
- Mostrar emoji de festivo (🎄, 🎆, etc.)
- Permitir override con botón "Forzar Clase"
- Auditoría de cambios de horarios

---

## 📊 Ejemplos Visuales

```
ANTES (Compacto):
┌───────┬───────┬───────┬───────┬───────┬───────┬───────┐
│ LUN   │ MAR   │ MIÉ   │ JUE   │ VIE   │ SÁB   │ DOM   │
├───────┼───────┼───────┼───────┼───────┼───────┼───────┤
│CrossF.│Yoga   │Gym    │Pilates│Zumba  │Cross  │Yoga   │
│ 06:00 │ 09:00 │ 10:00 │ 14:00 │ 18:00 │ 08:00 │ 10:00 │
└───────┴───────┴───────┴───────┴───────┴───────┴───────┘

DESPUÉS (Expandido):
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│    LUNES        │    MARTES       │   MIÉRCOLES     │    JUEVES       │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ CrossFit        │ Yoga            │ Gym             │ Pilates         │
│ 06:00 (15/20)   │ 09:00 (8/15)    │ 10:00 (18/20)   │ 14:00 (12/15)   │
│ Zumba           │ Gym             │ Pilates         │ Zumba           │
│ 18:00 (20/20)   │ 14:00 (10/20)   │ 18:00 (15/20)   │ 17:00 (14/15)   │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘

FILTRO STAFF - ESTADÍSTICAS:
┌─────────────────────────────────────────────────────────────────┐
│  Juan García - Instructor Crossfit                              │
├──────┬──────┬──────┬──────────┬───────────────────────────────┤
│  12  │ 18h  │ 156  │   87%    │  [Filtro: 14/01 - 20/01]    │
│Clases│Horas │Estud.│Ocupación │                               │
├──────────────────────────────────────────────────────────────────┤
│ Fecha │ Hora │ Clase  │ Inscritos │ Capacidad │ Ocupación     │
├──────────────────────────────────────────────────────────────────┤
│ Tue14 │ 07:00│CrossFit│    15     │    20     │ ████████░░ 75%│
│ Wed15 │ 18:00│CrossFit│    18     │    20     │ ██████████ 90%│
│ Thu16 │ 06:00│CrossFit│    20     │    20     │ ██████████100%│
└──────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Conclusión

Las 3 mejoras te permitirán:

1. **Grid más amplio:** Mejor visualización, menos truncado
2. **Filtro por staff:** Datos reales, análisis de carga
3. **Festivos:** Control total sobre días especiales

Todo en línea con lo que hace **Mindbody**, **Zenoti** y **Opengym**.

