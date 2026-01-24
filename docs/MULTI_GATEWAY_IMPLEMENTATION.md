# Implementación Multi-Pasarela Stripe + Redsys

## Resumen

Se ha implementado un sistema completo de coexistencia de pasarelas de pago (Stripe y Redsys) que permite:

1. **Configuración a nivel de gimnasio** - Estrategia de pasarela principal para App y POS
2. **Preferencia a nivel de cliente** - Cada cliente puede tener su pasarela preferida
3. **Tracking de pasarela por operación** - Cada pago registra qué pasarela se utilizó

---

## Cambios en Modelos

### finance/models.py - FinanceSettings

```python
GATEWAY_STRATEGY_CHOICES = [
    ('STRIPE_ONLY', 'Solo Stripe'),
    ('REDSYS_ONLY', 'Solo Redsys'),
    ('STRIPE_PRIMARY', 'Stripe primario, Redsys secundario'),
    ('REDSYS_PRIMARY', 'Redsys primario, Stripe secundario'),
    ('CLIENT_CHOICE', 'El cliente elige'),
]

# Nuevos campos añadidos:
- app_gateway_strategy: CharField (estrategia para app/online)
- pos_gateway_strategy: CharField (estrategia para POS/backoffice)

# Nuevos métodos helper:
- has_stripe: Verifica si Stripe está configurado
- has_redsys: Verifica si Redsys está configurado
- get_available_gateways(): Lista pasarelas disponibles
- get_primary_gateway(context): Obtiene pasarela principal según contexto
```

### clients/models.py - Client

```python
GATEWAY_PREFERENCE_CHOICES = [
    ('AUTO', 'Automático (según gimnasio)'),
    ('STRIPE', 'Stripe'),
    ('REDSYS', 'Redsys'),
]

# Nuevo campo añadido:
- preferred_gateway: CharField (preferencia de pasarela del cliente)
```

### sales/models.py - OrderPayment

```python
GATEWAY_CHOICES = [
    ('NONE', 'Sin pasarela'),
    ('STRIPE', 'Stripe'),
    ('REDSYS', 'Redsys'),
]

# Nuevo campo añadido:
- gateway_used: CharField (pasarela utilizada en el pago)
```

---

## Migraciones Aplicadas

1. `finance/migrations/0013_gateway_strategy.py` - Campos de estrategia en FinanceSettings
2. `clients/migrations/0023_gateway_strategy.py` - Campo preferred_gateway en Client
3. `sales/migrations/0003_gateway_strategy.py` - Campo gateway_used en OrderPayment

---

## Templates Actualizados

### templates/backoffice/app/settings.html

Nueva sección "Pasarela de Pago en la App" con:
- Indicadores de configuración de Stripe y Redsys (verde = configurado)
- Selector de estrategia de pasarela con descripciones
- Información visual del estado de cada pasarela

### templates/backoffice/finance/billing_dashboard.html

**Tabla "Desglose de Operaciones":**
- Nueva columna "Pasarela"
- Badge morado para Stripe, rojo para Redsys

**Tabla "Próximos Cobros" (suscripciones pendientes):**
- Nueva columna "Pasarela"
- Muestra la pasarela preferida del cliente o "Auto" si no hay preferencia

### templates/backoffice/clients/list.html

- Nueva columna "Pasarela" en la tabla de clientes
- Badge morado para Stripe, rojo para Redsys, gris para Auto
- Nuevo filtro "Pasarela Pago" en el formulario de filtros

### templates/backoffice/clients/detail.html

- Selector de pasarela preferida en la sección "Métodos de Pago"
- Actualización vía AJAX sin recargar la página
- Notificación toast al cambiar la pasarela

---

## Vistas/Endpoints Nuevos

### clients/views.py

**Nueva vista:** `client_update_preferred_gateway`
- URL: `/backoffice/clients/<client_id>/update-gateway/`
- Método: POST
- Permisos: `clients.change`
- Payload: `{"gateway": "AUTO|STRIPE|REDSYS"}`

**Vista actualizada:** `clients_list`
- Nuevo filtro `gateway` para filtrar clientes por pasarela preferida

---

## Formularios Actualizados

### finance/forms.py - AppSettingsForm

- Nuevo campo `app_gateway_strategy` para configurar la estrategia de pasarela

---

## Flujo de Selección de Pasarela

```
1. El gimnasio configura su estrategia en "App del Cliente" > "Pasarela de Pago"
   
2. Cuando se procesa un pago:
   a. Si el cliente tiene preferred_gateway != 'AUTO': usar esa pasarela
   b. Si preferred_gateway == 'AUTO': usar get_primary_gateway() del gimnasio
   
3. La pasarela utilizada se guarda en OrderPayment.gateway_used

4. En el billing dashboard se puede ver qué pasarela se usó en cada operación
```

---

## Estrategias Disponibles

| Estrategia | Comportamiento |
|------------|----------------|
| `STRIPE_ONLY` | Solo se ofrece Stripe como método de pago |
| `REDSYS_ONLY` | Solo se ofrece Redsys como método de pago |
| `STRIPE_PRIMARY` | Stripe por defecto, Redsys como alternativa |
| `REDSYS_PRIMARY` | Redsys por defecto, Stripe como alternativa |
| `CLIENT_CHOICE` | El cliente puede elegir en cada compra |

---

## Próximos Pasos Sugeridos

1. **App Flutter**: Implementar selector de pasarela según `app_gateway_strategy`
2. **Checkout**: Modificar flujo de checkout para respetar preferencias
3. **Cobros automáticos**: Usar `preferred_gateway` en renovaciones automáticas
4. **Reportes**: Añadir estadísticas por pasarela en analytics

---

## Archivos Modificados

```
finance/models.py         # Campos de estrategia
finance/forms.py          # Formulario AppSettings
finance/views.py          # Context con finance_settings
clients/models.py         # Campo preferred_gateway
clients/views.py          # Vista y filtro de pasarela
sales/models.py           # Campo gateway_used
backoffice/urls.py        # URL update-gateway
api/shop_views.py         # Nuevo archivo (requerido por imports)

templates/backoffice/app/settings.html           # UI configuración pasarela
templates/backoffice/finance/billing_dashboard.html  # Columnas pasarela
templates/backoffice/clients/list.html           # Columna y filtro pasarela
templates/backoffice/clients/detail.html         # Selector pasarela cliente
```
