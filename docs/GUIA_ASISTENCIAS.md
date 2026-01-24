# 📊 Guía del Sistema de Asistencias

## 🎯 Resumen Ejecutivo

Sistema completo de gestión de asistencia a clases con tres estados diferenciados y marcado por staff. Permite un seguimiento preciso de la asistencia real vs. reservas confirmadas.

---

## 🔑 Estados de Asistencia

### Estados Disponibles

| Estado | Código | Color | Descripción | Icono |
|--------|--------|-------|-------------|-------|
| **Pendiente** | `PENDING` | Gris | Estado inicial al reservar | ⏳ |
| **Asistió** | `ATTENDED` | Verde | Cliente presente en clase | ✅ |
| **No Vino** | `NO_SHOW` | Rojo | Cliente no se presentó | ❌ |
| **Cancelación Tardía** | `LATE_CANCEL` | Amarillo | Canceló fuera de plazo | ⚠️ |

---

## 📍 Ubicación en el Sistema

### Calendario de Clases
1. Ve a **Horario** en el menú principal
2. Haz clic en cualquier clase programada
3. Se abre el modal de detalles de sesión
4. Pestaña **"👥 Asistentes"** muestra la lista

### Marcado Individual
Cada asistente tiene 4 botones verticales:
- 🟢 **Asistió** - Color verde cuando está marcado
- 🔴 **No Vino** - Color rojo cuando está marcado  
- 🟡 **Canceló** - Color amarillo cuando está marcado
- ⚪ **× Quitar** - Eliminar de la clase

### Marcado Masivo
Botón superior **"✓ Marcar Todos"**:
- Marca todos los asistentes pendientes como "Asistió"
- Requiere confirmación
- Útil para clases con alta asistencia

---

## 🔧 Funcionalidad Técnica

### Modelo de Datos
**Tabla**: `ActivitySessionBooking`

```python
class ActivitySessionBooking(models.Model):
    session = ForeignKey(ActivitySession)
    client = ForeignKey(Client)
    status = CharField  # PENDING, CONFIRMED, CANCELLED
    attendance_status = CharField  # PENDING, ATTENDED, NO_SHOW, LATE_CANCEL
    marked_at = DateTimeField  # Cuándo se marcó
    marked_by = ForeignKey(StaffProfile)  # Quién lo marcó
```

### Endpoints API

#### Marcar Asistencia Individual
```http
POST /activities/api/session/{session_id}/attendance/
Content-Type: application/json

{
  "booking_id": 123,
  "status": "ATTENDED"  // o NO_SHOW, LATE_CANCEL
}
```

**Respuesta**:
```json
{
  "status": "ok",
  "booking_id": 123,
  "attendance_status": "ATTENDED",
  "marked_at": "2024-01-15T10:30:00Z",
  "marked_by": "Juan Pérez"
}
```

#### Marcar Múltiples (Marcar Todos)
```http
POST /activities/api/session/{session_id}/attendance/
Content-Type: application/json

{
  "booking_ids": [123, 124, 125],
  "status": "ATTENDED"
}
```

**Respuesta**:
```json
{
  "status": "ok",
  "updated": 3,
  "bookings": [...]
}
```

#### Obtener Estados de Asistencia
```http
GET /activities/api/session/{session_id}/attendance/
```

**Respuesta**:
```json
{
  "session_id": 456,
  "total_bookings": 15,
  "attended": 12,
  "no_show": 2,
  "late_cancel": 1,
  "pending": 0,
  "attendance_rate": 80.0,
  "bookings": [
    {
      "booking_id": 123,
      "client_name": "Ana García",
      "attendance_status": "ATTENDED",
      "marked_at": "2024-01-15T10:30:00Z",
      "marked_by": "Staff: Juan"
    }
  ]
}
```

---

## 🎨 Interfaz de Usuario

