# 🚀 GUÍA RÁPIDA: Sistema de Analytics

## 📍 Acceso Rápido

### URLs Principales:
```
Dashboard Principal:     /activities/analytics/
Reporte Asistencias:     /activities/reports/attendance/
Reporte Instructores:    /activities/reports/staff/
Reporte Actividades:     /activities/reports/activities/
Analytics Avanzados:     /activities/reports/advanced/
```

### APIs JSON:
```
Heatmap Data:           /activities/api/analytics/heatmap/
Tendencias:             /activities/api/analytics/trends/
Predicción:             /activities/api/analytics/predict/
```

### Exportar CSV:
```
/activities/reports/export/csv/?type=attendance&start_date=2024-01-01&end_date=2024-01-31
/activities/reports/export/csv/?type=staff&start_date=2024-01-01&end_date=2024-01-31
/activities/reports/export/csv/?type=activities&start_date=2024-01-01&end_date=2024-01-31
```

---

## 🎯 Casos de Uso

### 1. Ver Dashboard General
1. Ir a `/activities/analytics/`
2. Aplicar filtros de fecha si necesario
3. Ver KPIs principales en las tarjetas superiores
4. Explorar gráficas de horarios pico y actividades populares
5. Revisar tabla de top instructores

### 2. Analizar Asistencias (Heatmap)
1. Ir a `/activities/reports/attendance/`
2. Seleccionar rango de fechas
3. Elegir período: diario/semanal/mensual
4. Ver **heatmap** de día × hora (colores más intensos = más asistencia)
5. Revisar tendencias temporales en la gráfica
6. Exportar datos con el botón CSV

**💡 Para qué sirve:**
- Identificar los mejores horarios para programar clases
- Detectar días/horas con baja asistencia
- Optimizar capacidad por horario
- Planificar horarios de staff

### 3. Evaluar Performance de Instructores
1. Ir a `/activities/reports/staff/`
2. Aplicar filtros de fecha
3. Opcionalmente filtrar por instructor específico
4. Ver rankings por:
   - 📊 Asistencia total (más clientes atraídos)
   - ⭐ Rating promedio (mejor valorados)
   - 📅 Clases impartidas (más activos)
   - 👥 Clientes únicos (mayor alcance)
5. Comparar instructores en la gráfica inferior
6. Exportar para análisis adicional

**💡 Para qué sirve:**
- Identificar instructores estrella
- Detectar áreas de mejora
- Calcular bonos/incentivos basados en performance
- Asignar clases estratégicamente

### 4. Estudiar Popularidad de Actividades
1. Ir a `/activities/reports/activities/`
2. Ver top 15 actividades más populares
3. Revisar tasas de ocupación (🟢 >80%, 🟡 50-80%, 🔴 <50%)
4. Analizar performance por time slot (matriz hora × día)
5. Ver utilización de salas
6. Explorar **patrones de asistencia cruzada** (clases que comparten clientes)

**💡 Para qué sirve:**
- Decidir qué clases ofrecer más frecuentemente
- Eliminar clases con baja demanda
- Identificar horarios óptimos por tipo de clase
- Crear paquetes de clases relacionadas (cross-selling)

### 5. Predicciones y Patrones Avanzados
1. Ir a `/activities/reports/advanced/`
2. **Booking Lead Time:**
   - Ver cuándo reservan tus clientes (mismo día, 1-3 días, 4-7 días, 8+ días)
   - Ajustar estrategia de recordatorios
3. **Patrones Estacionales:**
   - Identificar mejores días de la semana
   - Programar clases según demanda por día
4. **Predictor de Asistencia:**
   - Seleccionar actividad + día + hora
   - Obtener predicción de asistencia esperada
   - Ajustar capacidad máxima
5. **Retención por Clase:**
   - Ver qué clases tienen mayor tasa de clientes recurrentes
   - Identificar clases que necesitan mejorar engagement

**💡 Para qué sirve:**
- Marketing dirigido según comportamiento de reserva
- Optimizar campañas de recordatorios
- Planificación estratégica a largo plazo
- Predecir demanda para nuevas clases

---

## 🔍 Filtros Disponibles

### Todos los Reportes:
- **Fecha Inicio**: Primera fecha del rango a analizar
- **Fecha Fin**: Última fecha del rango a analizar
- **Período**: Cómo agrupar datos (diario/semanal/mensual)

### Reporte de Instructores:
- **Staff**: Filtrar por instructor específico

### Reporte de Actividades:
- **Actividad**: Filtrar por clase específica
- **Período**: Ver tendencias en el tiempo

---

## 📊 KPIs Principales Explicados

### Ocupación Promedio
- **Qué es**: % de capacidad de las clases que se llena
- **Fórmula**: (Asistencia Total / Capacidad Total) × 100
- **Bueno**: >80% (clases casi llenas)
- **Regular**: 60-80% (hay espacio de mejora)
- **Malo**: <60% (necesita atención)

