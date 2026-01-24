# Análisis Completo de Estructura Django - CRM Gimnasios

## Fecha: Enero 13, 2026
---

## 📊 1. APPS DJANGO ENCONTRADAS

### **Listado de Apps Instaladas (config/settings.py)**

```python
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Third-party
    "django_celery_beat",
    "django_celery_results",
    
    # Project apps
    "accounts",
    "organizations",
    "backoffice",
    "clients",
    "staff",
    "activities",
    "services",
    "products",
    "memberships",
    "finance",
    "sales",
    "reporting",
    "marketing",
    "routines",
]
```

### **Apps Adicionales Detectadas (no en INSTALLED_APPS)**

- `auth_app/` - App aparentemente no utilizada/en construcción
- `billing/` - Contiene migraciones pero no instalada
- `bonuses/` - Contiene migraciones pero no instalada
- `catalog/` - Contiene migraciones pero no instalada
- `core/` - Contiene migraciones pero no instalada
- `gyms/` - Contiene migraciones pero no instalada
- `plans/` - Sin estructura de app formal
- `reports/` - Sin estructura de app formal
- `saas/` - Sin estructura de app formal
- `saas_payments/` - Sin estructura de app formal
- `scheduler/` - Sin estructura de app formal
- `subscriptions/` - Sin estructura de app formal

---

## 🏗️ 2. ESTRUCTURA DE APPS PRINCIPALES

### **ACCOUNTS** (Sistema de Usuarios)
**Ruta:** `accounts/`

#### Modelos Principales:
| Modelo | Campos Clave | Descripción |
|--------|--------------|-------------|
| **User** | email, first_name, last_name, is_active, is_staff, created_at | Usuario personalizado basado en email (no en username) |

#### Características:
- Usuario personalizado (AbstractBaseUser + PermissionsMixin)
- Autenticación por email
- Sistema de permisos Django
- Middleware personalizado: `CurrentGymMiddleware`

#### Decoradores & Services:
- `@require_gym_permission()` - Control de acceso por gym
- `accounts.services.user_gym_ids()` - Obtener gyms del usuario
- `accounts.context_processors.gym_permissions()` - Inyectar permisos en contexto

#### Vistas de Configuración:
- ❌ No tiene vistas de configuración propias

---

### **ORGANIZATIONS** (Estructura Empresarial)
**Ruta:** `organizations/`

#### Modelos Principales:
| Modelo | Campos Clave | Descripción |
|--------|--------------|-------------|
| **Franchise** | name | Franquicia (padre empresarial) |
| **Gym** | name, commercial_name, legal_name, tax_id, address, city, zip_code, province, country, phone, email, website, instagram, facebook, tiktok, youtube, franchise, is_active, logo, brand_color | Centro de gimnasia individual |

#### Características:
- Datos completos de contacto y ubicación
- Identidad visual (logo, color corporativo)
- Redes sociales integradas
- Datos fiscales para facturación

#### Vistas de Configuración:
- ✅ `gym_settings_view()` - Editar configuración del gym
- Template: `backoffice/settings/gym.html`
- URL: `gym_settings`

---

### **CLIENTS** (Gestión de Clientes)
**Ruta:** `clients/`

#### Modelos Principales:
| Modelo | Campos Clave | Descripción |
|--------|--------------|-------------|
| **Client** | gym, user (FK User), status, first_name, last_name, email, phone_number, dni, birth_date, gender, address, photo, access_code, stripe_customer_id, extra_data | Cliente/Socio del gimnasio |
| **ClientGroup** | gym, name, parent | Agrupación jerárquica de clientes (ej: Mañanas, Empresas) |
| **ClientTag** | gym, name, color | Etiquetas rápidas (VIP, Moroso, Lesionado) |
| **ClientNote** | (parcialmente legible) | Notas sobre clientes |

#### Estados de Cliente:
- LEAD, ACTIVE, INACTIVE, BLOCKED, PAUSED

#### Características:
- Vinculación opcional a usuario real
- Código de acceso simplificado
- Integración con Stripe (customer_id)
- Datos flexibles (extra_data JSON)

#### Vistas de Configuración:
- ❌ No tiene vistas de configuración propias (pero sí de gestión)

---

### **STAFF** (Gestión de Empleados)
**Ruta:** `staff/`

