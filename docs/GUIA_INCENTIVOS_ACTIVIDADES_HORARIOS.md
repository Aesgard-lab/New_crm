# 📊 Guía: Sistema de Incentivos por Actividad y Horario

## 🎯 Descripción General

Sistema completo de incentivos con **criterios opcionales independientes** que permite configurar comisiones e incentivos basados en:

- ✅ **Actividades específicas** (ej: Yoga, Spinning, Pilates)
- ✅ **Categorías completas** (ej: Cardiovascular, Fuerza, Flexibilidad)
- ✅ **Franjas horarias personalizadas** (ej: 06:00-12:00, 18:00-22:00)
- ✅ **Días de la semana específicos** (ej: solo lunes y miércoles, solo fines de semana)
- ✅ **Combinaciones** (ej: "Spinning en horario nocturno, solo viernes y sábado")

---

## 📋 Modelo de Datos: IncentiveRule

### Campos Nuevos Añadidos:

```python
class IncentiveRule(models.Model):
    # Campos existentes
    gym = ForeignKey(Gym)
    staff = ForeignKey(StaffProfile, null=True, blank=True)  # Opcional: específico o global
    name = CharField(max_length=150)
    type = CharField(choices=Type.choices)  # SALE_PCT, CLASS_FIXED, etc.
    value = DecimalField()  # Cantidad o porcentaje
    
    # ⭐ NUEVOS: Filtros de Actividad (Opcionales)
    activity = ForeignKey(Activity, null=True, blank=True)
    activity_category = ForeignKey(ActivityCategory, null=True, blank=True)
    
    # ⭐ NUEVOS: Filtros de Horario (Opcionales)
    time_start = TimeField(null=True, blank=True)  # ej: 06:00
    time_end = TimeField(null=True, blank=True)    # ej: 12:00
    
    # ⭐ NUEVO: Filtros de Días (Opcional)
    weekdays = JSONField(default=list)  # ['MON', 'TUE', 'WED', ...]
    
    criteria = JSONField(default=dict)  # Otros filtros avanzados
    is_active = BooleanField(default=True)
```

### Métodos del Modelo:

#### 1. `get_filters_summary()` - Resumen Legible
Retorna un string con los filtros aplicados para mostrar en la UI:

```python
"Actividad: Yoga | Horario: 06:00-12:00 | Días: Lun, Mié, Vie"
```

#### 2. `matches_session(session)` - Verificación de Criterios
Verifica si una sesión de clase cumple con todos los criterios configurados:

```python
def matches_session(self, session):
    # Verifica actividad, categoría, horario y días
    # Retorna True si cumple todos los criterios
```

---

## 🎨 Interfaz de Usuario

### Formulario de Creación/Edición

El formulario tiene **4 secciones visuales diferenciadas**:

#### 1️⃣ **Información Básica** (Obligatoria)
- **Nombre**: Identificador de la regla (ej: "Spinning Mañanas")
- **Tipo**: % Comisión Venta, Fijo por Clase, Variable por Asistente, etc.
- **Valor**: Cantidad en € o porcentaje
- **Aplicar a**: Empleado específico o todo el equipo

#### 2️⃣ **Filtros de Actividad** (Opcional - Fondo Morado)
```
📌 Actividad Específica: [Select: Yoga, Spinning, Pilates, ...]
📁 Categoría Completa: [Select: Cardiovascular, Fuerza, ...]

⚠️ No selecciones ambos: Elige actividad O categoría
```

#### 3️⃣ **Franja Horaria** (Opcional - Fondo Azul)
```
🕐 Hora Inicio: [Time Input: 06:00]
🕐 Hora Fin:    [Time Input: 12:00]

💡 Ejemplo: 06:00 - 12:00 para mañanas, 18:00 - 22:00 para noches
```

#### 4️⃣ **Días de la Semana** (Opcional - Fondo Verde)
```
[✓] Lun  [✓] Mar  [✓] Mié  [ ] Jue  [✓] Vie  [ ] Sáb  [ ] Dom

ℹ️ Dejar todo sin marcar = todos los días
```

---

## 💼 Casos de Uso Reales

### Ejemplo 1: Incentivo por Actividad Específica
```yaml
Nombre: "Bonus Yoga"
Tipo: Fijo por Clase Impartida
Valor: 8€
Actividad: Yoga
Categoría: (vacío)
Horario: (vacío)
Días: (vacío)

➡️ Resultado: 8€ por cada clase de Yoga, cualquier día, cualquier hora
```

### Ejemplo 2: Incentivo por Franja Horaria
```yaml
Nombre: "Clases Nocturnas Premium"
Tipo: Fijo por Clase Impartida
Valor: 12€
Actividad: (vacío)
Categoría: (vacío)
Horario: 20:00 - 23:00
Días: (vacío)

➡️ Resultado: 12€ por cualquier clase entre 20:00 y 23:00
```