### Vista del Modal
```
┌─────────────────────────────────────────┐
│ 👥 Asistentes (15)  📋 Espera  ✏️ Editar│
├─────────────────────────────────────────┤
│                                         │
│ [✓ Marcar Todos] [📧 Email] [📲]       │
│                                         │
│ ┌───────────────────────────────────┐  │
│ │ 👤 Ana García                      │  │
│ │ 📊 85% • 💳 Mensual • 🔄 Serie    │  │
│ │ 📞 +34 600 000 001                │  │
│ │                  [✅ Asistió    ]  │  │
│ │                  [ No Vino     ]  │  │
│ │                  [ Canceló     ]  │  │
│ │                  [ × Quitar    ]  │  │
│ └───────────────────────────────────┘  │
│                                         │
│ ┌───────────────────────────────────┐  │
│ │ 👤 Carlos Ruiz                     │  │
│ │ 📊 92% • ⚠️ Sin cuota             │  │
│ │ 📧 carlos@mail.com                │  │
│ │                  [ Asistió     ]  │  │
│ │                  [✅ No Vino    ]  │  │
│ │                  [ Canceló     ]  │  │
│ │                  [ × Quitar    ]  │  │
│ └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Colores y Estados Visuales

| Estado | Color Botón | Color Ring | Texto |
|--------|-------------|------------|-------|
| **Asistió** | `bg-green-500` | `ring-green-300` | Blanco con ✓ |
| **No Vino** | `bg-red-500` | `ring-red-300` | Blanco con ✗ |
| **Canceló** | `bg-amber-500` | `ring-amber-300` | Blanco con ⚠ |
| **Sin marcar** | `bg-{color}-50` | - | Color oscuro |

---

## 📊 Integración con Automatizaciones

### Trigger de Eventos
El sistema dispara eventos que pueden conectarse a automatizaciones:

```python
# Señales disponibles
on_attendance_marked(booking, old_status, new_status, staff)
on_no_show_marked(booking, session, client)
on_late_cancel_marked(booking, session, client)
```

### Ejemplos de Automatizaciones

#### Email de Confirmación
```yaml
Trigger: on_attendance_marked
Condición: new_status == 'ATTENDED'
Acción: Enviar email
  - Plantilla: "Gracias por asistir"
  - Variables: {clase, fecha, puntos_ganados}
```

#### Alerta de Ausencias Repetidas
```yaml
Trigger: on_no_show_marked
Condición: client.no_show_count >= 3
Acción: Crear tarea para staff
  - Título: "Cliente con 3+ ausencias"
  - Asignar a: Responsable de retención
```

#### Penalización por Cancelación Tardía
```yaml
Trigger: on_late_cancel_marked
Condición: membership.count_late_cancel_as_used == True
Acción: Descontar sesión
  - membership.sessions_remaining -= 1
  - Registrar en historial
```

---

## 🎯 Casos de Uso Comunes

### 1. Marcar Asistencia al Finalizar Clase
**Flujo**:
1. Al terminar la clase, abrir modal de sesión
2. Hacer clic en **"✓ Marcar Todos"**
3. Confirmar en el diálogo
4. Sistema marca todos como `ATTENDED`
5. Si hay ausentes, marcarlos individualmente como `NO_SHOW`

**Ventaja**: Rápido para clases con alta asistencia.

---

### 2. Cliente Avisa Cancelación Tardía
**Flujo**:
1. Cliente llama 2 horas antes de la clase
2. Staff abre la clase en calendario
3. Busca al cliente en lista de asistentes
4. Hace clic en botón **"Canceló"** (amarillo)
5. Sistema registra como `LATE_CANCEL`
6. Si configurado, descuenta sesión de membresía

**Ventaja**: Diferencia cancelación tardía de ausencia sin aviso.

---

### 3. Revisar Ausencias del Mes
**Flujo**:
1. Ir a Analytics → Asistencias
2. Filtrar por estado = `NO_SHOW`
3. Filtrar por fecha = último mes
4. Exportar lista de clientes
5. Crear campaña de reactivación

**Ventaja**: Identificar clientes en riesgo de abandono.

---

## 📈 Métricas y Reportes

### Tasa de Asistencia
```
Asistencia % = (ATTENDED / TOTAL) × 100