#### Modelos Principales:
| Modelo | Campos Clave | Descripción |
|--------|--------------|-------------|
| **StaffProfile** | user (FK User), gym, role, bio, color, photo, pin_code, is_active | Perfil de empleado |
| **SalaryConfig** | staff (OneToOne), mode (MONTHLY/HOURLY), base_amount | Configuración de salario |
| **IncentiveRule** | gym, staff, name, type, value, criteria, is_active | Regla de comisiones/incentivos |
| **StaffCommission** | staff, rule, concept, amount, date | Registro de comisiones ganadas |
| **StaffTask** | gym, staff, status | Tareas asignadas a empleados |

#### Roles Disponibles:
- MANAGER, TRAINER, RECEPTIONIST, CLEANER, OTHER

#### Tipos de Incentivos:
- SALE_PCT, SALE_FIXED, CLASS_FIXED, CLASS_ATTENDANCE, TASK_FIXED

#### Vistas de Configuración:
- ✅ `staff_list()` - Listado y gestión de staff
- ✅ `role_list()` - Listado de roles y permisos
- ✅ `role_edit()` - Editar roles
- ✅ `audit_log_list()` - Logs de auditoría
- Templates:
  - `backoffice/settings/staff/role_list.html`
  - `backoffice/settings/staff/role_edit.html`
  - `backoffice/settings/system/audit_logs.html`

---

### **ACTIVITIES** (Actividades Grupales)
**Ruta:** `activities/`

#### Modelos Principales:
| Modelo | Campos Clave | Descripción |
|--------|--------------|-------------|
| **Activity** | gym, category, name, description, image, color, duration, base_capacity, intensity_level, video_url, eligible_staff, cancellation_policy | Actividad grupal (clase de yoga, etc) |
| **ActivityCategory** | gym, name, parent, icon | Categorización jerárquica |
| **Room** | gym, name, capacity, layout_configuration | Salas del centro |
| **ScheduleRule** | gym, activity, room, staff, day_of_week, start_time, end_time, start_date, end_date | Patrón recurrente de clases |
| **ActivitySession** | (parcialmente legible) | Instancia específica de una clase |
| **CancellationPolicy** | gym, name, window_hours, penalty_type, fee_amount | Política de cancelación |

#### Características:
- Colores para calendario
- Niveles de intensidad
- Personal cualificado asignado
- Políticas de cancelación configurables

#### Vistas de Configuración:
- ✅ `activity_list` - Gestión de actividades
- Template: `backoffice/settings/activities/`

---

### **SERVICES** (Servicios 1-on-1)
**Ruta:** `services/`

#### Modelos Principales:
| Modelo | Campos Clave | Descripción |
|--------|--------------|-------------|
| **Service** | gym, name, category, description, image, color, duration, max_attendees, default_room, base_price, tax_rate, price_strategy, is_active, is_visible_online | Servicio individual (ej: sesión personal) |
| **ServiceCategory** | gym, name, parent, icon | Categorización jerárquica |
| **ServiceAppointment** | gym, service, client, staff, room, start_datetime, end_datetime, status, notes, order | Reserva de servicio |

#### Estados de Cita:
- CONFIRMED, PENDING, CANCELLED, COMPLETED, NOSHOW

#### Características:
- Precios con impuestos
- Disponibilidad online
- Tracking de asistentes
- Vinculación con órdenes de venta

#### Vistas de Configuración:
- ✅ `service_list` - Gestión de servicios
- Template: `backoffice/settings/services/`

---

### **PRODUCTS** (Inventario)
**Ruta:** `products/`

#### Modelos Principales:
| Modelo | Campos Clave | Descripción |
|--------|--------------|-------------|
| **Product** | gym, name, category, description, image, sku, cost_price, base_price, tax_rate, price_strategy, supplier_name, supplier_reference, track_stock, stock_quantity, low_stock_threshold, is_active, is_visible_online | Producto físico |
| **ProductCategory** | gym, name, parent, icon | Categorización jerárquica |
| **StockMove** | product, quantity_change, reason, notes, created_by, created_at | Movimiento de inventario |

#### Razones de Stock:
- SALE, RESTOCK, ADJUSTMENT, LOSS, RETURN

#### Características:
- Control de inventario
- Alertas de stock bajo
- Historial de movimientos
- Precio de compra vs venta