### Tamaño Promedio de Clase
- **Qué es**: Cuántas personas asisten en promedio por sesión
- **Fórmula**: Asistencia Total / Número de Sesiones
- **Uso**: Comparar con capacidad para ver si sobra o falta espacio

### Utilización de Staff
- **Qué es**: % de sesiones programadas que efectivamente se imparten
- **Fórmula**: (Sesiones Realizadas / Sesiones Programadas) × 100
- **Uso**: Detectar cancelaciones excesivas o subutilización

### Tasa de No-Show
- **Qué es**: % de reservas que NO se convierten en asistencia
- **Fórmula**: (No-Shows / Total Reservas) × 100
- **Bueno**: <10%
- **Regular**: 10-20%
- **Malo**: >20% (problema serio)

### Tasa de Cancelación
- **Qué es**: % de reservas que se cancelan antes de la clase
- **Fórmula**: (Cancelaciones / Total Reservas) × 100
- **Uso**: Evaluar política de cancelación y satisfacción

---

## 💾 Exportar Datos

### CSV para Excel/Google Sheets:
1. Click en botón "📥 Exportar CSV" en cualquier reporte
2. Abrir archivo descargado en Excel/Sheets
3. Aplicar filtros adicionales
4. Crear gráficas personalizadas
5. Compartir con equipo

### Campos en CSV:

**Attendance Report:**
- Fecha, Sesiones, Asistencia Total, Promedio, Ocupación %

**Staff Report:**
- Instructor, Clases, Asistencia, Promedio, Clientes Únicos, Rating

**Activities Report:**
- Actividad, Categoría, Sesiones, Asistencia, Promedio, Ocupación %, Rating

---

## 🎨 Gráficas y Visualizaciones

### Heatmap (Mapa de Calor)
- **Ejes**: Día de la semana (vertical) × Hora del día (horizontal)
- **Color**: Intensidad = más asistencia
- **Hover**: Ver números exactos
- **Uso**: Detectar patrones visuales rápidamente

### Gráfica de Líneas (Tendencias)
- **Eje X**: Tiempo (días/semanas/meses)
- **Eje Y**: Asistencia
- **Uso**: Ver evolución temporal, detectar crecimiento/decrecimiento

### Gráfica de Barras (Rankings)
- **Horizontal**: Top instructores/actividades
- **Vertical**: Horarios pico
- **Uso**: Comparar elementos entre sí

### Gráfica de Barras Doble Eje
- **Eje Y izquierdo**: Asistencia total
- **Eje Y derecho**: Promedio o porcentaje
- **Uso**: Comparar dos métricas relacionadas

---

## 🔔 Tips y Mejores Prácticas

### 1. Análisis Semanal
- Revisar dashboard cada lunes
- Comparar con semana anterior
- Ajustar programación según patrones

### 2. Análisis Mensual
- Exportar CSV mensual
- Calcular bonos de instructores
- Revisar retención por clase
- Planificar siguiente mes

### 3. Análisis Trimestral
- Usar período de 90 días en analytics avanzados
- Revisar patrones estacionales
- Ajustar estrategia de marketing
- Planificar nuevas clases

### 4. Uso del Predictor
- Usar para clases nuevas
- Ajustar capacidad máxima
- Evitar overbooking
- Optimizar tamaño de sala

### 5. Patrones de Asistencia Cruzada
- Crear paquetes de clases relacionadas
- Ofrecer descuentos en combos
- Cross-selling dirigido
- Aumentar LTV (lifetime value)

---

## 🐛 Troubleshooting

### No veo datos en el dashboard
- ✅ Verificar que existan sesiones en el rango de fechas
- ✅ Confirmar que las sesiones tengan asistencias registradas
- ✅ Ampliar rango de fechas
- ✅ Revisar filtros aplicados

### El heatmap está vacío
- ✅ Necesitas al menos 30 días de datos
- ✅ Las sesiones deben tener hora (start_datetime)
- ✅ Los clientes deben estar marcados como ATTENDED

### La predicción dice "baja confianza"
- ✅ Normal con pocas sesiones históricas (<5)
- ✅ Esperar más datos o usar como referencia aproximada
- ✅ La confianza mejora con más histórico

### Exportar CSV no funciona
- ✅ Verificar permisos de descarga en navegador
- ✅ Confirmar que hay datos en el rango seleccionado
- ✅ Probar con rango de fechas más amplio

---

## 📞 Soporte

Para dudas o problemas:
1. Revisar esta guía
2. Consultar [SISTEMA_ANALYTICS_REPORTES.md](SISTEMA_ANALYTICS_REPORTES.md) para detalles técnicos
3. Contactar al equipo de desarrollo

---

**Última actualización**: Enero 2026  
**Versión**: 1.0
