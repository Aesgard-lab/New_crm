# 🏗️ DIAGRAMA DE ARQUITECTURA COMPLETA

## Vista General del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKOFFICE CRM - ARQUITECTURA                     │
└─────────────────────────────────────────────────────────────────────┘

                           ┌──────────────┐
                           │  NAVEGADOR   │
                           │   (Usuario)  │
                           └──────┬───────┘
                                  │
                         ┌────────┴────────┐
                         │                 │
                    /admin/          /backoffice/*
                         │                 │
                         └────────┬────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   Django URL Router        │
                    │   (config/urls.py)         │
                    └─────────────┬──────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
   ┌────▼──────┐         ┌───────▼────┐         ┌─────────▼─────┐
   │ Admin Site│         │ Backoffice │         │ Member Portal │
   │(Django)   │         │ (Views)    │         │ (Client App)  │
   └─────┬──────┘        └───────┬────┘         └──────────┬────┘
         │                       │                         │
         │              ┌────────▼────────┐                │
         │              │ Settings Views  │                │
         │              │                 │                │
         │              │ ✅ gym_settings │                │
         │              │ ✅ finance_*    │                │
         │              │ ✅ staff_*      │                │
         │              │ ✅ activity_*   │                │
         │              │ ⚠️  incentive_* │                │
         │              └────────┬────────┘                │
         │                       │                         │
         └───────────┬───────────┼─────────┬───────────────┘
                     │           │         │
              ┌──────▼───────────▼─────────▼──────┐
              │  MODELOS DE DATOS (Django ORM)    │
              │                                    │
              │  ✅ accounts.User                  │
              │  ✅ organizations.Gym              │
              │  ✅ organizations.Franchise        │
              │  ✅ clients.Client                 │
              │  ✅ staff.StaffProfile             │
              │  ✅ activities.Activity            │
              │  ✅ services.Service               │
              │  ✅ products.Product               │
              │  ✅ memberships.MembershipPlan     │
              │  ✅ finance.TaxRate                │
              │  ✅ finance.PaymentMethod          │
              │  ✅ finance.CashSession            │
              │  ✅ finance.FinanceSettings        │
              │  ✅ sales.Order                    │
              │  ✅ marketing.MarketingSettings    │
              │  ✅ marketing.EmailTemplate        │
              │  ✅ marketing.Campaign             │
              │                                    │
              └──────────────┬─────────────────────┘
                             │
                   ┌─────────▼──────────┐
                   │  PostgreSQL DB     │
                   │                    │
                   │ new_gym (default)  │
                   └────────────────────┘
```

---

## 🎯 SETTINGS DASHBOARD - DETALLADO

```
┌─────────────────────────────────────────────────────────┐
│   BACKOFFICE → /settings/                               │
│   Template: backoffice/settings/dashboard.html           │
└─────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
       ┌────▼──────┐   ┌────▼──────┐   ┌──▼──────┐
       │  EMPRESA   │   │   EQUIPO   │   │SERVICIOS│
       │  (🏢)      │   │   (👥)     │   │  (⚙️)   │
       └────┬──────┘   └────┬──────┘   └──┬──────┘
            │               │             │
       ┌────▼────┐     ┌────▼────┐   ┌──▼──────┐
       │gym.html │     │ roles.  │   │activity │
       │horarios │     │ audit_  │   │service  │
       │         │     │ logs    │   │member.  │
       │         │     │         │   │product  │
       └─────────┘     └─────────┘   └─────────┘

            │               │             │
       ┌────▼──────┐   ┌────▼──────┐   ┌──▼──────┐
       │ FINANZAS   │   │ MARKETING  │   │ SISTEMA │
       │   (💰)     │   │    (📧)    │   │  (⚙️⚙️) │
       └────┬──────┘   └────┬──────┘   └──┬──────┘
            │               │             │
       ┌────▼────┐     ┌────▼────┐   ┌──▼──────┐
       │tax_rates│     │smtp_    │   │audit    │
       │methods  │     │leads_   │   │hardware │
       │hardware │     │campaigns│   │         │
       │stripe   │     │         │   │         │
       │redsys   │     │         │   │         │
       └─────────┘     └─────────┘   └─────────┘
```

---

## 🔗 FLUJO DE DATOS - ORDEN DE VENTA

```
CLIENTE COMPRA → ORDER
│
├─→ Selecciona Producto/Servicio/Membresía
│   │
│   └─→ OrderItem (Polimórfica)
│       ├─→ content_type = Product
│       ├─→ object_id = 123
│       ├─→ quantity, unit_price, tax_rate
│       └─→ subtotal = quantity * unit_price * (1 + tax)
│
├─→ Elige Método de Pago
│   │
│   └─→ OrderPayment
│       ├─→ payment_method (FK PaymentMethod)
│       ├─→ amount
│       └─→ transaction_id (Stripe/Redsys)
│
├─→ Se registra en CashSession
│   │
│   └─→ CashSession
│       ├─→ opened_by (user)
│       ├─→ total_cash_sales = SUM(all orders)
│       ├─→ expected_balance = opening + sales - withdrawals
│       └─→ actual_balance (arqueo)
│
└─→ Genera Datos para Reportería
    │
    ├─→ Factura (invoice_number)
    ├─→ Comisión de staff (si aplica)
    ├─→ Stock (si product)
    └─→ Historial de cliente

CASOS ESPECIALES:
─────────────────
Servicio → ServiceAppointment (asignación de slot)
Actividad → ActivitySession (asistencia)
Membresía → Client.membership tracking
```

---

## 🏪 CATÁLOGO DE PRODUCTOS/SERVICIOS

```
┌─────────────────────────────────────────┐
│        SISTEMA DE CATÁLOGO               │
└─────────────────────────────────────────┘

    ┌──────────────────────────────────┐
    │        MembershipPlan             │
    │  (Cuotas periódicas recurrentes)  │
    │                                   │
    │  - base_price                     │
    │  - frequency: MONTH, YEAR, etc    │
    │  - prorate_first_month            │
    │  - is_recurring: bool             │
    │  - contract_required              │
    │                                   │
    │  ACCESS RULES:                    │
    │  ├─→ Activity (¿cuál?)            │
    │  ├─→ ActivityCategory (¿tipo?)    │
    │  ├─→ Service (¿cuál?)             │
    │  └─→ ServiceCategory (¿tipo?)     │
    └──────────────────────────────────┘
           │              │
           ▼              ▼
    ┌──────────────┐  ┌─────────────────┐
    │  Activity    │  │  Service        │
    │              │  │                 │
    │ Grupal       │  │ 1-on-1 / Custom │
    │ (Clases)     │  │ (Entrenador)    │
    │              │  │                 │
    │ - duration   │  │ - max_attendees │
    │ - capacity   │  │ - room          │
    │ - color      │  │ - staff         │
    │ - intensity  │  │ - base_price    │
    │              │  │                 │
    │ SCHEDULE:    │  │ BOOKING:        │
    │ ├─→ Rule     │  │ └─→ Appointment │
    │ └─→ Session  │  │     (with slots)│
    └──────────────┘  └─────────────────┘
           │                    │
           ▼                    ▼
    ┌──────────────┐  ┌─────────────────┐
    │   Product    │  │  (no product)   │
    │              │  │                 │
    │ Inventario   │  │                 │
    │ (Física)     │  │                 │
    │              │  │                 │
    │ - cost_price │  │                 │
    │ - base_price │  │                 │
    │ - stock      │  │                 │
    │ - supplier   │  │                 │
    │              │  │                 │
    │ TRACKING:    │  │                 │
    │ └─→ StockMove│  │                 │
    └──────────────┘  └─────────────────┘

TODAS COMPARTEN:
───────────────
✅ gym FK
✅ name, description
✅ category (jerárquico)
✅ base_price, tax_rate
✅ price_strategy (TAX_INCLUDED/EXCLUDED)
✅ is_active (visible en POS)
✅ is_visible_online (venta web)
```

---

## 👥 GESTIÓN DE USUARIOS Y ROLES

```
┌─────────────────────────────────────────┐
│          ACCOUNTS & STAFF                │
└─────────────────────────────────────────┘

    User (AUTH)
     │
     ├─→ Django Groups + Permissions
     │   (Admin django.contrib.auth)
     │
     └─→ StaffProfile (1-1)
         │
         ├─→ Gym (FK)
         │
         ├─→ SalaryConfig (1-1)
         │   ├─→ mode: MONTHLY / HOURLY
         │   └─→ base_amount
         │
         ├─→ IncentiveRule (M2O)
         │   ├─→ type: SALE_PCT, CLASS_FIXED, etc
         │   ├─→ value: porcentaje o cantidad
         │   └─→ criteria: filtros JSON
         │
         └─→ StaffCommission (auditoría)
             ├─→ rule (qué la generó)
             ├─→ amount (dinero ganado)
             └─→ date (cuándo)

CLIENT (USUARIO FINAL)
     │
     └─→ Client (0-1)
         ├─→ gym (FK)
         ├─→ user (FK, opcional)
         │   └─→ Si tiene user, puede hacer login
         │
         ├─→ status: LEAD, ACTIVE, INACTIVE, BLOCKED, PAUSED
         │
         ├─→ Group (M2M)
         │   └─→ Agrupación de clientes (Mañanas, VIPs, etc)
         │
         ├─→ Tag (M2M)
         │   └─→ Etiquetas (Moroso, Lesionado, Premium)
         │
         └─→ extra_data (JSON)
             └─→ Campos dinámicos

PERMISOS (CONTROL DE ACCESO):
────────────────────────────
@require_gym_permission('app.permission')
 └─→ Valida que usuario tiene permiso en gym actual
```

---

## 💰 FLUJO FINANCIERO

```
┌──────────────────────────────────────────┐
│      SISTEMA FINANCIERO COMPLETO         │
└──────────────────────────────────────────┘

    CONFIG PREVIA:
    ──────────────
    ✅ TaxRate (IVA 21%, IVA 10%, etc)
    ✅ PaymentMethod (Efectivo, Tarjeta, Stripe, etc)
    ✅ FinanceSettings (Stripe keys, Redsys config)

    ┌─────────────────┐
    │  CashSession    │
    │  (Sesión de caja)
    │                 │
    │ opened_at       │
    │ opened_by       │
    │ opening_balance │
    │                 │
    │ [Operaciones]   │
    │                 │
    │ total_cash_     │
    │ sales (auto)    │◄─── Agrupa múltiples Order
    │                 │
    │ total_cash_     │
    │ withdrawals     │
    │                 │
    │ closed_at       │
    │ closed_by       │
    │ actual_balance  │◄─── Arqueo (conteo físico)
    │ discrepancy     │◄─── expected - actual
    │                 │
    │ is_closed: bool │
    └────────┬────────┘
             │
       ┌─────▼─────────────┐
       │  Order (Ticket)   │
       │                   │
       │ [LineItems]       │
       │ ├─→ Product       │
       │ ├─→ Service       │
       │ ├─→ Membership    │
       │ └─→ Custom        │
       │                   │
       │ [Payments]        │
       │ └─→ OrderPayment  │
       │     ├─→ Stripe    │
       │     ├─→ Redsys    │
       │     ├─→ Efectivo  │
       │     └─→ Other     │
       │                   │
       │ Totals (denorm):  │
       │ ├─→ total_base    │
       │ ├─→ total_tax     │
       │ ├─→ total_discount│
       │ └─→ total_amount  │
       │                   │
       │ invoice_number    │◄─── Facturación
       └───────────────────┘

FLUJOS ALTERNATIVOS:
───────────────────
💳 PAGO ONLINE (Stripe):
   Order → OrderPayment(Stripe)
        → Verificar en Webhook
        → Marcar como PAID

🔐 PAGO REDSYS (TPV Banco):
   Order → Redirigir a Redsys authorize
        → Usuario completa pago
        → Webhook notifica resultado
        → OrderPayment + Order.status = PAID

💵 EFECTIVO:
   Order → CashSession
        → OrderPayment(method=Efectivo)
        → Incluir en total_cash_sales
```

---

## 📧 MARKETING & COMUNICACIÓN

```
┌──────────────────────────────────────────┐
│    SISTEMA DE MARKETING & EMAIL          │
└──────────────────────────────────────────┘

    ┌─────────────────────────────┐
    │   MarketingSettings (OneToOne)
    │   ──────────────────────     │
    │                             │
    │   SMTP CONFIG:              │
    │   ├─→ smtp_host             │
    │   ├─→ smtp_port: 587        │
    │   ├─→ smtp_username         │
    │   ├─→ smtp_password         │
    │   ├─→ smtp_use_tls: True    │
    │   │                          │
    │   DEFAULT SENDER:           │
    │   ├─→ default_sender_email  │
    │   ├─→ default_sender_name   │
    │   │                          │
    │   BRANDING:                 │
    │   ├─→ header_logo           │
    │   └─→ footer_text (HTML)    │
    └──────────┬──────────────────┘
               │
        ┌──────▼────────────┐
        │  EmailTemplate    │
        │  (Plantilla Email)│
        │                   │
        │ content_json      │◄─── GrapesJS format
        │ content_html      │◄─── Compiled HTML
        │ thumbnail         │
        │                   │
        │ Drag & Drop       │
        │ Editor Visual     │
        └──────────┬────────┘
                   │
        ┌──────────▼──────────┐
        │  Campaign           │
        │  (Campaña Email)    │
        │                     │
        │ CONFIGURABLE:       │
        │ ├─→ name            │
        │ ├─→ subject         │
        │ ├─→ template        │
        │ │                   │
        │ AUDIENCE:           │
        │ ├─→ ALL_ACTIVE      │
        │ ├─→ ALL_CLIENTS     │
        │ ├─→ INACTIVE        │
        │ ├─→ STAFF           │
        │ └─→ CUSTOM_TAG      │
        │ │                   │
        │ TIMING:             │
        │ ├─→ scheduled_at    │
        │ └─→ status: DRAFT   │
        │                     │
        │ TRACKING:           │
        │ ├─→ sent_count      │
        │ ├─→ open_count      │
        │ └─→ click_count     │
        └─────────────────────┘

    TAMBIÉN:
    ────────
    ┌─────────────┐      ┌────────────┐
    │   Lead      │      │   Popup    │
    │   Pipeline  │      │  In-app    │
    │             │      │            │
    │ Kanban view │      │ target:    │
    │ Stages      │      │ CLIENTS    │
    │ (Leads app) │      │ STAFF      │
    │             │      │ ALL        │
    └─────────────┘      └────────────┘
```

---

## 📊 REPORTERÍA (VACÍA - FUTURA)

```
┌─────────────────────────────────────┐
│    REPORTING (En Construcción)      │
│    app/reporting/                   │
└─────────────────────────────────────┘

MODELOS: (Vacíos)

PROPUESTAS DE REPORTES:
──────────────────────
📈 Dashboard Financiero
   ├─→ Ingresos vs Gastos (Mensual)
   ├─→ Top Productos (Vendidos)
   ├─→ Top Clientes (Por Gasto)
   ├─→ Revenue Breakdown (Product/Service/Membership)
   └─→ Cash Discrepancies

📊 Membresías & Retención
   ├─→ Active Members (Trending)
   ├─→ Churn Rate
   ├─→ Revenue por Tipo de Plan
   └─→ Lifetime Value

👥 Staff Performance
   ├─→ Comisiones (Por Empleado)
   ├─→ Clases Impartidas
   ├─→ No-Shows / Cancelaciones
   └─→ Incentivos Otorgados

📅 Actividades
   ├─→ Ocupación (Attendance Rate)
   ├─→ No-Shows
   ├─→ Cancelaciones
   └─→ Revenue por Actividad

🏆 KPIs Principales
   ├─→ MRR (Monthly Recurring Revenue)
   ├─→ NRR (Net Revenue Retention)
   ├─→ CAC (Customer Acquisition Cost)
   ├─→ LTV (Lifetime Value)
   └─→ Churn Rate
```

---

## 🔐 VALIDACIONES & INTEGRACIONES

```
PUNTOS DE VALIDACIÓN:
────────────────────

✅ Stripe Integration:
   └─→ finance.stripe_utils.validate_keys()
       ├─→ Valida public_key
       ├─→ Valida secret_key
       └─→ Usa stripe.Account.retrieve()

✅ Redsys Integration:
   └─→ finance.redsys_utils.validate_redsys()
       ├─→ Valida merchant_code
       ├─→ Valida secret_key
       └─→ Genera firma correcta

✅ SMTP Integration:
   └─→ Testeable con Django send_mail()

✅ Inventario:
   └─→ Product.stock_quantity >= low_stock_threshold
       → Alertas en admin

✅ Horarios de Clases:
   └─→ Validar no solapamiento
   └─→ Validar dentro de horarios gym (falta)

✅ Disponibilidad de Salas:
   └─→ Room.activity_sessions no solapadas
```

---

## 🎪 ESTADO ACTUAL VS. IDEAL

```
ESTADO ACTUAL (92% completo):
═════════════════════════════

✅ Estructura base de apps: Excelente
✅ Modelos: Completos y bien diseñados
✅ Settings centralizados: Bien organizados
✅ Autenticación: Multi-gym implementada
✅ Integraciones: Stripe, Redsys, SMTP
✅ Catálogo: Products, Services, Activities, Memberships
✅ Ventas: Orders polimórficas, payments, invoices
✅ Personal: Staff, Salaries, Incentives (UI falta)
✅ Marketing: SMTP, Templates, Campaigns, Leads

❌ FALTA (8%):
━━━━━━━━━━━━
❌ Horarios de Apertura (Gym)
❌ UI para Incentivos (Staff)
❌ Apps huérfanas (cleanup)
❌ Reportería (en roadmap)

IDEAL (100%):
═════════════

✅ Todo lo anterior +
✅ Horarios de Apertura implementados
✅ Vistas de Incentivos completas
✅ Apps huérfanas documentadas/integradas
✅ Reportería básica (MRR, Churn, KPIs)
✅ Dashboard de validación de integraciones
✅ Importar/Exportar configuración
```

---