#### Vistas de Configuración:
- ✅ `product_list` - Gestión de productos
- Template: `backoffice/settings/products/`

---

### **MEMBERSHIPS** (Planes y Cuotas)
**Ruta:** `memberships/`

#### Modelos Principales:
| Modelo | Campos Clave | Descripción |
|--------|--------------|-------------|
| **MembershipPlan** | gym, name, description, image, base_price, tax_rate, price_strategy, is_recurring, frequency_amount, frequency_unit, pack_validity_days, prorate_first_month, is_active, is_visible_online, is_membership, contract_required, contract_content | Plan de membresía |
| **PlanAccessRule** | plan, activity_category, activity, service_category, service, quantity, period | Acceso a actividades/servicios |

#### Unidades de Frecuencia:
- DAY, WEEK, MONTH, YEAR

#### Períodos de Acceso:
- TOTAL (bono único), PER_CYCLE (recurrente)

#### Características:
- Modelos flexibles (recurrentes o puntuales)
- Prorrateo de primer mes
- Contratos digitales configurables
- Acceso granular a actividades/servicios

#### Vistas de Configuración:
- ✅ `membership_plans` - Gestión de planes
- Template: `backoffice/settings/memberships/`

---

### **FINANCE** (Finanzas y Pagos)
**Ruta:** `finance/`

#### Modelos Principales:
| Modelo | Campos Clave | Descripción |
|--------|--------------|-------------|
| **TaxRate** | gym, name, rate_percent, is_active | Configuración de impuestos |
| **PaymentMethod** | gym, name, is_cash, is_active, provider_code | Método de pago |
| **CashSession** | gym, opened_by, closed_by, opened_at, closed_at, opening_balance, total_cash_sales, total_cash_withdrawals, total_cash_additions, expected_balance, actual_balance, discrepancy | Sesión de caja/arqueo |
| **FinanceSettings** | gym (OneToOne), stripe_public_key, stripe_secret_key, redsys_merchant_code, redsys_merchant_terminal, redsys_secret_key, redsys_environment, currency | Configuración de pago |

#### Características:
- Integración Stripe
- Integración Redsys (tarjetas)
- Control de caja física
- Detección de descuadres

#### Vistas de Configuración:
- ✅ `settings_view()` - Configuración financiera
- ✅ `tax_create()`, `tax_edit()`, `tax_delete()` - CRUD impuestos
- ✅ `method_create()`, `method_edit()`, `method_delete()` - CRUD métodos de pago
- ✅ `hardware_settings()` - Configuración de hardware
- ✅ `billing_dashboard()` - Reportes de facturación
- Template: `backoffice/finance/settings.html`

---

### **SALES** (Órdenes de Venta)
**Ruta:** `sales/`

#### Modelos Principales:
| Modelo | Campos Clave | Descripción |
|--------|--------------|-------------|
| **Order** | gym, client, session (FK CashSession), created_at, status, total_base, total_tax, total_discount, total_amount, internal_notes, invoice_number, created_by | Orden/Ticket de venta |
| **OrderItem** | order, content_type, object_id (GenericForeignKey), description, quantity, unit_price, tax_rate, discount_amount, subtotal | Línea de producto/servicio |
| **OrderPayment** | order, payment_method, amount, transaction_id, created_at | Pago registrado |

#### Características:
- Polimórfica (puede vender cualquier producto/servicio)
- Detalles denormalizados para queries rápidas
- Tracking de transacciones externas
- Estados: PENDING, PAID, CANCELLED

#### Vistas de Configuración:
- ❌ Gestión propia de órdenes (no en settings)

---

### **MARKETING** (Email, Leads, Campañas)
**Ruta:** `marketing/`

#### Modelos Principales:
| Modelo | Campos Clave | Descripción |
|--------|--------------|-------------|
| **MarketingSettings** | gym (OneToOne), smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_tls, default_sender_email, default_sender_name, header_logo, footer_text | Configuración SMTP |
| **EmailTemplate** | gym, name, description, content_json, content_html, thumbnail | Plantilla de email |
| **Campaign** | gym, name, subject, template, audience_type, audience_filter_value, scheduled_at, status, sent_count, open_count | Campaña de email |
| **Popup** | gym, title, content, image, target (CLIENTS/STAFF/ALL) | Popup in-app |

#### Estados de Campaña:
- DRAFT, SCHEDULED, SENDING, SENT, FAILED