### Ejemplo 3: Combinación Completa
```yaml
Nombre: "Spinning Fines de Semana Mañana"
Tipo: Variable por Asistente a Clase
Valor: 0.40€
Actividad: Spinning
Categoría: (vacío)
Horario: 09:00 - 13:00
Días: [Sáb, Dom]

➡️ Resultado: 0.40€ por asistente en clases de Spinning,
              solo sábados/domingos, solo de 9:00 a 13:00
```

### Ejemplo 4: Categoría Completa + Días Laborables
```yaml
Nombre: "Cardiovascular Entre Semana"
Tipo: Fijo por Clase Impartida
Valor: 5€
Actividad: (vacío)
Categoría: Cardiovascular
Horario: (vacío)
Días: [Lun, Mar, Mié, Jue, Vie]

➡️ Resultado: 5€ por clase de cualquier actividad cardiovascular,
              lunes a viernes, cualquier hora
```

---

## 🔧 Validaciones del Formulario

### Validación 1: Actividad vs Categoría
```python
if activity AND activity_category:
    raise ValidationError("No puedes seleccionar actividad Y categoría simultáneamente")
```

### Validación 2: Horario Completo
```python
if time_start XOR time_end:
    raise ValidationError("Debes especificar inicio Y fin, o dejar ambos vacíos")
```

### Validación 3: Horario Lógico
```python
if time_end <= time_start:
    raise ValidationError("La hora fin debe ser posterior al inicio")
```

---

## 🎯 Lógica de Coincidencia (matches_session)

Cuando un instructor completa una clase, el sistema verifica **TODOS** los filtros configurados:

```python
def matches_session(self, session):
    # 1. Si hay filtro de actividad específica
    if self.activity:
        if session.activity_id != self.activity_id:
            return False  # ❌ No coincide
    
    # 2. Si hay filtro de categoría
    if self.activity_category:
        if session.activity.category_id != self.activity_category_id:
            return False  # ❌ No coincide
    
    # 3. Si hay filtro de horario
    if self.time_start and self.time_end:
        session_time = session.start_datetime.time()
        if not (self.time_start <= session_time <= self.time_end):
            return False  # ❌ No coincide
    
    # 4. Si hay filtro de días
    if self.weekdays:
        weekday_map = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        session_weekday = weekday_map[session.start_datetime.weekday()]
        if session_weekday not in self.weekdays:
            return False  # ❌ No coincide
    
    return True  # ✅ Cumple TODOS los criterios
```

---

## 📊 Reglas Múltiples y Acumulación

### Sistema de Prioridad Implementado: **ACUMULACIÓN**

Si una clase cumple **múltiples reglas**, se pagan **TODAS** las reglas que coincidan:

```yaml
Clase: Spinning a las 19:30h (Viernes)

Regla 1: "Spinning General" → 5€
Regla 2: "Clases Nocturnas (18:00-22:00)" → 3€
Regla 3: "Viernes Tarde" → 2€

Total pagado: 5€ + 3€ + 2€ = 10€
```

### Recomendación de Uso:

Para evitar pagos duplicados, sé específico:
- ✅ **Bueno**: "Spinning Mañanas (06:00-12:00)" + "Spinning Noches (18:00-22:00)"
- ❌ **Malo**: "Spinning" + "Todas las Clases Mañanas" (se pagaría doble)

---

## 🗄️ Migración de Datos

### Migración Aplicada: `0009_add_activity_time_filters_to_incentives`

```bash
python manage.py migrate staff
```

**Cambios:**
- Añadido `activity` (ForeignKey nullable)
- Añadido `activity_category` (ForeignKey nullable)
- Añadido `time_start` (TimeField nullable)
- Añadido `time_end` (TimeField nullable)
- Añadido `weekdays` (JSONField con default=[])
- Modificado `criteria` (actualización de help_text)

**Impacto en datos existentes:**
- ✅ Todas las reglas existentes funcionan sin cambios
- ✅ Nuevos campos = NULL/[] por defecto (sin filtros = aplica a todo)
- ✅ Retrocompatible al 100%

---

## 🎨 Archivos Modificados

### 1. **staff/models.py**
- ✅ Añadidos 5 campos nuevos a `IncentiveRule`
- ✅ Método `get_filters_summary()`
- ✅ Método `matches_session(session)`

### 2. **staff/forms.py**
- ✅ Import de `Activity` y `ActivityCategory`
- ✅ 7 campos booleanos para días de la semana
- ✅ Filtrado de queryset por gym
- ✅ Validaciones personalizadas
- ✅ Conversión de checkboxes a array JSON en `save()`

