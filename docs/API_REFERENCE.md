# API Reference

## Overview

This document describes the REST API for the CRM/Gym Management System.

**Base URL:** `/api/`

**Authentication:**
- Token Authentication: `Authorization: Token <token>`
- Session Authentication (for browser-based clients)

**Response Format:**
All responses follow this structure:

```json
// Success
{
  "success": true,
  "message": "Optional message",
  "data": { ... }
}

// Error
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE",
  "field_errors": { "field": ["error"] }
}
```

---

## Authentication

### Login

```http
POST /api/auth/login/
```

Authenticate a user and receive an access token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "gym_id": 1
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "token": "abc123...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "client": {
    "id": 1,
    "gym_id": 1,
    "status": "ACTIVE"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid credentials
- `403 Forbidden`: Account disabled

---

### Check Authentication

```http
GET /api/auth/check/
```

Verify current authentication status.

**Headers:**
```
Authorization: Token <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "authenticated": true,
  "user": {
    "id": 1,
    "email": "user@example.com"
  }
}
```

---

### Logout

```http
POST /api/auth/logout/
```

Invalidate the current token.

**Headers:**
```
Authorization: Token <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## User Profile

### Get Profile

```http
GET /api/profile/
```

Get the authenticated user's profile.

**Headers:**
```
Authorization: Token <token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone": "+34612345678",
  "dni": "12345678A",
  "birth_date_formatted": "15/03/1990",
  "photo_url": "/media/clients/photos/1.jpg",
  "gym": {
    "id": 1,
    "name": "Fitness Center"
  },
  "membership": {
    "id": 1,
    "name": "Plan Mensual",
    "status": "ACTIVE",
    "end_date": "2026-03-01",
    "sessions_remaining": 10
  }
}
```

---

### Update Profile

```http
PUT /api/profile/
```

Update the authenticated user's profile.

**Headers:**
```
Authorization: Token <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+34612345678",
  "address": "Calle Example 123"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Perfil actualizado"
}
```

---

## Activities

### List Activities

```http
GET /api/activities/
```

Get all activities available at the gym.

**Headers:**
```
Authorization: Token <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | int | Filter by category ID |
| `date` | string | Filter by date (YYYY-MM-DD) |

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Yoga",
      "description": "Relaxing yoga class",
      "duration": 60,
      "base_capacity": 20,
      "category": {
        "id": 1,
        "name": "Mind & Body"
      }
    }
  ]
}
```

---

### List Sessions

```http
GET /api/activities/sessions/
```

Get upcoming activity sessions.

**Headers:**
```
Authorization: Token <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `activity_id` | int | Filter by activity |
| `date_from` | string | Start date (YYYY-MM-DD) |
| `date_to` | string | End date (YYYY-MM-DD) |
| `page` | int | Page number |
| `page_size` | int | Items per page (default 20) |

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "activity": {
        "id": 1,
        "name": "Yoga"
      },
      "start_datetime": "2026-02-04T10:00:00Z",
      "end_datetime": "2026-02-04T11:00:00Z",
      "max_capacity": 20,
      "current_bookings": 5,
      "available_spots": 15,
      "status": "SCHEDULED",
      "instructor": "María García"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 50,
    "total_pages": 3
  }
}
```

---

## Bookings

### Create Booking

```http
POST /api/bookings/
```

Book a spot in an activity session.

**Headers:**
```
Authorization: Token <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "session_id": 1
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Reserva confirmada",
  "booking": {
    "id": 1,
    "session_id": 1,
    "status": "CONFIRMED",
    "created_at": "2026-02-03T15:30:00Z"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Session full or already booked
- `403 Forbidden`: No active membership

---

### List My Bookings

```http
GET /api/bookings/
```

Get authenticated user's bookings.

**Headers:**
```
Authorization: Token <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (CONFIRMED, CANCELLED, ATTENDED) |
| `upcoming` | boolean | Only future sessions |

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "session": {
        "id": 1,
        "activity_name": "Yoga",
        "start_datetime": "2026-02-04T10:00:00Z"
      },
      "status": "CONFIRMED",
      "created_at": "2026-02-03T15:30:00Z"
    }
  ]
}
```

---

### Cancel Booking

```http
DELETE /api/bookings/{booking_id}/
```

Cancel a booking.

**Headers:**
```
Authorization: Token <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Reserva cancelada"
}
```

**Error Responses:**
- `400 Bad Request`: Cancellation not allowed (too late)
- `404 Not Found`: Booking not found

---

## Memberships

### Get Active Membership

```http
GET /api/membership/
```

Get the authenticated user's active membership.

**Headers:**
```
Authorization: Token <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "membership": {
    "id": 1,
    "plan": {
      "id": 1,
      "name": "Plan Mensual",
      "description": "Acceso ilimitado"
    },
    "status": "ACTIVE",
    "start_date": "2026-01-01",
    "end_date": "2026-02-01",
    "days_remaining": 28,
    "sessions_total": null,
    "sessions_used": 0,
    "sessions_remaining": null,
    "is_unlimited": true
  }
}
```

---

### List Available Plans

```http
GET /api/plans/
```

Get available membership plans.

**Headers:**
```
Authorization: Token <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Plan Mensual",
      "description": "Acceso ilimitado a todas las instalaciones",
      "base_price": "49.99",
      "is_recurring": true,
      "frequency_unit": "MONTH",
      "is_visible_online": true
    }
  ]
}
```

---

## Notifications

### List Notifications

```http
GET /api/notifications/
```

Get user's notifications.

**Headers:**
```
Authorization: Token <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `unread` | boolean | Only unread notifications |
| `page` | int | Page number |

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "Clase confirmada",
      "message": "Tu reserva para Yoga ha sido confirmada",
      "type": "BOOKING_CONFIRMED",
      "is_read": false,
      "created_at": "2026-02-03T15:30:00Z"
    }
  ],
  "unread_count": 5
}
```

---

### Mark as Read

```http
POST /api/notifications/{id}/read/
```

Mark a notification as read.

**Headers:**
```
Authorization: Token <token>
```

**Response (200 OK):**
```json
{
  "success": true
}
```

---

## Check-in

### QR Check-in

```http
POST /api/checkin/qr/
```

Perform check-in via QR code.

**Request Body:**
```json
{
  "qr_token": "abc123...",
  "session_id": 1
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Check-in realizado",
  "client": {
    "name": "John Doe",
    "photo_url": "/media/clients/1.jpg"
  }
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_ERROR` | Authentication required or failed |
| `PERMISSION_DENIED` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `VALIDATION_ERROR` | Invalid input data |
| `DUPLICATE_EMAIL` | Email already exists |
| `DUPLICATE_DNI` | DNI already exists |
| `ACTIVE_MEMBERSHIP_EXISTS` | Client already has active membership |
| `SESSION_FULL` | No available spots |
| `ALREADY_BOOKED` | Already has booking for this session |
| `CANCELLATION_NOT_ALLOWED` | Too late to cancel |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INTERNAL_ERROR` | Server error |

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

| Endpoint Type | Limit |
|---------------|-------|
| Authentication | 5/minute |
| API General | 100/minute |
| Heavy Operations | 20/minute |
| Public Endpoints | 30/minute |

When rate limited, you'll receive:
```json
{
  "success": false,
  "error": "Demasiadas solicitudes. Intenta de nuevo en 60 segundos.",
  "code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "retry_after": 60
  }
}
```

---

## Webhooks

The system can send webhooks for certain events. Contact your administrator to configure webhook endpoints.

### Events

| Event | Description |
|-------|-------------|
| `membership.created` | New membership assigned |
| `membership.expired` | Membership expired |
| `booking.created` | New booking made |
| `booking.cancelled` | Booking cancelled |
| `payment.completed` | Payment processed |
| `payment.failed` | Payment failed |

### Webhook Payload

```json
{
  "event": "booking.created",
  "timestamp": "2026-02-03T15:30:00Z",
  "data": {
    "booking_id": 1,
    "client_id": 1,
    "session_id": 1
  },
  "signature": "sha256=..."
}
```

---

## SDK Examples

### Python

```python
import requests

BASE_URL = "https://your-crm.com/api"
TOKEN = "your-token"

headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# Get profile
response = requests.get(f"{BASE_URL}/profile/", headers=headers)
profile = response.json()

# Book a session
booking_data = {"session_id": 1}
response = requests.post(
    f"{BASE_URL}/bookings/",
    json=booking_data,
    headers=headers
)
```

### JavaScript

```javascript
const BASE_URL = 'https://your-crm.com/api';
const TOKEN = 'your-token';

// Get profile
const response = await fetch(`${BASE_URL}/profile/`, {
  headers: {
    'Authorization': `Token ${TOKEN}`,
  },
});
const profile = await response.json();

// Book a session
const bookingResponse = await fetch(`${BASE_URL}/bookings/`, {
  method: 'POST',
  headers: {
    'Authorization': `Token ${TOKEN}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ session_id: 1 }),
});
```

---

## Changelog

### v1.0.0 (2026-02-03)
- Initial API documentation
- Authentication endpoints
- Profile management
- Activity booking system
- Membership management
- Notifications
- QR Check-in