#### Audience Types:
- ALL_ACTIVE, ALL_CLIENTS, INACTIVE, STAFF, CUSTOM_TAG

#### Características:
- Drag & Drop builder (GrapesJS JSON + HTML compilado)
- Segmentación por audiencia
- Tracking de aperturas

#### Vistas de Configuración:
- ✅ `marketing_settings_view()` - Configuración SMTP
- ✅ `lead_settings_view()` - Pipeline de leads
- Templates:
  - `backoffice/marketing/settings.html`
  - `backoffice/marketing/leads/settings.html`

---

### **ROUTINES** (Tareas Automáticas)
**Ruta:** `routines/`

#### Descripción:
App para gestionar tareas automáticas (Celery). Detalles no completamente explorados.

#### Vistas de Configuración:
- ❌ No identificadas aún

---

### **REPORTING** (Reportes y Análisis)
**Ruta:** `reporting/`

#### Descripción:
Modelos vacíos detectados. Aparentemente en construcción.

#### Vistas de Configuración:
- ❌ No identificadas

---

### **BACKOFFICE** (Panel Principal)
**Ruta:** `backoffice/`

#### Vistas Principales:
| Vista | URL | Descripción |
|--------|-----|-------------|
| `login_view()` | /login/ | Login con email/password |
| `logout_view()` | /logout/ | Cierre de sesión |
| `home()` | / | Dashboard principal con KPIs |
| `whoami()` | /whoami/ (JSON) | Información de usuario actual |
| `select_gym()` | /select-gym/ (POST) | Cambiar gym activo |
| `settings_dashboard()` | /settings/ | **HUB DE CONFIGURACIÓN CENTRAL** |
| `staff_page()` | /staff/ | Lista de staff |
| `marketing_page()` | /marketing/ | Dashboard de marketing |

#### Settings Dashboard:
El dashboard de settings central (`backoffice/views.py:settings_dashboard`) está implementado en:
- Template: `templates/backoffice/settings/dashboard.html`
- Estructura de 6 categorías principales (ver sección 3)

---

## ⚙️ 3. ESTRUCTURA ACTUAL DE SETTINGS

### **Dashboard Central de Configuración**
**URL:** `/settings/` (nombre: `settings_dashboard`)
**Template:** `templates/backoffice/settings/dashboard.html`

#### Categorías Organizadas:

### **1. EMPRESA (Datos Generales)**
```
├── Perfil del Centro → gym_settings
└── Horarios de Apertura → #
```
- **Vista:** `organizations.views.gym_settings_view()`
- **Template:** `backoffice/settings/gym.html`
- **Form:** `GymSettingsForm`

### **2. EQUIPO (Usuarios y Roles)**
```
├── Ver Usuarios → staff_list
├── Roles y Permisos → role_list
└── Configurar Incentivos → #
```
- **Vistas:**
  - `staff_list()` - Listado
  - `staff_create()` - Crear
  - `staff_edit()` - Editar
  - `staff_detail()` - Detalle
  - `role_list()` - Roles
  - `role_create()` - Crear rol
  - `role_edit()` - Editar rol
- **Templates:** `backoffice/settings/staff/`

### **3. SERVICIOS (Actividades, Cuotas, Productos)**
```
├── Servicios y Categorías → service_list
├── Actividades Grupales → activity_list
└── Planes de Membresía → membership_plans
```
- **Vistas:**
  - `service_list()` en services/views.py
  - `activity_list()` en activities/views.py
  - `membership_plans()` en memberships/views.py

### **4. FINANZAS (Pagos e Impuestos)**
```
└── Impuestos y Métodos de Pago → finance_settings
```
- **Vista:** `finance.views.settings_view()`
- **Template:** `backoffice/finance/settings.html`
- **Modelos:**
  - TaxRate (CRUD)
  - PaymentMethod (CRUD)
  - FinanceSettings (instancia única por gym)

**Vistas Secundarias en Finance:**
- `tax_create()` / `tax_edit()` / `tax_delete()`
- `method_create()` / `method_edit()` / `method_delete()`
- `hardware_settings()` - Configuración de TPV

### **5. MARKETING (Email, Leads, Campañas)**
```
├── Pipeline de Leads → lead_settings
└── Configuración Email (SMTP) → marketing_settings
```
- **Vistas:**
  - `marketing_settings_view()` - Configuración SMTP
  - `lead_settings_view()` - Pipeline y automatización
