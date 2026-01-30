# 📅 Sistema de Sincronización de Calendario

Este documento describe el sistema de sincronización de calendario implementado para el CRM.

## Funcionalidades

### 1. Feed iCal (URL de suscripción)
Los clientes pueden obtener una URL única que pueden añadir como suscripción a cualquier aplicación de calendario (Google Calendar, Apple Calendar, Outlook, etc.).

**Características:**
- Se actualiza automáticamente cuando el cliente reserva o cancela clases
- Incluye recordatorios (30 minutos y 2 horas antes)
- Muestra las reservas de las últimas 2 semanas + futuras

### 2. Descarga de .ics individual
Los clientes pueden descargar un archivo .ics para una reserva específica y añadirla manualmente a su calendario.

### 3. API para app móvil Flutter
Endpoints REST para integración con la app móvil.

---

## Endpoints Disponibles

### Portal del Cliente (`/portal/...`)
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/portal/calendar/` | GET | Página de sincronización de calendario |
| `/portal/calendar/settings/` | GET | Obtener URL del feed (JSON) |
| `/portal/calendar/regenerate-token/` | POST | Regenerar token del feed |
| `/portal/calendar/booking/<id>/download/` | GET | Descargar .ics de una reserva |

### Portal Público (`/public/gym/<slug>/...`)
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/public/gym/<slug>/calendar/` | GET | Página de sincronización |
| `/public/gym/<slug>/calendar/settings/` | GET | Obtener URL del feed |
| `/public/gym/<slug>/calendar/regenerate-token/` | POST | Regenerar token |
| `/public/gym/<slug>/calendar/booking/<id>/download/` | GET | Descargar .ics |

### API REST (`/api/...`)
| Endpoint | Método | Autenticación | Descripción |
|----------|--------|---------------|-------------|
| `/api/calendar/settings/` | GET | Token | Obtener URL del feed |
| `/api/calendar/regenerate-token/` | POST | Token | Regenerar token |
| `/api/calendar/booking/<id>/ics/` | GET | Token | Descargar .ics |
| `/api/calendar/add-event/` | POST | Token | Datos del evento para añadir al calendario nativo |

### Feed Público (sin autenticación)
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/calendar/feed/<token>.ics` | GET | Feed iCal para suscripción |

---

## Integración con Flutter

### 1. Obtener URL del feed
```dart
// GET /api/calendar/settings/
final response = await http.get(
  Uri.parse('$baseUrl/api/calendar/settings/'),
  headers: {'Authorization': 'Token $token'},
);

final data = jsonDecode(response.body);
final feedUrl = data['feed_url'];
// feedUrl = "https://domain.com/calendar/feed/abc123.ics"
```

### 2. Añadir evento al calendario nativo
Usa el paquete `device_calendar` o `add_2_calendar`:

```dart
// POST /api/calendar/add-event/
final response = await http.post(
  Uri.parse('$baseUrl/api/calendar/add-event/'),
  headers: {
    'Authorization': 'Token $token',
    'Content-Type': 'application/json',
  },
  body: jsonEncode({'booking_id': bookingId}),
);

final eventData = jsonDecode(response.body);
// {
//   "title": "Yoga",
//   "description": "📍 GymName\n👤 Instructor: Juan\n🚪 Sala: Sala 1",
//   "start": "2024-01-15T10:00:00+01:00",
//   "end": "2024-01-15T11:00:00+01:00",
//   "location": "Sala: Sala 1, Calle Principal 123, Madrid",
//   "reminder_minutes": [30, 120]
// }

// Usar device_calendar para añadir el evento
import 'package:device_calendar/device_calendar.dart';

final deviceCalendarPlugin = DeviceCalendarPlugin();
final calendars = await deviceCalendarPlugin.retrieveCalendars();
final calendar = calendars.data!.first; // O dejar que el usuario elija

final event = Event(
  calendar.id,
  title: eventData['title'],
  description: eventData['description'],
  start: TZDateTime.parse(local, eventData['start']),
  end: TZDateTime.parse(local, eventData['end']),
  location: eventData['location'],
);

// Añadir recordatorios
for (final minutes in eventData['reminder_minutes']) {
  event.reminders.add(Reminder(minutes: minutes));
}

await deviceCalendarPlugin.createOrUpdateEvent(event);
```

### 3. Permisos necesarios en Flutter

**Android** (`android/app/src/main/AndroidManifest.xml`):
```xml
<uses-permission android:name="android.permission.READ_CALENDAR"/>
<uses-permission android:name="android.permission.WRITE_CALENDAR"/>
```

**iOS** (`ios/Runner/Info.plist`):
```xml
<key>NSCalendarsUsageDescription</key>
<string>Necesitamos acceso a tu calendario para añadir tus reservas de clases</string>
```

---

## Modelo de Datos

### Campo añadido a Client
```python
# clients/models.py
calendar_token = models.CharField(
    max_length=64, 
    blank=True, 
    null=True, 
    unique=True,
    help_text="Token único para la URL de suscripción al calendario"
)
```

### Migración
```
clients/migrations/0104_add_calendar_token.py
```

---

## Dependencias

```
# requirements.txt
icalendar>=5.0.0
```

---

## Ejemplos de Uso

### Copiar URL de suscripción al portapapeles (JavaScript)
```javascript
async function copyCalendarUrl() {
    const response = await fetch('/portal/calendar/settings/');
    const data = await response.json();
    await navigator.clipboard.writeText(data.feed_url);
    alert('URL copiada al portapapeles');
}
```

### Regenerar token de seguridad
```javascript
async function regenerateToken() {
    const response = await fetch('/portal/calendar/regenerate-token/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        }
    });
    const data = await response.json();
    // data.feed_url contiene la nueva URL
}
```
