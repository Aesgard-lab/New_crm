# Guía de Gestión de Pagos del Gimnasio

## Funcionalidad Implementada

Se ha añadido la funcionalidad completa para que los gimnasios puedan gestionar sus métodos de pago (tarjetas bancarias) para realizar los pagos de suscripción al SaaS.

## Características

### 1. Vista de Métodos de Pago
- **Ubicación**: `/billing/dashboard/` (enlace en el sidebar "Facturación y Suscripción")
- Los gimnasios pueden ver todas sus tarjetas guardadas
- Muestra información básica: marca de la tarjeta y últimos 4 dígitos

### 2. Añadir Tarjetas
- Botón "Añadir" en la sección de Métodos de Pago
- Modal con formulario seguro de Stripe Elements
- Integración con Stripe SetupIntent para capturar los datos de la tarjeta sin cargo
- La tarjeta se asocia automáticamente como método de pago predeterminado
- Validación en tiempo real del formulario

### 3. Eliminar Tarjetas
- Botón "Eliminar" junto a cada tarjeta guardada
- Confirmación antes de eliminar
- La tarjeta se desvincula del cliente en Stripe

## Flujo Técnico

### Backend

#### Nuevos Endpoints (saas_billing/gym_views.py)

1. **`create_setup_intent`** (POST)
   - Crea un SetupIntent de Stripe
   - Crea un cliente de Stripe si no existe
   - Devuelve el clientSecret para el formulario

2. **`save_payment_method`** (POST)
   - Vincula el método de pago al cliente
   - Lo establece como método predeterminado
   - Guarda los últimos 4 dígitos y la marca en la BD

3. **`delete_payment_method`** (POST)
   - Desvincula el método de pago del cliente en Stripe
   - Limpia los datos locales

#### Servicios de Stripe (saas_billing/stripe_service.py)

Nuevos métodos añadidos:
- `create_setup_intent(customer_id)`: Crea un SetupIntent
- `attach_payment_method(payment_method_id, customer_id)`: Vincula y establece como predeterminado
- `get_payment_methods(customer_id)`: Lista todos los métodos de pago
- `detach_payment_method(payment_method_id)`: Elimina un método de pago

### Frontend

#### Template (templates/saas_billing/gym/dashboard.html)

**Nueva Sección: Métodos de Pago**
- Tarjeta en el sidebar derecho
- Lista de tarjetas guardadas
- Botón para añadir nueva tarjeta
- Integración con Stripe.js v3

**Modal de Añadir Tarjeta**
- Formulario con Stripe Elements
- Estilizado para coincidir con el diseño del sistema
- Validación en tiempo real
- Feedback de errores
- Indicador de carga durante el procesamiento

#### JavaScript
- Inicialización de Stripe con clave pública
- Manejo del flujo de SetupIntent
- Confirmación de la tarjeta
- Guardado del método de pago
- Eliminación con confirmación

## Configuración Requerida

### 1. Variables de Stripe
Asegúrate de configurar las claves de Stripe en el panel de Superadmin:
- **Stripe Publishable Key** (pk_test_... o pk_live_...)
- **Stripe Secret Key** (sk_test_... o sk_live_...)
- **Webhook Secret** (whsec_...)

### 2. Base de Datos
El modelo `GymSubscription` ya incluye los campos necesarios:
- `stripe_customer_id`: ID del cliente en Stripe
- `stripe_subscription_id`: ID de la suscripción
- `payment_method_last4`: Últimos 4 dígitos de la tarjeta
- `payment_method_brand`: Marca de la tarjeta (Visa, Mastercard, etc.)

No se requieren migraciones adicionales.

## Seguridad

### Protección de Datos
- **No se almacenan números de tarjeta completos**: Solo los últimos 4 dígitos
- **PCI Compliance**: Stripe maneja todos los datos sensibles
- **CSRF Protection**: Todos los endpoints POST están protegidos
- **Authentication**: Login requerido para todas las vistas
- **Gym Isolation**: Solo se pueden ver/modificar métodos del gimnasio actual

### Validación
- Validación de entrada en el backend
- Verificación de permisos
- Manejo de errores de Stripe con logs

## Uso

### Para el Administrador del Gimnasio

1. **Ver Métodos de Pago**
   - Ir a "Facturación y Suscripción" en el menú lateral
   - La sección "Métodos de Pago" muestra las tarjetas guardadas

2. **Añadir Tarjeta**
   - Click en "Añadir" o "Añadir tarjeta"
   - Se abre un modal con el formulario
   - Introduce los datos de la tarjeta
   - Click en "Guardar Tarjeta"
   - La página se recarga mostrando la nueva tarjeta

3. **Eliminar Tarjeta**
   - Click en "Eliminar" junto a la tarjeta
   - Confirmar la acción
   - La página se recarga sin la tarjeta

### Integración con Pagos Automáticos

Los métodos de pago guardados se utilizan automáticamente para:
- Renovación de suscripciones mensuales/anuales
- Cobro de facturas pendientes
- Cargos adicionales según el plan

## Testing

### Tarjetas de Prueba de Stripe

Para probar en modo test, usa estas tarjetas:

**Pago Exitoso:**
- Número: 4242 4242 4242 4242
- Fecha: Cualquier fecha futura
- CVC: Cualquier 3 dígitos
- ZIP: Cualquier código postal

**Pago Rechazado:**
- Número: 4000 0000 0000 0002

**Requiere Autenticación (3D Secure):**
- Número: 4000 0027 6000 3184

## Mejoras Futuras

1. **Múltiples Tarjetas**: Permitir guardar varias tarjetas y elegir la predeterminada
2. **Otros Métodos de Pago**: Añadir SEPA Direct Debit, PayPal, etc.
3. **Historial de Cargos**: Vista detallada de todos los cargos realizados
4. **Notificaciones**: Email cuando falla un pago o se añade/elimina una tarjeta
5. **Facturación Automática**: Generar facturas PDF automáticamente después de cada cargo
6. **Portal de Stripe**: Mantener el enlace al portal de Stripe para gestión avanzada

## Soporte

Si hay problemas con los pagos:
1. Verificar que las claves de Stripe estén configuradas correctamente
2. Revisar los logs de Django para errores de Stripe
3. Consultar el Dashboard de Stripe para ver los eventos y errores
4. Verificar que el webhook esté configurado y funcionando

## Archivos Modificados

- `saas_billing/gym_views.py`: Vistas para gestión de métodos de pago
- `saas_billing/stripe_service.py`: Servicios de integración con Stripe
- `saas_billing/urls.py`: Nuevas rutas para los endpoints
- `templates/saas_billing/gym/dashboard.html`: UI para métodos de pago

## Documentación Relacionada

- [Stripe SetupIntents Documentation](https://stripe.com/docs/payments/setup-intents)
- [Stripe Elements Documentation](https://stripe.com/docs/stripe-js)
- [PCI Compliance](https://stripe.com/docs/security/guide)
