# 🏗️ ARQUITECTURA MEJORADA - Staff sin App

**Contexto:** Staff y Owners usarán SOLO web (sin app nativa)  
**Objetivo:** Web tan buena que no necesiten app

---

## 1. DECISIÓN ARQUITECTÓNICA

### Propuesta Actual
- ✅ Staff: Web responsive (RECOMENDADO)
- ✅ Owners: Web responsive
- ❌ Staff: No hace falta app nativa (por ahora)

### Ventajas
```
✅ Menos mantenimiento
✅ Una única codebase (Django + HTML)
✅ Deploy centralizad
✅ Updates automáticos
✅ Menor presupuesto
```

### Desventajas
```
⚠️ Sin offline (parcial)
⚠️ Necesita conexión
⚠️ Sin notificaciones push
⚠️ Sin acceso a cámara integrado
```

---

## 2. RECOMENDACIONES POR ROL

### 👨‍💼 OWNER/ADMIN

**Principales tareas:**
- Dashboard (lectura)
- Configuraciones
- Reportes
- Gestión de staff

**Dispositivos:** Laptop 95%, Tablet 5%

**Responsividad:** IMPORTANTE (para emergencias)

```
✅ PRIORIDAD: Desktop + Tablet
⚠️ Móvil: Funcional pero no crítico
```

---

### 👨‍🏫 STAFF (Instructores/Recepcionistas)

**Principales tareas:**
- ⏰ Fichar entrada/salida
- 📱 Ver clases asignadas
- 💰 Ver comisiones
- 📸 Foto de perfil
- ⚙️ Cambiar contraseña

**Dispositivos:** Móvil 60%, Tablet 30%, Desktop 10%

**Responsividad:** CRÍTICA

```
✅ PRIORIDAD: Móvil + Tablet
⚠️ Desktop: Debe funcionar pero no es primario
```

---

## 3. OPTIMIZACIONES POR USUARIO

### Para OWNER (Desktop-first)

```django-html
<!-- Mensajes importantes en desktop -->
<div class="hidden md:block p-4 bg-yellow-50 rounded-lg border border-yellow-200">
  💡 Notificación importante para dueño
</div>

<!-- En móvil: versión compacta -->
<div class="md:hidden p-2 bg-yellow-50 rounded-lg border border-yellow-200">
  ⚠️ Notificación
</div>
```

### Para STAFF (Mobile-first)

```django-html
<!-- Botones grandes y táctiles -->
<button class="w-full py-4 px-4 bg-emerald-600 hover:bg-emerald-700 
               text-white font-bold text-lg rounded-xl
               touch-target">
  ✓ FICHAR ENTRADA
</button>

<!-- Confirmación clara -->
{% if show_confirmation %}
<div class="fixed inset-0 flex items-center justify-center z-50 p-4">
  <div class="bg-white rounded-2xl p-6 max-w-sm w-full shadow-2xl">
    <h2 class="text-xl font-bold mb-4">¿Confirmaste tu entrada?</h2>
    <div class="flex gap-3">
      <button class="flex-1 py-3 bg-slate-200 rounded-lg font-bold">
        NO
      </button>
      <button class="flex-1 py-3 bg-emerald-600 text-white rounded-lg font-bold">
        SÍ
      </button>
    </div>
  </div>
</div>
{% endif %}
```

---

## 4. ESTRUCTURA DE VISTAS OPTIMIZADAS

### 4.1 Dashboard diferenciado

```python
# accounts/views.py

@login_required
def dashboard(request):
    """Dashboard adaptado según rol"""
    
    user = request.user
    
    # Cargar datos según rol
    if user.has_perm('staff.view_dashboard'):
        # STAFF: Información personal
        context = {
            'is_staff': True,
            'shifts_today': user.staffprofile.shifts.today(),
            'commissions': user.staffprofile.commissions.this_month(),
            'tasks': user.staffprofile.tasks.pending(),
        }
        template = 'backoffice/staff/dashboard.html'
    
    elif user.has_perm('company.view_dashboard'):
        # OWNER: Información del negocio
        context = {
            'is_owner': True,
            'gym_stats': get_gym_stats(request.gym),
            'revenue': get_revenue(request.gym),
            'alerts': get_alerts(request.gym),
        }
        template = 'backoffice/owner/dashboard.html'
    
    return render(request, template, context)
```

