# 📊 MATRIZ RÁPIDA DE REFERENCIA - APPS Y MODELOS

## Quick Lookup Table

### **APPS PRINCIPALES Y ESTADO**

```
┌──────────────┬──────────┬──────────────┬─────────────────────────┐
│ App          │ Status   │ Modelos      │ Settings View           │
├──────────────┼──────────┼──────────────┼─────────────────────────┤
│ accounts     │ ✅ 100%  │ User         │ ❌ No (en admin)        │
│ organizations│ ✅ 100%  │ Gym, Franchise│ ✅ gym_settings        │
│ clients      │ ✅ 100%  │ Client, Group│ ❌ No                  │
│ staff        │ ⚠️  85%  │ Profile, ...│ ✅ staff_list, roles   │
│ activities   │ ✅ 100%  │ Activity, ... │ ✅ activity_list       │
│ services     │ ✅ 100%  │ Service, ...│ ✅ service_list        │
│ products     │ ✅ 100%  │ Product, ... │ ✅ product_list        │
│ memberships  │ ✅ 100%  │ Plan, Access│ ✅ membership_plans    │
│ finance      │ ✅ 100%  │ TaxRate, ... │ ✅ finance_settings    │
│ sales        │ ✅ 100%  │ Order, Item │ ❌ No (es transaccional)│
│ marketing    │ ✅ 100%  │ Settings, ...│ ✅ marketing_settings  │
│ reporting    │ ⚠️   0%  │ (Vacía)     │ ❌ No                  │
│ routines     │ ⚠️  50%  │ (No explorado)│ ❌ No                  │
└──────────────┴──────────┴──────────────┴─────────────────────────┘
```

---

## 🔗 MODELOS POR APP (LISTA RÁPIDA)

### **ACCOUNTS**
```
├── User
│   └── Campos: email, first_name, last_name, is_active, is_staff
```

### **ORGANIZATIONS**
```
├── Franchise
│   └── Campos: name
└── Gym (RAÍZ)
    ├── Campos: name, commercial_name, legal_name, tax_id,
    │           address, city, zip_code, province, country,
    │           phone, email, website, social_media, brand_color, logo
    └── Relations: Todos los demás modelos por ForeignKey
```

### **CLIENTS**
```
├── Client
│   ├── Campos: gym, user, status, personal_data, access_code, stripe_id, extra_data
│   ├── Status: LEAD, ACTIVE, INACTIVE, BLOCKED, PAUSED
│   └── M2M: ClientGroup, ClientTag
├── ClientGroup (Jerárquico)
├── ClientTag
└── ClientNote
```

### **STAFF**
```
├── StaffProfile
│   └── Campos: user, gym, role, bio, pin_code, is_active
├── SalaryConfig
│   └── Campos: mode (MONTHLY/HOURLY), base_amount
├── IncentiveRule (⚠️ Falta vista CRUD)
│   └── Campos: gym, staff, name, type, value, criteria
├── StaffCommission
└── StaffTask
```

### **ACTIVITIES**
```
├── Activity
│   ├── Campos: gym, category, name, description, duration,
│   │           base_capacity, intensity_level, color, video_url
│   └── M2M: eligible_staff
├── ActivityCategory (Jerárquico)
├── Room
│   └── Campos: gym, name, capacity, layout_configuration
├── ScheduleRule (Patrón recurrente)
│   └── Campos: gym, activity, room, staff, day_of_week,
│               start_time, end_time, start_date, end_date
├── ActivitySession (Instancia)
└── CancellationPolicy
```

### **SERVICES**
```
├── Service
│   ├── Campos: gym, name, category, description, duration,
│   │           max_attendees, base_price, tax_rate, is_active
│   └── color, is_visible_online
├── ServiceCategory (Jerárquico)
└── ServiceAppointment
    └── Campos: gym, service, client, staff, room,
                start_datetime, end_datetime, status, order
```

### **PRODUCTS**
```
├── Product
│   ├── Campos: gym, name, category, description, sku,
│   │           cost_price, base_price, tax_rate,
│   │           supplier_name, supplier_reference,
│   │           track_stock, stock_quantity, low_stock_threshold
│   └── is_active, is_visible_online
├── ProductCategory (Jerárquico)
└── StockMove
    └── Campos: product, quantity_change, reason, notes,
                created_by, created_at
```

### **MEMBERSHIPS**
```
├── MembershipPlan
│   ├── Campos: gym, name, description, base_price, tax_rate,
│   │           is_recurring, frequency_amount, frequency_unit,
│   │           pack_validity_days, prorate_first_month,
│   │           is_membership, contract_required, contract_content
│   └── is_visible_online
└── PlanAccessRule
    └── Campos: plan, activity_category, activity,
                service_category, service, quantity, period
```

