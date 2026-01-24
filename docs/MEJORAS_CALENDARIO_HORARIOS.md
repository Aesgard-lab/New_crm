# 📅 Mejoras del Calendario y Horarios

## 🎯 Resumen de Mejoras Solicitadas

### 1. Grid más alargado en el calendario
### 2. Filtro por staff con datos reales y conteo de clases
### 3. Horarios de apertura con festivos

---

## 🏋️ Análisis de Softwares Competidores

### **Comparación: Qué Hacen Otros Softwares**

#### 1️⃣ **Funcional Gym Pro / Opengym**
- ✅ Grid expandible en calendario (puedes ajustar ancho)
- ✅ Filtro por profesor REAL con conteo automático
- ✅ Festivos configurables + bloqueo de clases
- ✅ Permite "forzar" clases en festivos
- ✅ Horarios especiales por salas
- ❌ No tiene captura de cámara (requiere foto subida)

#### 2️⃣ **Mindbody**
- ✅ Calendario responsive y ajustable
- ✅ Dashboard por instructor muy detallado
- ✅ Gestión de días cerrados (holidays)
- ✅ Excepciones para días específicos
- ✅ Integraciones con PayPal/Square
- ❌ Muy caro ($300+/mes)
- ❌ Interfaz compleja

#### 3️⃣ **Zenoti**
- ✅ Grid ultra-flexible, zoom in/out
- ✅ Staff analytics en tiempo real
- ✅ Holidays + horarios especiales
- ✅ Permite override de horarios
- ✅ Reportes completos
- ❌ Interfaz pesada
- ❌ Curva de aprendizaje alta

#### 4️⃣ **Teamup Calendar / Maroochy (Australia)**
- ✅ Staff view con stats
- ✅ Class count por periodo
- ✅ Drag-drop intuitivo
- ✅ Holidays management simple
- ✅ Mobile-friendly
- ❌ Menos automatización

---

## 📝 Recomendaciones de Implementación

### **1. Grid Más Alargado (Ancho de Clases)**

**Opciones recomendadas:**

```css
/* Opción A: Aumentar ancho del día en el grid */
.day-column {
    flex: 1 1 200px;  /* Cambiar de 180px a 200px */
    min-width: 200px;
}

/* Opción B: Scroll horizontal si es necesario */
.calendar-grid {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}

/* Opción C: Zoom/scale adjustable */
.class-card {
    padding: 8px;  /* Aumentar de 6px a 8px */
    min-height: 45px;  /* Aumentar altura mínima */
}
```

**Lo que hace Mindbody:**
- Selector de ancho: "Compacto | Normal | Expandido"
- Columnas dinámicas: 5, 6, 7 días
- Zoom de 80% a 150%

**Mi recomendación para tu sistema:**
- Agregar botón "📏 Expandir horarios" que aumenta ancho
- Hacer que sea persistente (localStorage)
- Opción de "Ajuste automático"

---

### **2. Filtro por Staff con Datos Reales**

**Qué hace la competencia:**

| Software | Implementación |
|---|---|
| **Opengym** | Listado con ✓/✗, total clases, horas, ingresos |
| **Mindbody** | Dashboard por instructor: ocupación, ingresos, clientes |
| **Zenoti** | Analytics: clase/mes, horas, rating |

**Lo que NECESITAS implementar:**

```python
# Vista mejorada:
- GET /activities/?staff=ID&range=week
  Returns: {
    "instructor": "Juan García",
    "total_classes": 12,
    "total_hours": 18,
    "students": 156,
    "occupancy_rate": "87%",
    "classes": [
      {
        "date": "2026-01-14",
        "time": "07:00",
        "name": "CrossFit",
        "room": "Sala 1",
        "capacity": 15,
        "enrolled": 12
      }
    ]
  }
```

**Métricas que te pide añadir:**
1. ✅ Total de clases en el rango
2. ✅ Horas totales dictadas
3. ✅ Estudiantes únicos
4. ✅ Tasa de ocupación promedio
5. ✅ Ingresos generados (si aplica)

---

### **3. Horarios de Apertura + Festivos**

**Cómo hacerlo correctamente (paso a paso):**

#### **Paso 1: Configuración Base**
```python
GymOpeningHours (ya creado) ✅
- Horarios L-V: 6:00-22:00
- Horarios S: 8:00-20:00
- Horarios D: 8:00-20:00

GymHoliday (ya creado) ✅
- Fecha del festivo
- Nombre (Navidad, Año Nuevo)
- is_closed: booleano
- allow_classes: permite forzar
- special_open/close: horario especial si abre
```