- **Templates:**
  - `backoffice/marketing/settings.html`
  - `backoffice/marketing/leads/settings.html`

### **6. SISTEMA (Integraciones y Avanzado)**
```
├── Logs de Auditoría → audit_log_list
└── Hardware TPV (Terminales) → finance_hardware_settings
```
- **Vistas:**
  - `audit_log_list()` en staff/views.py
  - `hardware_settings()` en finance/views.py

---

## 🔗 4. RELACIONES ENTRE APPS

### **Diagrama de Dependencias:**

```
organizations.Gym (CENTRO RAÍZ)
    ├── accounts.User (Usuarios del sistema)
    │   ├── staff.StaffProfile (Empleados)
    │   ├── clients.Client (Clientes con user opcional)
    │   └── sales.Order (Creadas por usuarios)
    │
    ├── clients.Client
    │   ├── clients.ClientGroup
    │   ├── clients.ClientTag
    │   ├── clients.ClientNote
    │   └── accounts.User (OneToOne opcional)
    │
    ├── staff.StaffProfile
    │   ├── staff.SalaryConfig (OneToOne)
    │   ├── staff.IncentiveRule
    │   ├── staff.StaffCommission
    │   ├── staff.StaffTask
    │   └── activities.ScheduleRule
    │
    ├── activities
    │   ├── activities.Activity
    │   │   ├── activities.ActivityCategory
    │   │   ├── activities.ScheduleRule (Clases recurrentes)
    │   │   ├── activities.ActivitySession (Instancias)
    │   │   ├── activities.CancellationPolicy
    │   │   └── staff.StaffProfile (eligible_staff M2M)
    │   │
    │   └── activities.Room (Salas)
    │
    ├── services
    │   ├── services.Service
    │   │   ├── services.ServiceCategory
    │   │   ├── services.ServiceAppointment
    │   │   └── finance.TaxRate
    │   │
    │   └── activities.Room (default_room)
    │
    ├── products
    │   ├── products.Product
    │   │   ├── products.ProductCategory
    │   │   ├── products.StockMove
    │   │   └── finance.TaxRate
    │   │
    │   └── products.StockMove
    │
    ├── memberships
    │   ├── memberships.MembershipPlan
    │   │   ├── memberships.PlanAccessRule
    │   │   ├── finance.TaxRate
    │   │   ├── activities.ActivityCategory
    │   │   ├── activities.Activity
    │   │   ├── services.ServiceCategory
    │   │   └── services.Service
    │   │
    │   └── memberships.PlanAccessRule
    │
    ├── finance
    │   ├── finance.TaxRate
    │   ├── finance.PaymentMethod
    │   ├── finance.CashSession
    │   │   └── accounts.User (opened_by, closed_by)
    │   │
    │   └── finance.FinanceSettings (OneToOne)
    │
    ├── sales
    │   ├── sales.Order
    │   │   ├── clients.Client (FK nullable)
    │   │   ├── finance.CashSession (FK nullable)
    │   │   ├── accounts.User (created_by)
    │   │   └── sales.OrderItem (M2O)
    │   │       ├── sales.OrderPayment
    │   │       ├── finance.PaymentMethod
    │   │       └── ContentType (polimórfica: Product/Service)
    │   │
    │   └── sales.OrderPayment
    │
    ├── marketing
    │   ├── marketing.MarketingSettings (OneToOne)
    │   ├── marketing.EmailTemplate
    │   ├── marketing.Campaign
    │   └── marketing.Popup
    │
    └── finance.TaxRate (Usado por Product, Service, MembershipPlan)
```

### **Relaciones Clave:**

| De | A | Tipo | Notas |
|----|---|------|-------|
| clients.Client | accounts.User | OneToOne | Opcional: cliente con login |
| staff.StaffProfile | accounts.User | OneToOne | Staff siempre vinculado a usuario |
| memberships.PlanAccessRule | activities/services | FK | Define acceso a recursos |
| sales.OrderItem | Product/Service | GenericFK | Polimórfica |
| finance.CashSession | sales.Order | 1-M | Agrupa ventas en una sesión |
| activities.ScheduleRule | activities.ActivitySession | Generator | Genera instancias de clases |

---

## 📋 5. VISTAS DE CONFIGURACIÓN EXISTENTES

