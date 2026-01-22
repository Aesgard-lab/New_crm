# 🔧 PLAN DE CONSOLIDACIÓN DE CONFIGURACIONES

**Objetivo:** Centralizar TODAS las configuraciones en un único lugar intuitivo  
**Estado Actual:** 70% Ya consolidado en `/settings/`  
**Trabajo Restante:** 30% (6-8 horas)  

---

## 📍 ESTRUCTURA ACTUAL DE SETTINGS

```
/settings/
├── dashboard.html          ← HUB PRINCIPAL
├── form.html              ← Estilos compartidos
└── tabs.html              ← Navegación entre secciones
```

**Vista:** `backoffice.views.settings_dashboard`  
**URL:** `django_admin/urls.py → path('settings/', ...)`  
**Template:** `templates/backoffice/settings/dashboard.html`

---

## 🎯 CONFIGURACIONES ACTUALMENTE IMPLEMENTADAS

### ✅ EMPRESA (100%)
```
/settings/ → Perfil del Centro
  ├── Nombre del gym
  ├── Ubicación
  ├── Contacto
  ├── Branding (logo, color)
  └── ✅ Vista: gym_settings (finance/views.py)
```

### ✅ FINANZAS (100%)
```
/settings/ → Finanzas
  ├── Configuración General
  │   └── ✅ finance_settings (finance/views.py)
  ├── Métodos de Pago
  │   ├── ✅ method_list, method_create, method_edit
  │   └── Integración: Stripe + Redsys
  ├── Tasas Impositivas (IVA)
  │   ├── ✅ tax_list, tax_create, tax_edit
  │   └── Por categoría de producto
  └── Hardware POS
      └── ✅ hardware_settings (finance/views.py)
```

### ✅ EQUIPO (100%)
```
/settings/ → Equipo
  ├── Usuarios
  │   └── ✅ staff_list, staff_create (staff/views.py)
  └── Roles & Permisos
      └── ✅ role_list, role_edit (staff/views.py)
```

### ✅ SERVICIOS (100%)
```
/settings/ → Servicios
  ├── Servicios
  │   └── ✅ service_list, service_create (services/views.py)
  └── Categorías
      └── ✅ category_list, category_create (services/views.py)
```

### ✅ MEMBRESÍAS (95%)
```
/settings/ → Membresías
  ├── Planes
  │   └── ⚠️ membership_list (memberships/views.py)
  └── Configuración
      └── Necesita revisión
```

### ⚠️ EMPRESA - HORARIOS (0%)
```
/settings/ → Horarios de Apertura
  ├── Modelo existe: Gym.opening_hours (JSONField)
  ├── Falta: Interfaz para editar
  └── TODO: Crear vista + template

PROTOTIPO:
class GymOpeningHours(Form):
    monday_open = TimeField()
    monday_close = TimeField()
    tuesday_open = TimeField()
    ... (todos los días)
    
def gym_opening_hours(request):
    # GET: Mostrar formulario
    # POST: Guardar horarios en Gym.opening_hours JSON
```

### ⚠️ EQUIPO - INCENTIVOS (0%)
```
/settings/ → Configurar Incentivos
  ├── Modelo existe: Incentive
  ├── Campos:
  │   ├── staff (FK)
  │   ├── name (CharField)
  │   ├── type (CHOICES: percentage, fixed, target)
  │   ├── value (DecimalField)
  │   ├── condition (TextField - descripción)
  │   ├── valid_from (DateField)
  │   ├── valid_until (DateField)
  │   └── is_active (BooleanField)
  └── TODO: Crear vistas CRUD + templates

VISTAS NECESARIAS:
  - incentive_list()      → Listar incentivos por staff
  - incentive_create()    → Crear nuevo
  - incentive_edit()      → Editar existente
  - incentive_delete()    → Eliminar
```

### ⚠️ SERVICIOS - PRODUCTOS (60%)
```
/settings/ → Productos
  ├── Modelo: Product (INCOMPLETO)
  ├── Campos actuales:
  │   ├── name ✅
  │   ├── price ✅
  │   └── gym (FK) ✅
  ├── Campos necesarios:
  │   ├── description
  │   ├── category (FK)
  │   ├── sku
  │   ├── stock
  │   ├── tax_rate (FK)
  │   ├── is_active
  │   └── image
  └── TODO: Completar modelo + vistas CRUD
```

---

## 🏗️ ARQUITECTURA DE CONFIGURACIONES

### Por Tipo de Datos