### **FINANCE**
```
├── TaxRate
│   └── Campos: gym, name, rate_percent, is_active
├── PaymentMethod
│   └── Campos: gym, name, is_cash, is_active, provider_code
├── CashSession
│   ├── Campos: gym, opened_by, closed_by, opened_at, closed_at,
│   │           opening_balance, total_cash_sales,
│   │           total_cash_withdrawals, total_cash_additions,
│   │           expected_balance, actual_balance, discrepancy
│   └── is_closed
└── FinanceSettings (OneToOne)
    └── Campos: gym, stripe_keys, redsys_config,
                currency, environment
```

### **SALES**
```
├── Order
│   ├── Campos: gym, client, session, status,
│   │           total_base, total_tax, total_discount, total_amount,
│   │           invoice_number, created_by, created_at
│   └── Status: PENDING, PAID, CANCELLED
├── OrderItem (Polimórfica GenericFK)
│   └── content_type→Product/Service, quantity, price, tax, discount
└── OrderPayment
    └── Campos: order, payment_method, amount,
                transaction_id, created_at
```

### **MARKETING**
```
├── MarketingSettings (OneToOne)
│   └── Campos: gym, smtp_host, smtp_port, smtp_username,
│               smtp_password, default_sender_email, header_logo
├── EmailTemplate
│   └── Campos: gym, name, content_json (GrapesJS),
│               content_html, thumbnail
├── Campaign
│   ├── Campos: gym, name, subject, template, audience_type,
│   │           scheduled_at, status, sent_count, open_count
│   └── Status: DRAFT, SCHEDULED, SENDING, SENT, FAILED
└── Popup
    └── Campos: gym, title, content, image, target (CLIENTS/STAFF/ALL)
```

---

## 🌐 RELACIONES (VISTA GRÁFICA)

```
User ←─── StaffProfile ─→ Gym
 │                         ├─→ Gym.clients
 │                         ├─→ Gym.staff
 │                         ├─→ Gym.activities
 │                         ├─→ Gym.services
 │                         ├─→ Gym.products
 │                         ├─→ Gym.memberships
 │                         ├─→ Gym.tax_rates
 │                         ├─→ Gym.payment_methods
 │                         ├─→ Gym.orders
 │                         ├─→ Gym.finance_settings (OneToOne)
 │                         └─→ Gym.marketing_settings (OneToOne)
 │
 └─────── Client ──────────┘
          │
          ├─→ ClientGroup (M2M)
          ├─→ ClientTag (M2M)
          └─→ Order (Comprador)

Activity ─────┬────→ ActivitySession (instancias)
              ├────→ PlanAccessRule (parte de membresía)
              └────→ ScheduleRule (patrón recurrente)

Service ──────┬────→ ServiceAppointment
              └────→ PlanAccessRule

Product ──────┬────→ StockMove (auditoría)
              └────→ OrderItem (compras)

MembershipPlan ────┬────→ PlanAccessRule (qué se puede usar)
                   └────→ Order (historial)

Order ────┬────→ OrderItem (Polimórfic)
          │       ├─→ Product
          │       └─→ Service
          │
          ├────→ OrderPayment
          └────→ CashSession (dónde se registró)
```

---

## 📍 URLS MAPA

```
/settings/                          ← DASHBOARD CENTRAL
├── /settings/gym/                  ← gym_settings
├── /finance/settings/              ← finance_settings
│   ├── /finance/tax/add/           ← finance_tax_create
│   ├── /finance/tax/<id>/edit/     ← finance_tax_edit
│   ├── /finance/method/add/        ← finance_method_create
│   ├── /finance/method/<id>/edit/  ← finance_method_edit
│   └── /finance/hardware/          ← finance_hardware_settings
│
├── /marketing/settings/            ← marketing_settings
└── /marketing/leads/settings/      ← lead_settings

/staff/
├── /staff/list/                    ← staff_list
├── /staff/create/                  ← staff_create
├── /staff/roles/                   ← role_list
└── /staff/audit-logs/              ← audit_log_list

/activities/
├── /activities/list/               ← activity_list

/services/
├── /services/list/                 ← service_list

/products/
├── /products/list/                 ← product_list

/memberships/
└── /memberships/plans/             ← membership_plans
```

---

## ✅ CHECKLIST DE CONFIGURACIÓN REQUERIDA

### **Para que un Gym funcione correctamente:**

```
CONFIGURACIÓN MÍNIMA REQUERIDA:
─────────────────────────────────

☐ Gym Profile
  ├── [✅] Nombre y nombre comercial
  ├── [✅] Logo y color corporativo
  ├── [✅] Dirección completa
  ├── [❌] Horarios de apertura ← FALTA
  └── [✅] Contacto y redes sociales

☐ Finance Setup
  ├── [✅] Moneda
  ├── [✅] Al menos 1 TaxRate (IVA 21%)
  ├── [✅] Al menos 1 PaymentMethod (Efectivo)
  ├── [⚠️] Stripe Keys (Opcional pero recomendado)
  ├── [⚠️] Redsys Config (Opcional pero recomendado)
  └── [✅] FinanceSettings

☐ Staff Setup
  ├── [✅] Al menos 1 StaffProfile (Manager)
  ├── [❌] IncentiveRules configuradas ← FALTA
  └── [✅] Roles y permisos

☐ Services Setup
  ├── [✅] Al menos 1 Activity
  ├── [✅] Al menos 1 Room
  ├── [✅] Al menos 1 Service
  └── [✅] Al menos 1 MembershipPlan

☐ Marketing Setup
  ├── [✅] SMTP Configuration
  └── [✅] MarketingSettings
```