#### **Paso 2: Lógica de Validación**

```python
def is_gym_open(gym, date, time):
    """Verifica si el gym está abierto en esa fecha/hora"""
    
    # 1. Verificar si es festivo
    holiday = GymHoliday.objects.filter(gym=gym, date=date).first()
    
    if holiday:
        if holiday.is_closed:
            return False  # Cerrado
        elif holiday.special_open and holiday.special_close:
            return holiday.special_open <= time <= holiday.special_close
    
    # 2. Si no es festivo, usar horarios regulares
    day_of_week = date.weekday()  # 0=Lunes, 6=Domingo
    hours = gym.opening_hours.get_hours_for_day(day_of_week)
    
    return hours['open'] <= time <= hours['close']


def can_schedule_class(gym, date, time, force=False):
    """
    Verifica si se puede programar una clase
    force=True ignora cerres pero no horarios regulares
    """
    
    holiday = GymHoliday.objects.filter(gym=gym, date=date).first()
    
    if holiday and holiday.is_closed and not force:
        return False, "Gym cerrado en esta fecha"
    
    if not is_gym_open(gym, date, time):
        if force and holiday and holiday.allow_classes:
            return True, "Clase forzada en festivo"
        return False, "Fuera de horario"
    
    return True, "OK"
```

#### **Paso 3: UI en Calendario**

**Indicadores visuales:**

```html
<!-- Días festivos -->
<div class="day-column holiday">
    <div class="holiday-banner">🎄 Navidad</div>
    <!-- Las clases aparecen grisadas/deshabilitadas -->
</div>

<!-- Clases forzadas en festivo -->
<div class="class-card forced-holiday">
    📌 Clase Especial (Forzada en Festivo)
</div>

<!-- Fuera de horario -->
<div class="class-card out-of-hours">
    ⚠️ Fuera de horario (ver aviso)
</div>
```

---

## 🎨 Mejoras Visuales Recomendadas

### **Para el Calendario:**

1. **Selector de Ancho**
   ```
   [ Compacto ▼ ] Normal | Expandido | Automático
   ```

2. **Leyenda Visual**
   ```
   🟢 Abierto | 🔴 Cerrado | 🟡 Horario Especial | ⚠️ Advertencia
   ```

3. **Información al Pasar Mouse**
   ```
   Fecha: 14/01/2026
   Estado: ABIERTO (6:00-22:00)
   Clases: 8
   Ocupación: 87%
   ```

### **Para Filtro de Staff:**

1. **Card Principal**
   ```
   Instructor: Juan García
   ├─ Total clases: 12
   ├─ Horas: 18h
   ├─ Estudiantes: 156
   ├─ Ocupación: 87%
   └─ Ingresos: $2,340
   ```

2. **Tabla de Clases**
   ```
   | Fecha | Hora | Clase | Sala | Capacidad | Inscritos | % |
   |-------|------|-------|------|-----------|-----------|---|
   ```

---

## 🚀 Orden de Implementación Recomendado

1. ✅ **Ya hecho:** Modelos GymOpeningHours y GymHoliday
2. **Próximo:** Vista de admin para gestionar festivos
3. **Luego:** Función de validación `is_gym_open()`
4. **Después:** Mejorar grid calendario (CSS)
5. **Final:** Dashboard de staff con métricas

---

## 💡 Funcionalidades Extra que Piden Otros

- [ ] Horarios especiales por **sala** (no solo gym)
- [ ] Plantillas de festivos por **país**
- [ ] Notificaciones cuando falta cambiar horarios
- [ ] Sincronización con Google Calendar
- [ ] Alertas de cambios de horario a staff
- [ ] Reportes de ocupación vs horarios
- [ ] Análisis de rentabilidad por hora

---

## 📊 Benchmarking de Precios (Contexto)

| Software | Precio | Usuarios | Características |
|----------|--------|----------|-----------------|
| **Mindbody** | $300+/mes | +50,000 | Muy completo, caro |
| **Zenoti** | $250+/mes | +30,000 | Analytics fuerte |
| **Opengym** | $150/mes | 10,000+ | Buena relación precio |
| **Tu CRM** | GRATIS* | ∞ | Personalizable |

*Tienes oportunidad de hacer algo especial aquí.

---

## 📝 Siguiente Paso

¿Quieres que implemente:

1. **Vista admin mejorada** para gestionar festivos
2. **Funciones de validación** (is_gym_open, can_schedule_class)
3. **Mejoras visuales** del calendario (grid expandible)
4. **Dashboard de staff** con conteo real de clases
5. **Todos los anteriores**

¿Cuál es tu prioridad?