#### 1. DATOS SIMPLES (String, Int, Bool)
```
Ubicación: Gym model
Ejemplos: Nombre, ubicación, teléfono
Guardado: Directamente en DB
Vista pattern:
  - GET: Form pre-populated
  - POST: Guardar y redirigir
  
Ejemplos en código:
  - finance/views.py → settings_view()
  - finance/views.py → gym_settings()
```

#### 2. DATOS COMPLEJOS (JSON)
```
Ubicación: Field JSONField en modelo
Ejemplos: Horarios (opening_hours), configuraciones
Guardado: JSON en DB
Vista pattern:
  - GET: Parsear JSON → Form
  - POST: Validar → JSON → Guardar
  
Implementar para:
  - opening_hours (Gym)
  - meta_settings (FinanceSettings)
```

#### 3. RELACIONES 1:N (Listados)
```
Ubicación: Modelos relacionados
Ejemplos: Métodos de pago, tasas, servicios
Guardado: Registros individuales
Vistas pattern:
  - _list(): Mostrar tabla + botones CRUD
  - _create(): Form + POST
  - _edit(): Form pre-filled
  - _delete(): Confirmación + DELETE
  
Ejemplos existentes:
  - finance/views.py → tax_create, tax_edit, tax_delete
  - services/views.py → service_list, service_create
```

#### 4. CONFIGURACIÓN AVANZADA
```
Ubicación: Modelos especiales
Ejemplos: Permisos, roles, cadenas de pago
Guardado: M2M relations + Fields
Vistas pattern:
  - Interfaz específica por tipo
  - Multi-step forms para complejas
  
Ejemplos:
  - staff/views.py → role_edit() (M2M permissions)
  - finance/views.py → hardware_settings()
```

---

## 📋 TABLA DE IMPLEMENTACIÓN

| Feature | Tipo | Modelo | Vista | Template | Estado | ETA |
|---------|------|--------|-------|----------|--------|-----|
| Perfil Gym | Simple | Gym | gym_settings | settings/gym.html | ✅ | - |
| Horarios | JSON | Gym | ⚠️ TODO | TODO | ⚠️ 0% | 2h |
| Usuarios | 1:N | User | staff_list | staff/list.html | ✅ | - |
| Roles | M2M | Role | role_edit | staff/role.html | ✅ | - |
| Incentivos | 1:N | Incentive | ⚠️ TODO | TODO | ⚠️ 0% | 2.5h |
| Servicios | 1:N | Service | service_list | services/list.html | ✅ | - |
| Productos | 1:N | Product | ⚠️ TODO | TODO | ⚠️ 60% | 3h |
| Met. Pago | 1:N | PaymentMethod | method_create | finance/method.html | ✅ | - |
| Tasas IVA | 1:N | TaxRate | tax_create | finance/tax.html | ✅ | - |
| Membresías | 1:N | Membership | membership_list | memberships/list.html | ⚠️ 95% | 1h |

---

## 🔄 FLUJO DE CONFIGURACIÓN

```
Usuario entra a /settings/
         ↓
Dashboard muestra 6 categorías
         ↓
Usuario hace clic en una sección
         ↓
¿Es simple?  ¿Es 1:N?  ¿Es JSON?  ¿Es M2M?
    ↓          ↓         ↓          ↓
  Form      Listado   Form      Interface
   ↓          ↓         ↓          ↓
 GET/POST   +CRUD    GET/POST   Complex
```

---

## 🚀 IMPLEMENTACIÓN PASO A PASO

### PASO 1: Horarios de Apertura (2 horas)

**1. Crear forma en finance/forms.py:**
```python
class GymOpeningHoursForm(forms.Form):
    DAYS = [
        ('monday', 'Lunes'),
        ('tuesday', 'Martes'),
        # ... etc
    ]
    
    for day, label in DAYS:
        globals()[f'{day}_open'] = forms.TimeField(
            label=f'{label} - Apertura',
            required=False,
            widget=forms.TimeInput(attrs={'type': 'time'})
        )
        globals()[f'{day}_close'] = forms.TimeField(
            label=f'{label} - Cierre',
            required=False,
            widget=forms.TimeInput(attrs={'type': 'time'})
        )
```

**2. Vista en finance/views.py:**
```python
@login_required
@require_gym_permission('organizations.change_gym')
def gym_opening_hours(request):
    gym = request.gym
    
    if request.method == 'GET':
        # Parsear JSON → Form
        hours = gym.opening_hours or {}
        form = GymOpeningHoursForm(initial=hours)
    else:  # POST
        form = GymOpeningHoursForm(request.POST)
        if form.is_valid():
            gym.opening_hours = form.cleaned_data
            gym.save()
            messages.success(request, 'Horarios guardados')
    
    return render(request, 'backoffice/finance/opening_hours.html', 
                  {'form': form})
```