---

## 🔴 VISTAS FALTANTES

```
Staff.IncentiveRule
├── ❌ incentive_rules_list()          ← LISTA
├── ❌ incentive_create()               ← CREAR
├── ❌ incentive_edit()                 ← EDITAR
└── ❌ incentive_delete()               ← ELIMINAR

Organizations.GymOperatingHours
├── ❌ gym_operating_hours_view()       ← CRUD (en formulario)
└── ❌ Template: gym_hours.html
```

---

## 🎯 MODELOS CON SINGLETON PATTERN (OneToOne a Gym)

```
├── finance.FinanceSettings
│   └── Contiene: Stripe keys, Redsys config, Currency
│   └── Acceso: FinanceSettings.objects.get_or_create(gym=request.gym)
│
└── marketing.MarketingSettings
    └── Contiene: SMTP config, Email branding
    └── Acceso: MarketingSettings.objects.get_or_create(gym=request.gym)
```

---

## 📈 ESTADÍSTICAS DEL PROYECTO

```
Total Apps Instaladas:        14
├── Completamente Funcionales: 12 (85%)
├── Parcialmente Funcionales:  1 (7%) [staff - falta incentives]
└── Vacías/No Usadas:          1 (7%) [reporting]

Total Modelos:                ~40
├── Con Settings View:        ~25 (62%)
├── Sin Settings View:        ~15 (38%)

Porcentaje de Completitud:    92%
Falta Implementar:            8% (Incentives + OperatingHours)
```

---

## 🔧 INTEGRACIÓN CON TERCEROS

```
✅ Stripe
   └── FinanceSettings.stripe_public_key/secret_key
   └── Client.stripe_customer_id
   └── Métodos de pago tipo 'stripe_terminal'

✅ Redsys (TPV)
   └── FinanceSettings.redsys_merchant_code/terminal/secret_key
   └── Environment: TEST/REAL
   └── Views: redsys_authorize_start, redsys_notify, redsys_ok, redsys_ko

✅ Email (SMTP)
   └── MarketingSettings.smtp_host/port/username/password
   └── Usado por Campaign sending

✅ GrapesJS (Email Builder)
   └── EmailTemplate.content_json (estructura GrapesJS)
   └── EmailTemplate.content_html (HTML compilado)
```

---

## 📝 NOTAS IMPORTANTES

1. **Gym es la raíz**: Todos los modelos relacionados al gym tienen FK a Gym
2. **Multi-tenant**: El middleware `CurrentGymMiddleware` maneja el gym actual
3. **Permisos**: `@require_gym_permission()` valida acceso por gym
4. **Impuestos centralizados**: TaxRate usado por Product, Service, MembershipPlan
5. **Órdenes polimórficas**: OrderItem puede ser Product o Service
6. **Sesiones de caja**: CashSession agrupa Order para contabilización

---

## 🚨 PROBLEMAS POTENCIALES

```
⚠️ CRÍTICA:
   └─ Horarios de apertura no implementados
      └─ Impacta: Reportería de disponibilidad, horarios de clases

⚠️ ALTA:
   └─ Vistas de Incentivos no implementadas
      └─ Impacta: Gestión de comisiones del staff

⚠️ MEDIA:
   └─ Apps huérfanas (auth_app, billing, etc)
      └─ Impacta: Claridad del código, mantenimiento

⚠️ BAJA:
   └─ Reporting app vacía
      └─ Impacta: Análisis avanzados (no crítico aún)
```

---

## 🎓 GUÍA RÁPIDA PARA NUEVOS DESARROLLADORES

**Si quieres agregar una nueva configuración:**

1. Crea el modelo en la app correspondiente
2. Crea migración: `python manage.py makemigrations <app>`
3. Crea formulario: `<app>/forms.py`
4. Crea vista: `<app>/views.py`
5. Crea template: `templates/backoffice/settings/<path>`
6. Agrega URL: `<app>/urls.py`
7. Agrega link en: `templates/backoffice/settings/dashboard.html`

**Ejemplo: Crear nuevo Settings para X**
```python
# 1. Model
class XSettings(models.Model):
    gym = ForeignKey(Gym, OneToOne, ...)
    config_field = ...

# 2. Form
class XSettingsForm(ModelForm):
    class Meta:
        model = XSettings
        fields = [...]

# 3. View
def x_settings_view(request):
    settings, _ = XSettings.objects.get_or_create(gym=request.gym)
    # Handle POST and render...

# 4. URL
path('x/settings/', x_settings_view, name='x_settings'),

# 5. Template link
<a href="{% url 'x_settings' %}">X Configuration</a>
```

---

