# API de Adelantar Pago - Documentación

## Descripción General

Esta API permite a los clientes adelantar el pago de su próxima cuota de membresía antes de la fecha programada. La funcionalidad debe estar habilitada en la configuración financiera del gimnasio (`FinanceSettings.allow_client_pay_next_fee = True`).

## Endpoints

### 1. Obtener Información de Adelanto de Pago

**GET** `/api/advance-payment/info/`

Retorna información sobre la capacidad del cliente para adelantar el pago, incluyendo detalles de la membresía, próxima fecha de cobro, monto y estado del método de pago.

#### Headers Requeridos
```
Authorization: Token <user_token>
```

#### Respuesta Exitosa (200)
```json
{
  "success": true,
  "enabled": true,
  "has_payment_method": true,
  "payment_method": {
    "type": "stripe",
    "has_method": true
  },
  "membership": {
    "id": 123,
    "plan_name": "Plan Premium Mensual",
    "status": "ACTIVE",
    "is_recurring": true,
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-02-01T00:00:00Z",
    "next_billing_date": "2024-02-01T00:00:00Z",
    "amount": 49.99
  }
}
```

#### Respuestas de Error

**403 - Funcionalidad deshabilitada**
```json
{
  "success": false,
  "enabled": false,
  "error": "Esta funcionalidad no está habilitada para este gimnasio"
}
```

**404 - Cliente no encontrado**
```json
{
  "success": false,
  "error": "Cliente no encontrado"
}
```

**200 - Sin membresía recurrente activa**
```json
{
  "success": false,
  "enabled": true,
  "error": "No tienes una membresía activa recurrente",
  "membership": null
}
```

---

### 2. Procesar Adelanto de Pago

**POST** `/api/advance-payment/process/`

Procesa un pago adelantado para la próxima cuota de membresía del cliente. Requiere que el cliente tenga una membresía activa recurrente y un método de pago válido.

#### Headers Requeridos
```
Authorization: Token <user_token>
Content-Type: application/json
```

#### Body
```json
{}
```
*No se requieren parámetros en el body. Toda la información se obtiene del usuario autenticado.*

#### Respuesta Exitosa (200)
```json
{
  "success": true,
  "message": "✅ Pago procesado exitosamente. Tu membresía ha sido extendida.",
  "new_end_date": "2024-03-01T00:00:00Z",
  "new_billing_date": "2024-03-01T00:00:00Z",
  "amount_charged": 49.99,
  "payment_date": "2024-01-15T10:30:00Z"
}
```

#### Respuestas de Error

**400 - Sin membresía recurrente**
```json
{
  "success": false,
  "error": "No tienes una membresía activa recurrente para adelantar el pago"
}
```

**400 - Sin método de pago**
```json
{
  "success": false,
  "error": "No tienes un método de pago vinculado. Por favor, agrega una tarjeta antes de continuar."
}
```

**400 - Error en el cobro**
```json
{
  "success": false,
  "error": "Error al procesar el pago: Tarjeta rechazada"
}
```

**403 - Funcionalidad deshabilitada**
```json
{
  "success": false,
  "error": "Esta funcionalidad no está habilitada"
}
```

**404 - Cliente no encontrado**
```json
{
  "success": false,
  "error": "Cliente no encontrado"
}
```

**500 - Error del servidor**
```json
{
  "success": false,
  "error": "Error inesperado al procesar el pago: <detalle del error>"
}
```

---

## Flujo de Uso Recomendado

### En la App Flutter

1. **Al cargar la pantalla de membresía:**
   - Llamar a `GET /api/advance-payment/info/`
   - Si `enabled: false`, no mostrar la opción de adelantar pago
   - Si `enabled: true` pero `has_payment_method: false`, mostrar botón deshabilitado con mensaje "Debes agregar un método de pago"
   - Si `enabled: true` y `has_payment_method: true`, mostrar botón "Adelantar Cobro" habilitado

2. **Al presionar el botón "Adelantar Cobro":**
   - Mostrar modal de confirmación:
     - "¿Estás seguro de que deseas adelantar el pago de tu cuota?"
     - Mostrar: Plan, Monto, Próxima fecha de cobro
   - Si el usuario confirma, llamar a `POST /api/advance-payment/process/`

3. **Al recibir la respuesta del POST:**
   - Si `success: true`: Mostrar mensaje de éxito con las nuevas fechas
   - Si `success: false`: Mostrar el error al usuario
   - Recargar la información de la membresía

### Ejemplo de código Flutter

```dart
// 1. Obtener información
Future<AdvancePaymentInfo> getAdvancePaymentInfo() async {
  final response = await dio.get(
    '/api/advance-payment/info/',
    options: Options(headers: {'Authorization': 'Token $token'}),
  );
  return AdvancePaymentInfo.fromJson(response.data);
}

// 2. Procesar pago adelantado
Future<AdvancePaymentResult> processAdvancePayment() async {
  final response = await dio.post(
    '/api/advance-payment/process/',
    options: Options(headers: {'Authorization': 'Token $token'}),
  );
  return AdvancePaymentResult.fromJson(response.data);
}

// 3. Uso en el widget
ElevatedButton(
  onPressed: info.enabled && info.hasPaymentMethod 
    ? () async {
        final confirm = await showConfirmDialog();
        if (confirm) {
          final result = await processAdvancePayment();
          if (result.success) {
            showSuccessMessage(result.message);
          } else {
            showErrorMessage(result.error);
          }
        }
      }
    : null,
  child: Text('Adelantar Cobro'),
)
```

---

## Lógica de Negocio

### Validaciones
1. El usuario debe estar autenticado
2. Debe existir un cliente asociado al usuario
3. La funcionalidad debe estar habilitada en `FinanceSettings`
4. El cliente debe tener una membresía activa recurrente (`status='ACTIVE'` y `is_recurring=True`)
5. El cliente debe tener un método de pago guardado (Stripe customer ID + payment method ID)

### Procesamiento del Pago
1. Se calcula el monto desde `membership.plan.final_price`
2. Se genera un concepto descriptivo: "Adelanto de cuota - {plan} - Fecha: {fecha}"
3. Se procesa el cargo usando `charge_client_off_session()` de `finance.payment_strategies`
4. Si el pago es exitoso:
   - Se crea un registro en `ClientPayment` con status='PAID'
   - Se extiende `membership.end_date` por 30 días
   - Se actualiza `membership.next_billing_date` por 30 días
   - Se guarda la membresía

### Seguridad
- Uso de `@transaction.atomic` para garantizar consistencia de datos
- `select_for_update()` en la membresía para evitar race conditions
- Validación de permisos en cada endpoint
- Manejo de excepciones con respuestas apropiadas

---

## Configuración en el Backoffice

Para habilitar esta funcionalidad:

1. Ir a **Configuración** > **Finanzas**
2. Activar el checkbox **"Permitir pagar la siguiente cuota"**
3. Guardar cambios

La opción aparecerá automáticamente en el portal del cliente y en la app móvil.

---

## Notas Técnicas

- **Autenticación**: Usa `IsAuthenticated` de Django Rest Framework
- **Base de datos**: Transacciones atómicas para integridad de datos
- **Gateway de pago**: Compatible con Stripe y Redsys (según configuración del gimnasio)
- **Extensión de membresía**: Siempre 30 días (puede parametrizarse en el futuro)
- **Formato de fechas**: ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`)

---

## Contacto y Soporte

Para dudas sobre la implementación, contactar al equipo de desarrollo.