**3. URL en finance/urls.py:**
```python
path('opening_hours/', views.gym_opening_hours, 
     name='gym_opening_hours'),
```

**4. Template:**
```html
<form method="post" class="space-y-4">
    {% csrf_token %}
    {% for day in form.days %}
        {{ form|add:day }}_open
        {{ form|add:day }}_close
    {% endfor %}
    <button type="submit">Guardar</button>
</form>
```

**5. Actualizar dashboard:**
```html
<a href="{% url 'gym_opening_hours' %}">
    Horarios de Apertura
</a>
```

---

### PASO 2: Incentivos de Staff (2.5 horas)

**1. Crear forms.py en staff/:**
```python
class IncentiveForm(forms.ModelForm):
    class Meta:
        model = Incentive
        fields = ['name', 'type', 'value', 'condition', 
                  'valid_from', 'valid_until', 'is_active']
```

**2. Vistas en staff/views.py:**
```python
@require_gym_permission('staff.view_incentive')
def incentive_list(request):
    incentives = Incentive.objects.filter(
        staff__user__gyms=request.gym
    )
    return render(request, 'backoffice/staff/incentive/list.html',
                  {'incentives': incentives})

@require_gym_permission('staff.add_incentive')
def incentive_create(request):
    if request.method == 'POST':
        form = IncentiveForm(request.POST)
        if form.is_valid():
            incentive = form.save(commit=False)
            incentive.staff_id = request.POST['staff_id']
            incentive.save()
            messages.success(request, 'Incentivo creado')
            return redirect('incentive_list')
    else:
        form = IncentiveForm()
    return render(request, 'backoffice/staff/incentive/form.html',
                  {'form': form})

# ... edit, delete similar
```

**3. URLs:**
```python
path('incentives/', views.incentive_list, name='incentive_list'),
path('incentives/create/', views.incentive_create, name='incentive_create'),
# ... etc
```

**4. Dashboard link:**
```html
<a href="{% url 'incentive_list' %}">
    Configurar Incentivos
</a>
```

---

### PASO 3: Completar Productos (3 horas)

**1. Actualizar models.py en products/:**
```python
class Product(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(ServiceCategory, 
                                 on_delete=models.SET_NULL, 
                                 null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.SET_NULL,
                                 null=True, blank=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
```

**2. Crear migration:**
```bash
python manage.py makemigrations products
python manage.py migrate
```

**3. Vistas CRUD:**
```python
# products/views.py
class ProductListView(ListView):
    model = Product
    template_name = 'backoffice/products/list.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        return Product.objects.filter(gym=self.request.gym)

# ... CreateView, UpdateView, DeleteView
```

**4. URLs:**
```python
# products/urls.py
path('', ProductListView.as_view(), name='product_list'),
path('create/', ProductCreateView.as_view(), name='product_create'),
# ... etc
```

---

## 📊 VERIFICACIÓN DE COMPLETITUD

### Antes
```
✅ Empresa:          80% (falta horarios)
✅ Finanzas:        100%
✅ Equipo:           85% (falta incentivos UI)
✅ Servicios:       100%
⚠️ Productos:        60% (modelo incompleto)
⚠️ Membresías:       95% (revisar)
TOTAL:              86%
```

### Después (de implementar TODO)
```
✅ Empresa:         100%
✅ Finanzas:        100%
✅ Equipo:          100%
✅ Servicios:       100%
✅ Productos:       100%
✅ Membresías:      100%
TOTAL:              100%
```

---

## ✅ CHECKLIST FINAL

- [ ] Horarios de apertura implementados
- [ ] Incentivos CRUD completo
- [ ] Productos modelo completado
- [ ] Todas las vistas creadas
- [ ] Templates creados
- [ ] URLs registradas
- [ ] Permisos asignados
- [ ] Dashboard actualizado
- [ ] Tests escritos
- [ ] Documentación actualizada

---

## 📞 REFERENCIAS

- **Modelos:** `*/models.py`
- **Vistas existentes:** `finance/views.py`, `staff/views.py`
- **Templates:** `templates/backoffice/settings/`
- **URLs:** `config/urls.py`, `*/urls.py`
- **Permisos:** `accounts/permissions.py`