### **Consolidación por Área:**

#### **EMPRESA**
- ✅ `organizations.gym_settings_view()` → `gym_settings`
- ❌ Horarios de apertura (NO IMPLEMENTADO)

#### **EQUIPO & PERMISOS**
- ✅ `staff.staff_list()` → `staff_list`
- ✅ `staff.staff_create()` → `staff_create`
- ✅ `staff.staff_edit()` → `staff_edit`
- ✅ `staff.role_list()` → `role_list`
- ✅ `staff.role_create()` → `role_create`
- ✅ `staff.role_edit()` → `role_edit`
- ✅ `staff.audit_log_list()` → `audit_log_list`
- ❌ Configurar incentivos (NO IMPLEMENTADO)

#### **SERVICIOS (Actividades, Planes, Productos)**
- ✅ `services.service_list()` → `service_list`
- ✅ `activities.activity_list()` → `activity_list`
- ✅ `memberships.membership_plans()` → `membership_plans`
- ✅ `products.product_list()` → `product_list`

#### **FINANZAS**
- ✅ `finance.settings_view()` → `finance_settings`
  - CRUD TaxRate
  - CRUD PaymentMethod
  - FinanceSettings form
- ✅ `finance.hardware_settings()` → `finance_hardware_settings`
- ✅ `finance.billing_dashboard()` → `finance_billing_dashboard`

#### **MARKETING**
- ✅ `marketing.marketing_settings_view()` → `marketing_settings`
- ✅ `marketing.lead_settings_view()` → `lead_settings`

#### **SISTEMA**
- ✅ `staff.audit_log_list()` → `audit_log_list`
- ✅ `finance.hardware_settings()` → `finance_hardware_settings`

---

## 📁 6. ESTRUCTURA DE TEMPLATES

### **Organización Actual:**
```
templates/backoffice/
├── settings/
│   ├── dashboard.html          ← HUB PRINCIPAL
│   ├── gym.html                ← Empresa
│   ├── staff/
│   │   ├── role_list.html
│   │   └── role_edit.html
│   ├── system/
│   │   └── audit_logs.html
│   └── [otros directorios de settings]
│
├── finance/
│   └── settings.html           ← Finance configuración
│
├── marketing/
│   ├── settings.html           ← Marketing SMTP
│   └── leads/
│       └── settings.html       ← Leads pipeline
│
└── [otros: activities/, clients/, staff/, etc.]
```

---

## 🎯 7. MODELOS CON CONFIGURACIÓN (SETTINGS)

Estos son modelos con patrón OneToOne o Singleton para Gym:

| Modelo | App | Patrón | Propósito |
|--------|-----|--------|----------|
| `FinanceSettings` | finance | OneToOne | Config de Stripe, Redsys, moneda |
| `MarketingSettings` | marketing | OneToOne | SMTP, email branding |
| `Gym` | organizations | Direct | Datos del centro (branding, ubicación) |

---

## 📊 8. ESTADO DE IMPLEMENTACIÓN DE SETTINGS

### **Completamente Implementados ✅**
1. **Gym Settings** - Datos del centro, branding, ubicación, redes sociales
2. **Finance Settings** - Impuestos, métodos de pago, Stripe/Redsys, hardware
3. **Marketing Settings** - SMTP, email branding
4. **Staff Management** - Roles, permisos, auditoría
5. **Service Management** - Servicios, categorías, pricing
6. **Activity Management** - Actividades, salas, horarios
7. **Membership Management** - Planes, acceso, pricing
8. **Product Management** - Inventario, stock, categorías

### **Parcialmente Implementados ⚠️**
1. **Lead Settings** - Pipeline visible, pero automatización limitada
2. **Incentives Configuration** - Modelos existen (IncentiveRule), pero vista NO implementada

### **No Implementados ❌**
1. **Horarios de Apertura** (Gym)
2. **Configurar Incentivos** (Staff) - Modelos existen, falta UI
3. **Reportes/Analytics** (Reporting app vacía)

---

## 💡 9. RECOMENDACIONES DE CONSOLIDACIÓN

### **Situación Actual:**
✅ El dashboard de settings central (`/settings/`) **ya existe** y está bien estructurado.

✅ Las vistas están distribuidas lógicamente por app.

### **Mejoras Sugeridas:**