Donde:
- ATTENDED: Clientes que asistieron
- TOTAL: ATTENDED + NO_SHOW + LATE_CANCEL
```

### Indicadores de Cliente
Cada cliente muestra en el modal:
- **📊 Tasa de asistencia general**: % de clases a las que asistió
- **🔄 Clases futuras**: Si tiene reservas en serie
- **💳 Tipo de membresía**: Plan activo
- **⚠️ Alertas**: Cancelaciones tardías previas

---

## ⚙️ Configuración

### Contabilizar Cancelaciones Tardías
Configuración por plan de membresía:

**Ubicación**: Configuración → Membresías → [Plan] → Editar

Campo: **"Contar cancelaciones tardías como sesión usada"**
- ✅ **Activado**: Cancelar tarde = descuenta 1 sesión
- ❌ **Desactivado**: Cancelar tarde = no descuenta

**Cuándo activar**:
- Planes con sesiones limitadas
- Gimnasios con alta demanda
- Política estricta de asistencia

**Cuándo desactivar**:
- Planes ilimitados
- Período de prueba/introducción
- Clientes VIP

---

## 🚀 Mejoras Futuras Planeadas

### V2.0 - Check-in Automático
- [ ] QR en entrada registra automáticamente como `ATTENDED`
- [ ] Integración con torniquetes/puertas
- [ ] App móvil con check-in por geolocalización

### V2.1 - Predicción de Asistencia
- [ ] ML para predecir probabilidad de asistencia
- [ ] Alertas proactivas para ausencias probables
- [ ] Sugerencias de reemplazo automático

### V2.2 - Gamificación
- [ ] Puntos por asistencia consistente
- [ ] Badges por racha de asistencias
- [ ] Tabla de clasificación mensual

---

## 🐛 Resolución de Problemas

### Error: "No se puede marcar asistencia"
**Causa**: No existe registro de booking.

**Solución**:
```python
# En Django shell
from activities.models import ActivitySessionBooking, ActivitySession
from clients.models import Client

session = ActivitySession.objects.get(pk=SESSION_ID)
client = Client.objects.get(pk=CLIENT_ID)

# Crear booking manualmente
ActivitySessionBooking.objects.get_or_create(
    session=session,
    client=client,
    defaults={'status': 'CONFIRMED', 'attendance_status': 'PENDING'}
)
```

---

### Los botones no cambian de color
**Causa**: Datos no se refrescan en frontend.

**Solución**:
1. Abrir consola del navegador (F12)
2. Verificar que la llamada API retorna correctamente
3. Refrescar el modal cerrando y abriendo de nuevo
4. Si persiste, limpiar caché del navegador

---

### Todos aparecen como "Pendiente"
**Causa**: Sesiones antiguas sin bookings creados.

**Solución**: Migración de datos
```python
# Script de migración (ejecutar una vez)
from activities.models import ActivitySession, ActivitySessionBooking

for session in ActivitySession.objects.filter(start_datetime__gte='2024-01-01'):
    for client in session.attendees.all():
        ActivitySessionBooking.objects.get_or_create(
            session=session,
            client=client,
            defaults={
                'status': 'CONFIRMED',
                'attendance_status': 'PENDING'
            }
        )
```

---

## 📞 Soporte

Para reportar bugs o solicitar nuevas funcionalidades:
- **Email**: soporte@tugimnasio.com
- **Sistema de tickets**: Panel Admin → Soporte
- **Documentación completa**: [Ver INDICE_GENERAL.md](INDICE_GENERAL.md)

---

**Última actualización**: 2024-01-15  
**Versión**: 1.0.0  
**Autor**: Sistema CRM Gimnasios