### 4.2 Templates diferenciados

```
templates/
├── backoffice/
│   ├── staff/
│   │   ├── dashboard.html          ← Mobile-first
│   │   ├── clock_in_out.html       ← Large buttons
│   │   ├── my_schedule.html        ← Accordion layout
│   │   └── my_commissions.html     ← Cards, no tablas
│   │
│   └── owner/
│       ├── dashboard.html          ← Desktop-first
│       ├── analytics.html          ← Charts responsive
│       ├── reports.html            ← Data tables
│       └── settings.html           ← Complex forms
```

---

## 5. COMPONENTES ESPECÍFICOS POR ROL

### 5.1 Clock In/Out (STAFF MOBILE)

**Ubicación a crear:** `templates/backoffice/staff/clock_in_out.html`

```django-html
{% extends "backoffice/base.html" %}

{% block content %}
<div class="min-h-screen bg-gradient-to-b from-blue-50 to-white pt-4">
  
  <!-- Current Time Big Display -->
  <div class="text-center mb-8" x-data="{ time: new Date().toLocaleTimeString() }"
       x-init="setInterval(() => time = new Date().toLocaleTimeString(), 1000)">
    <div class="text-6xl font-bold text-slate-900">
      <span x-text="time"></span>
    </div>
    <div class="text-sm text-slate-500 mt-2">
      Hoy, <span x-text="new Date().toLocaleDateString('es-ES')"></span>
    </div>
  </div>
  
  <!-- Main CTA Button -->
  <div class="px-4 mb-6">
    {% if is_clocked_in %}
    <form method="post" action="{% url 'staff_clock_out' %}">
      {% csrf_token %}
      <button type="submit"
              class="w-full py-6 bg-red-600 hover:bg-red-700 text-white font-bold text-2xl rounded-2xl shadow-lg active:scale-95 transition-all">
        🔴 SALIR
      </button>
    </form>
    {% else %}
    <form method="post" action="{% url 'staff_clock_in' %}">
      {% csrf_token %}
      <button type="submit"
              class="w-full py-6 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-2xl rounded-2xl shadow-lg active:scale-95 transition-all">
        🟢 ENTRAR
      </button>
    </form>
    {% endif %}
  </div>
  
  <!-- Status Card -->
  <div class="px-4 mb-6">
    <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
      <div class="text-sm text-slate-500 font-bold uppercase mb-2">Estado</div>
      {% if is_clocked_in %}
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 bg-emerald-600 rounded-full animate-pulse"></span>
          <span class="text-lg font-bold text-emerald-600">
            Fichado desde {{ clock_in_time|time:"H:i" }}
          </span>
        </div>
      {% else %}
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 bg-slate-400 rounded-full"></span>
          <span class="text-lg font-bold text-slate-500">
            No fichado
          </span>
        </div>
      {% endif %}
    </div>
  </div>
  
  <!-- Today's Schedule -->
  <div class="px-4">
    <h3 class="font-bold text-lg text-slate-900 mb-4">Horario de Hoy</h3>
    <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
      {% if todays_schedule %}
        <div class="space-y-3">
          {% for schedule in todays_schedule %}
          <div class="flex items-center gap-4">
            <div class="text-2xl">
              {% if schedule.type == 'class' %}
              🏋️
              {% elif schedule.type == 'reception' %}
              🛎️
              {% endif %}
            </div>
            <div class="flex-1">
              <div class="font-bold text-slate-900">{{ schedule.title }}</div>
              <div class="text-sm text-slate-500">
                {{ schedule.start_time|time:"H:i" }} - {{ schedule.end_time|time:"H:i" }}
              </div>
            </div>
          </div>
          {% endfor %}
        </div>
      {% else %}
        <p class="text-slate-400 text-center py-4">Sin actividades hoy</p>
      {% endif %}
    </div>
  </div>

</div>
{% endblock %}
```

