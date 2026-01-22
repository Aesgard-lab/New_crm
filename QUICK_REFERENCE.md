# 🗺️ MAPA RÁPIDO - DÓNDE ESTÁ TODO

## 📍 URLS Y ACCESO DIRECTO

### Horarios de Apertura
```
URL interna: {% url 'gym_opening_hours' %}
Ruta completa: /finance/opening-hours/
Acceso: Settings → Empresa → Horarios de Apertura
Descripción: Editor interactivo para horarios 7 días/semana
```

### Incentivos CRUD
```
Listar:     {% url 'incentive_list' %}          → /staff/incentives/
Crear:      {% url 'incentive_create' %}        → /staff/incentives/create/
Editar:     {% url 'incentive_edit' pk=1 %}   → /staff/incentives/1/edit/
Eliminar:   {% url 'incentive_delete' pk=1 %} → /staff/incentives/1/delete/

Acceso: Settings → Equipo → Configurar Incentivos
```

### Productos CRUD
```
Listar:     {% url 'product_list' %}          → /products/
Crear:      {% url 'product_create' %}        → /products/create/
Editar:     {% url 'product_edit' pk=1 %}   → /products/1/edit/

Categorías:
Listar:     {% url 'product_category_list' %} → /products/categories/
Crear:      {% url 'product_category_create' %} → /products/categories/create/
Editar:     {% url 'product_category_edit' pk=1 %} → /products/categories/1/edit/

Acceso: Settings → Servicios → Productos y Tienda
```

---

## 📁 ARCHIVOS CLAVE DONDE ESTÁ LA LÓGICA

### HORARIOS (finance/)
```
finance/
├── forms.py
│   └── GymOpeningHoursForm (60 líneas)
├── views.py
│   └── gym_opening_hours() (30 líneas)
├── urls.py
│   └── path('opening-hours/', views.gym_opening_hours, name='gym_opening_hours')
└── models.py
    └── Gym.opening_hours (JSONField) ← aquí se guarda

templates/backoffice/finance/
└── opening_hours.html (150 líneas)
```

### INCENTIVOS (staff/)
```
staff/
├── forms.py
│   └── IncentiveRuleForm (50 líneas)
├── views.py
│   ├── incentive_list() 
│   ├── incentive_create()
│   ├── incentive_edit()
│   └── incentive_delete()
├── urls.py
│   ├── path('incentives/', views.incentive_list, name='incentive_list')
│   ├── path('incentives/create/', views.incentive_create, name='incentive_create')
│   ├── path('incentives/<int:pk>/edit/', views.incentive_edit, name='incentive_edit')
│   └── path('incentives/<int:pk>/delete/', views.incentive_delete, name='incentive_delete')
└── models.py
    └── IncentiveRule (ya existe)

templates/backoffice/staff/
├── incentive_list.html (120 líneas)
├── incentive_form.html (130 líneas)
└── incentive_confirm_delete.html (50 líneas)
```

### PRODUCTOS (products/)
```
products/
├── forms.py
│   ├── ProductForm (ya existe)
│   └── ProductCategoryForm (ya existe)
├── views.py
│   ├── product_list()
│   ├── product_create()
│   ├── product_edit()
│   ├── category_list()
│   ├── category_create()
│   └── category_edit()
├── urls.py (ya registradas todas)
└── models.py
    ├── Product (ya completo)
    ├── ProductCategory (ya completo)
    └── StockMove (ya existe)

templates/backoffice/products/
├── list.html (ya existe)
├── form.html (ya existe)
├── tabs.html (ya existe)
└── categories/
    ├── list.html (ya existe)
    └── form.html (ya existe)
```

---

## 🔗 DASHBOARD ACTUALIZADO

```
templates/backoffice/settings/dashboard.html

Sección "EMPRESA"
├── Perfil del Centro → gym_settings
└── Horarios de Apertura → gym_opening_hours ✨ NUEVO

Sección "EQUIPO"
├── Ver Usuarios → staff_list
├── Roles y Permisos → role_list
└── Configurar Incentivos → incentive_list ✨ NUEVO

Sección "SERVICIOS & PRODUCTOS"
├── Servicios y Categorías → service_list
├── Actividades Grupales → activity_list
├── Planes de Membresía → membership_plans
└── Productos y Tienda → product_list ✨ NUEVO LINK (existía)
```

---

## 💾 BASE DE DATOS

### Nuevas Tablas
```
(Ninguna nueva, se usa IncentiveRule que ya existía)
```

### Campos Nuevos
```
Gym.opening_hours (JSONField) - Horarios almacenados como JSON
```

### JSON Structure
```json
{
  "monday": {
    "is_open": true,
    "open_time": "07:00",
    "close_time": "22:00"
  },
  "tuesday": {
    "is_open": true,
    "open_time": "07:00",
    "close_time": "22:00"
  },
  ...
}
```

---

## 🔐 PERMISOS REQUERIDOS

Todas las nuevas vistas usan decoradores:

```python
@login_required
@require_gym_permission('finance.view_finance')  # Horarios
@require_gym_permission('staff.view_incentiverule')  # Incentivos
@require_gym_permission('products.view_product')  # Productos
```

User necesita estar:
1. Logueado
2. Asignado al gym
3. Tener el permiso correspondiente

---

## 🧪 TESTING BÁSICO

Verificar que está todo OK:

```python
# En Django shell (python manage.py shell)

# Test 1: Horarios
from finance.forms import GymOpeningHoursForm
form = GymOpeningHoursForm()
# Debe mostrar 7 campos para días

# Test 2: Incentivos
from staff.forms import IncentiveRuleForm
from staff.models import IncentiveRule
IncentiveRule.objects.count()  # Debe retornar número

# Test 3: Productos
from products.models import Product
Product.objects.count()  # Debe listar existentes
```

---

## 📋 CHECKLIST DE VERIFICACIÓN

Después de deployar, verifica:

```
[ ] URL /finance/opening-hours/ carga sin errores
[ ] Puedo crear un incentivo y guardarlo
[ ] Puedo listar incentivos creados
[ ] Puedo editar un incentivo
[ ] Puedo eliminar un incentivo
[ ] Dashboard muestra 3 nuevos links
[ ] Productos carga y funciona
[ ] No hay errores en Django logs
```

---

## 🚀 DEPLOYMENT QUICK START

```bash
# 1. Estar en el venv
source .venv/Scripts/activate  # Windows
source .venv/bin/activate       # Linux/Mac

# 2. Verificar que no hay errores
python manage.py check

# 3. Si hay migraciones nuevas (debería no haber)
python manage.py makemigrations
python manage.py migrate

# 4. Runserver para probar
python manage.py runserver

# 5. Ir a Settings y probar las 3 nuevas features
```

---

## 💡 NOTAS IMPORTANTES

### Horarios
- Se guardan en JSONField de Gym
- Cada gym tiene sus propios horarios
- Sin límite de horarios especiales (puedes extender JSON si necesitas)

### Incentivos  
- Tabla: staff_incentiverule
- Cada gym filtra solo sus propias reglas
- Soporte para incentivos globales (staff=NULL) o por empleado

### Productos
- Ya existían modelos, solo completamos vistas/forms
- Stock tracking automático
- Soporta múltiples categorías
- Imágenes con upload automático

---

**Última actualización:** 13 Enero 2026  
**Versión:** 1.0 - Production Ready  
**Soporte:** Ver IMPLEMENTATION_COMPLETED.md para detalles