#### **1. Unificación de URLs**
**Situación:** URLs dispersas
```
/finance/settings/        → finance_settings
/marketing/settings/      → marketing_settings
/staff/roles/            → role_list
/...                     → etc
```

**Propuesta:** Mantener estructura actual pero crear alias centralizados:
```python
# backoffice/urls.py
path("settings/", settings_dashboard, name="settings_dashboard"),
path("settings/gym/", gym_settings_view, name="gym_settings"),
path("settings/finance/", finance_settings_view, name="finance_settings"),
path("settings/marketing/", marketing_settings_view, name="marketing_settings"),
# etc - todos accesibles desde /settings/subcategoria/
```

#### **2. Crear un Settings Manager Service**
Crear `backoffice/settings_service.py` con métodos para:
- Obtener todas las configuraciones de un gym
- Validar integraciones (Stripe, Redsys, SMTP)
- Aplicar cambios masivos

```python
class SettingsManager:
    def __init__(self, gym):
        self.gym = gym
    
    def get_all_settings(self):
        return {
            'gym': GymSettings,
            'finance': FinanceSettings,
            'marketing': MarketingSettings,
        }
    
    def validate_integrations(self):
        # Validar Stripe, Redsys, SMTP
        pass
```

#### **3. Falta Implementar:**
- [ ] Vista de **Horarios de Apertura** (Gym)
- [ ] Vista de **Configuración de Incentivos** (Staff)
  - Ya existen modelos `IncentiveRule`, `StaffCommission`
  - Solo necesita formulario y CRUD en `staff/views.py`

#### **4. Apps Huérfanas**
Decidir qué hacer con:
- `auth_app/` - Aparentemente duplicado con accounts
- `billing/`, `bonuses/`, `catalog/`, `core/`, `gyms/`, `subscriptions/`

Opciones:
- [ ] Integrar funcionalidad en apps existentes
- [ ] Eliminar si no se usan
- [ ] Documentar para futura expansión

#### **5. Mejorar Validación**
Agregar validación de integraciones en settings views:
```python
def settings_view(request):
    # ...
    if request.POST:
        # Validar Stripe keys
        if form.stripe_public_key:
            try:
                validate_stripe_keys(form.stripe_public_key, form.stripe_secret_key)
            except StripeException as e:
                form.add_error('stripe_secret_key', str(e))
```

---

## 📝 10. CHECKLIST DE COMPLETITUD

### **Models:**
- [x] Accounts.User
- [x] Organizations (Franchise, Gym)
- [x] Clients (Client, Groups, Tags, Notes)
- [x] Staff (Profile, Salary, Incentives, Tasks)
- [x] Activities (Activity, Category, Room, Schedule, Session, Policy)
- [x] Services (Service, Category, Appointment)
- [x] Products (Product, Category, Stock)
- [x] Memberships (Plan, AccessRule)
- [x] Finance (TaxRate, PaymentMethod, CashSession, FinanceSettings)
- [x] Sales (Order, OrderItem, OrderPayment)
- [x] Marketing (Settings, Template, Campaign, Popup)
- [ ] Reporting (Vacío)
- [ ] Routines (No explorado)

### **Views (Settings):**
- [x] Gym Settings
- [x] Finance Settings (Tax, Methods, Hardware)
- [x] Marketing Settings (SMTP, Leads)
- [x] Staff Management (List, Roles, Audit)
- [x] Activity Management
- [x] Service Management
- [x] Membership Management
- [x] Product Management
- [ ] Incentives Configuration
- [ ] Operating Hours (Gym)

### **Dashboard Central:**
- [x] Dashboard de Settings (`/settings/`)
- [x] Estructura de 6 categorías
- [x] Links a todas las vistas (excepto las no implementadas)

---

## 🔚 CONCLUSIÓN

**El proyecto tiene una estructura de settings CENTRALIZADA y BIEN ORGANIZADA.**

El dashboard en `/settings/` actúa como hub central de configuración, con:
- ✅ Estructura clara en 6 categorías
- ✅ Vistas distribuidas lógicamente por app
- ✅ Modelos completos en todas las areas principales
- ⚠️ Algunas vistas faltantes (Horarios, Incentivos)
- ⚠️ Apps huérfanas que necesitan decisión

**Recomendación:** No requiere refactoring mayor, solo completar las vistas faltantes y limpiar apps no utilizadas.