### 5.2 Dashboard OWNER (Desktop-first)

**Ubicación a crear:** `templates/backoffice/owner/dashboard.html`

```django-html
{% extends "backoffice/base.html" %}

{% block content %}
<div class="space-y-6">
  
  <!-- KPIs Row -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
    <!-- Miembros Activos -->
    <div class="bg-white rounded-2xl p-6 border border-slate-200">
      <div class="text-sm text-slate-500 font-bold uppercase mb-2">Miembros Activos</div>
      <div class="text-4xl font-bold text-slate-900">{{ active_members }}</div>
      <div class="text-xs text-slate-400 mt-2">↑ {{ member_growth }}% este mes</div>
    </div>
    
    <!-- Ingresos Hoy -->
    <div class="bg-white rounded-2xl p-6 border border-slate-200">
      <div class="text-sm text-slate-500 font-bold uppercase mb-2">Ingresos Hoy</div>
      <div class="text-4xl font-bold text-emerald-600">{{ revenue_today }}€</div>
      <div class="text-xs text-slate-400 mt-2">Meta: {{ revenue_goal }}€</div>
    </div>
    
    <!-- Ocupación Clases -->
    <div class="bg-white rounded-2xl p-6 border border-slate-200">
      <div class="text-sm text-slate-500 font-bold uppercase mb-2">Ocupación Promedio</div>
      <div class="text-4xl font-bold text-blue-600">{{ avg_occupancy }}%</div>
      <div class="text-xs text-slate-400 mt-2">Capacidad total: {{ total_capacity }}</div>
    </div>
    
    <!-- Staff Activo -->
    <div class="bg-white rounded-2xl p-6 border border-slate-200">
      <div class="text-sm text-slate-500 font-bold uppercase mb-2">Staff Trabajando</div>
      <div class="text-4xl font-bold text-purple-600">{{ staff_working }} / {{ total_staff }}</div>
      <div class="text-xs text-slate-400 mt-2">Hora punta: 17:00-19:00</div>
    </div>
  </div>
  
  <!-- Charts Row -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Revenue Chart -->
    <div class="bg-white rounded-2xl p-6 border border-slate-200">
      <h3 class="font-bold text-lg text-slate-900 mb-4">Ingresos - Últimos 7 días</h3>
      <canvas id="revenueChart"></canvas>
    </div>
    
    <!-- Classes Occupancy -->
    <div class="bg-white rounded-2xl p-6 border border-slate-200">
      <h3 class="font-bold text-lg text-slate-900 mb-4">Ocupación por Clase</h3>
      <canvas id="occupancyChart"></canvas>
    </div>
  </div>
  
  <!-- Alerts Section -->
  <div class="bg-white rounded-2xl p-6 border border-slate-200">
    <h3 class="font-bold text-lg text-slate-900 mb-4">⚠️ Alertas Importantes</h3>
    <div class="space-y-3">
      {% for alert in alerts %}
      <div class="flex items-start gap-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
        <span class="text-2xl">{{ alert.icon }}</span>
        <div>
          <div class="font-bold text-yellow-900">{{ alert.title }}</div>
          <div class="text-sm text-yellow-700">{{ alert.description }}</div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>

</div>

<script>
  // Chart initialization
  // Revisar: Usar Chart.js con breakpoints
</script>
{% endblock %}
```

---

## 6. CONSIDERACIONES TÉCNICAS

### 6.1 Offline-first (Opcional pero recomendado)

Para staff que usa móvil en el gym sin WiFi estable:

```python
# En settings.py
INSTALLED_APPS = [
    ...
    'serviceworker',  # django-pwa
]

PWA_APP_NAME = 'New CRM'
PWA_APP_DESCRIPTION = 'Sistema de Gestión para Gimnasios'
PWA_APP_THEME_COLOR = '#0f172a'
PWA_APP_BACKGROUND_COLOR = '#ffffff'
PWA_APP_ICONS = [
    {
        'src': '/static/icons/icon-192x192.png',
        'sizes': '192x192',
        'type': 'image/png'
    }
]
```

### 6.2 Caché de datos

```python
# accounts/views.py
from django.views.decorators.cache import cache_page
from django.core.cache import cache

@cache_page(60 * 5)  # Cache 5 minutos
def staff_dashboard(request):
    """Dashboard staff con caché"""
    return render(request, 'staff/dashboard.html', context)

# Invalidar caché en updates
def update_shift(request, shift_id):
    cache.delete(f'staff_dashboard_{request.user.id}')
    # ... procesar update
```

### 6.3 Notificaciones (Sin push, pero con polling)

```javascript
// En template de staff
<script>
  // Polling cada 30 segundos
  setInterval(() => {
    fetch('/api/notifications/')
      .then(r => r.json())
      .then(data => {
        if (data.unread > 0) {
          // Mostrar badge
          document.querySelector('[data-notifications]').textContent = data.unread;
        }
      });
  }, 30000);
</script>
```

---

## 7. FLUJOS PRINCIPALES

### 7.1 Staff - Fichaje (4 pasos)

```
1. Llega al gym
   ↓
2. Abre web (PWA instalada)
   ↓
3. Ve botón GRANDE "FICHAR ENTRADA"
   ↓
4. Presiona → Confirmación clara
   ↓
5. Ding 🔔 + Feedback visual
```

### 7.2 Owner - Review Diario (5 min)

```
1. Abre web en laptop
   ↓
2. Ve dashboard con 4 KPIs principales
   ↓
3. Revisa alertas importantes
   ↓
4. Checa ingresos vs meta
   ↓
5. Decide acciones (si es necesario)
```

---

## 8. ROADMAP FUTURO

### Fase 1 (Hoy - 2 semanas)
✅ Responsividad web completa
✅ Tablas responsive
✅ Formularios optimizados
✅ Staff dashboard mobile

### Fase 2 (Próximo mes)
⏳ PWA instalable
⏳ Offline caché básico
⏳ Notificaciones por polling

### Fase 3 (Trimestre)
📅 App nativa (si la web no es suficiente)
📅 Notificaciones push
📅 Acceso cámara integrado

---

## 9. MÉTRICAS DE ÉXITO

### Para STAFF
```
✅ Fichar entrada en <2 segundos
✅ Cargar dashboard en <3 segundos
✅ Usable con 1 mano (mobile)
✅ >90% no vuelve a escritorio para tareas principales
```

### Para OWNER
```
✅ Dashboard carga en <1 segundo
✅ Ver todos los KPIs en 5 segundos
✅ Acceder a configuraciones en <10 clicks
✅ >95% satisfacción respecto a desktop
```

---

## 10. CHECKLIST FINAL

- [ ] Responsive completo (mobile first)
- [ ] Botones táctiles (mín 44x44px)
- [ ] Formularios optimizados
- [ ] Tablas responsive
- [ ] Imágenes con lazy loading
- [ ] Tipografía escalada
- [ ] Espacios responsive
- [ ] Testing en 3 dispositivos
- [ ] PWA installable
- [ ] Caché básico
- [ ] Documentación actualizada
- [ ] Performance <3s load (4G)

---

**¿Listo para empezar? ¿Quieres que comencemos con:**
1. Hamburguesa + sidebar móvil
2. Tablas responsive
3. Dashboard diferenciado por rol
4. Todo lo anterior

?