### 3. **templates/backoffice/staff/incentive_form.html**
- ✅ Sección de Filtros de Actividad (morado)
- ✅ Sección de Franja Horaria (azul)
- ✅ Sección de Días de la Semana (verde)
- ✅ Checkboxes visuales con hover
- ✅ Mensajes de ayuda contextual

### 4. **templates/backoffice/staff/incentive_list.html**
- ✅ Mostrar `get_filters_summary()` en lugar de `criteria`
- ✅ Resumen visual de filtros aplicados

---

## 🚀 Uso Paso a Paso

### Crear un Incentivo con Filtros:

1. **Navegar**: Menú → Equipo → Incentivos
2. **Crear**: Botón "+ Crear Incentivo"
3. **Básico**:
   - Nombre: "Spinning Noches Finde"
   - Tipo: "Fijo por Clase Impartida"
   - Valor: 10
   - Aplicar a: (vacío = todos)

4. **Filtros de Actividad**:
   - Actividad: Spinning
   - Categoría: (vacío)

5. **Franja Horaria**:
   - Hora Inicio: 18:00
   - Hora Fin: 22:00

6. **Días**:
   - ✓ Sábado
   - ✓ Domingo

7. **Guardar** → ✅ Regla creada

### Ver Filtros Aplicados:

En la lista de incentivos, cada regla muestra:
```
Spinning Noches Finde
Actividad: Spinning | Horario: 18:00-22:00 | Días: Sáb, Dom
```

---

## 🧪 Testing del Sistema

### Escenario de Prueba:

```python
# Crear regla
rule = IncentiveRule.objects.create(
    gym=gym,
    name="Test Yoga Mañanas",
    type="CLASS_FIXED",
    value=5.00,
    activity=yoga_activity,
    time_start=time(6, 0),
    time_end=time(12, 0),
    weekdays=['MON', 'WED', 'FRI']
)

# Crear sesión que cumple
session = ActivitySession.objects.create(
    gym=gym,
    activity=yoga_activity,
    start_datetime=datetime(2026, 1, 22, 10, 0),  # Miércoles 10:00
    ...
)

# Verificar
assert rule.matches_session(session) == True  # ✅ Cumple todos los criterios

# Crear sesión que NO cumple (día incorrecto)
session2 = ActivitySession.objects.create(
    gym=gym,
    activity=yoga_activity,
    start_datetime=datetime(2026, 1, 23, 10, 0),  # Jueves 10:00
    ...
)

assert rule.matches_session(session2) == False  # ❌ No es lunes/miércoles/viernes
```

---

## 💡 Consejos de Configuración

### ✅ Mejores Prácticas:

1. **Sé específico con las reglas**
   - En lugar de "Todas las clases", usa "Clases mañana + Clases tarde"
   - Evita solapamientos que paguen doble

2. **Usa nombres descriptivos**
   - ✅ "Spinning Lunes/Miércoles Mañana"
   - ❌ "Regla 1"

3. **Prioriza actividades sobre categorías**
   - Para incentivos especiales, usa actividad específica
   - Para políticas generales, usa categoría

4. **Testea las reglas**
   - Crea una regla → Completa una clase → Verifica comisión
   - Revisa el método `matches_session()` en logs

### ⚠️ Errores Comunes:

1. ❌ Seleccionar actividad Y categoría juntos
   - **Solución**: Elige solo uno

2. ❌ Hora fin antes que hora inicio
   - **Solución**: Verifica el orden (06:00 - 12:00)

3. ❌ Olvidar marcar días y dejar horario
   - **Solución**: Sin días marcados = todos los días

---

## 📚 Referencias

- **Modelo**: `staff/models.py` → `IncentiveRule`
- **Formulario**: `staff/forms.py` → `IncentiveRuleForm`
- **Vistas**: `staff/views.py` → `incentive_create`, `incentive_edit`
- **Templates**: `templates/backoffice/staff/incentive_form.html`
- **Migración**: `staff/migrations/0009_add_activity_time_filters_to_incentives.py`

---

## 🎓 Próximos Pasos Recomendados

1. **Automatizar cálculo de comisiones**: Crear un comando que calcule comisiones al finalizar cada día
2. **Dashboard de comisiones**: Vista para que el staff vea sus comisiones ganadas
3. **Reportes**: Excel/PDF con detalle de comisiones por período
4. **Notificaciones**: Avisar al staff cuando gana una comisión
5. **Historial**: Log de comisiones pagadas y pendientes

---

**Última actualización**: 21 de enero de 2026  
**Versión**: 1.0  
**Autor**: Sistema CRM Gimnasio
