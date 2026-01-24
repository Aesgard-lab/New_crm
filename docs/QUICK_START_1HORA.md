# ⚡ QUICK START - IMPLEMENTACIÓN EN 1 HORA

**Objetivo:** Tener Hamburguesa + Sidebar responsive en 60 minutos

**Requisitos:**
- Editor de código (VS Code)
- Navegador con DevTools
- Teléfono para testing

---

## ⏱️ TIMELINE

```
0-5 min:   Preparación
5-30 min:  Implementar hamburguesa
30-50 min: Implementar sidebar
50-60 min: Testear en móvil
```

---

## PASO 1: Preparación (5 minutos)

### 1.1 Abre los archivos que necesitas

**VS Code:**
```
File → Open Workspace
  → c:\Users\santi\OneDrive\Escritorio\New_crm
```

**Archivos a editar:**
```
[ ] templates/base/base.html     ← Editar 1
[ ] templates/base/sidebar.html  ← Editar 2
```

### 1.2 Ten a mano esta guía

```
[ ] SOLUCIONES_RESPONSIVIDAD_CODIGO.md abierto
  → Sección 1: Hamburguesa + Sidebar
```

### 1.3 Abre DevTools para testing

```
F12 → Device toolbar (Ctrl+Shift+M)
  → iPhone SE (375px)
```

---

## PASO 2: Implementar Hamburguesa (25 minutos)

### 2.1 Editar base.html - Paso 1 (5 min)

**Ubicación:** `templates/base/base.html` línea 1

**Encontrar:**
```django-html
<!doctype html>
<html lang="es">
```

**Reemplazar con:**
```django-html
<!doctype html>
<html lang="es" x-data="{ sidebarOpen: false }">
```

**Por qué:** Permite Alpine.js controlar estado del sidebar

**Verificación:**
```
✓ x-data= agregado en <html>
✓ sidebarOpen: false (cierra por defecto)
```

---

### 2.2 Editar base.html - Paso 2 (10 min)

**Ubicación:** `templates/base/base.html` antes de `<main>`

**Encontrar:**
```django-html
    </script>
  </head>

  <body class="bg-slate-50">
    {% include "base/sidebar.html" %}
    <main class="flex-1 lg:ml-64 transition-all">
```

**Reemplazar con:**
```django-html
    </script>
  </head>

  <body class="bg-slate-50">
    {% include "base/sidebar.html" %}
    
    <!-- MOBILE HEADER WITH HAMBURGER -->
    <div class="lg:hidden fixed top-0 left-0 right-0 z-50 bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
      <div class="text-sm font-bold text-slate-800">New CRM</div>
      
      <button @click="sidebarOpen = !sidebarOpen"
              class="p-2 hover:bg-slate-100 rounded-lg transition-colors">
        <svg class="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M4 6h16M4 12h16M4 18h16"></path>
        </svg>
      </button>
    </div>

    <!-- SIDEBAR OVERLAY (Mobile) -->
    <div x-show="sidebarOpen"
         @click="sidebarOpen = false"
         class="lg:hidden fixed inset-0 bg-black/50 z-30 transition-opacity"
         style="display: none;"></div>

    <main class="flex-1 lg:ml-64 transition-all pt-16 lg:pt-0">
```

**Por qué:**
- `lg:hidden` → Hamburguesa solo en móvil
- `x-show` → Alpine.js controla visibilidad
- `@click` → Cierra sidebar al hacer click afuera
- `pt-16 lg:pt-0` → Espacio para header en móvil

**Verificación:**
```
✓ Hamburguesa div agregado
✓ Overlay div agregado
✓ <main> tiene pt-16 lg:pt-0
✓ x-show y @click están presentes
```

---

### 2.3 Editar base.html - Paso 3 (10 min)

**Ubicación:** `templates/base/base.html` cerca del final (antes de `</body>`)

**Encontrar:**
```django-html
  </body>
</html>
```

**Agregar antes de `</body>`:**
```html
    <!-- Aquí va el cierre de </main> si existe -->
    
    <!-- No necesitas agregar nada aquí si Alpine ya está cargado -->
```

**Verificación:**
```
✓ Alpine.js está cargado en <head>
✓ x-data está en <html>
✓ Todos los @click y x-show están presentes
```

---

## PASO 3: Implementar Sidebar (20 minutos)

### 3.1 Editar sidebar.html - Paso 1 (10 min)

**Ubicación:** `templates/base/sidebar.html` línea 1

**Encontrar:**
```django-html
<aside
  class="fixed left-0 top-0 z-40 h-screen w-64 -translate-x-full border-r border-slate-200 bg-white transition-transform lg:translate-x-0">
```

**Reemplazar con:**
```django-html
<aside
  class="fixed left-0 top-0 z-40 h-screen w-64 border-r border-slate-200 bg-white 
         lg:translate-x-0 transition-transform duration-300 ease-in-out"
  :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
  @click.away="sidebarOpen = false">
```

**Por qué:**
- `:class` → Alpine.js controla posición
- `translate-x-0` → Abierto
- `-translate-x-full` → Cerrado
- `transition-transform` → Animación suave
- `@click.away` → Cierra si haces click afuera

**Verificación:**
```
✓ :class dinámico agregado
✓ transition classes presentes
✓ @click.away presente
```

---

### 3.2 Editar sidebar.html - Paso 2 (10 min)

**Ubicación:** Final de `sidebar.html` antes de `</aside>`

**Encontrar:**
```django-html
    </nav>
  </div>
</aside>
```

**Reemplazar con:**
```django-html
    </nav>
    
    <!-- MOBILE: Close button -->
    <button @click="sidebarOpen = false"
            class="lg:hidden mt-auto p-4 w-full bg-slate-100 hover:bg-slate-200 rounded-lg font-medium text-sm text-slate-600 transition-colors">
      Cerrar Menú
    </button>
  </div>
</aside>
```

**Por qué:**
- Botón para cerrar en móvil
- `lg:hidden` → Solo visible en móvil
- `@click="sidebarOpen = false"` → Cierra sidebar

**Verificación:**
```
✓ Botón cerrar agregado
✓ @click presente
✓ lg:hidden presente
```

---

## PASO 4: Testear en Móvil (5 minutos)

### 4.1 Abrir en DevTools

**Chrome/Firefox:**
```
F12 → Device Toolbar → iPhone SE (375px)
```

**En VS Code:**
```
Ctrl+Shift+D → Run
  → Ejecutar servidor Django
```

### 4.2 Verificar funcionamiento

**En desktop (1920px):**
```
□ Hamburguesa NO visible
□ Sidebar siempre visible
□ Layout normal
```

**En móvil (375px):**
```
□ Hamburguesa visible (arriba izquierda)
□ Sidebar oculto por defecto
□ Click hamburguesa → Abre sidebar (animación suave)
□ Click overlay → Cierra sidebar
□ Click botón cerrar → Cierra sidebar
□ Click en link → Navega y cierra
```

### 4.3 Testing en teléfono real (opcional)

```
1. En terminal:
   python manage.py runserver 0.0.0.0:8000

2. En teléfono móvil:
   http://TU_IP:8000
   Ej: http://192.168.1.100:8000

3. Probar:
   □ Hamburguesa aparece
   □ Sidebar abre/cierra suavemente
   □ Navegación funciona
```

---

## ✅ CHECKLIST FINAL

```
ANTES DE EMPEZAR:
□ Archivos base.html y sidebar.html listos
□ VS Code abierto
□ DevTools abierto (F12)
□ Device Toolbar activado (375px)

DURANTE:
□ Cambios en base.html completados (3/3)
□ Cambios en sidebar.html completados (2/2)
□ Guardaste archivos (Ctrl+S)

DESPUÉS:
□ Hamburguesa visible en móvil
□ Sidebar abre al presionar
□ Sidebar cierra al presionar botón
□ Sidebar cierra al presionar link
□ Sidebar cierra al click afuera
□ Desktop layout sin cambios
□ Transiciones suaves
```

---

## 🎯 RESULTADO ESPERADO

### Desktop (1920px):
```
Página normal
Sidebar visible a la izquierda
Sin cambios visuales
```

### Mobile (375px):
```
┌─────────────────────────────────┐
│ [☰] New CRM                     │  ← Hamburguesa
├─────────────────────────────────┤
│                                 │
│     Dashboard                   │
│     (contenido)                 │
│                                 │
└─────────────────────────────────┘

Al presionar [☰]:
┌──────────────────┐
│ New CRM          │  ← Overlay oscuro
│ ─────────────    │
│ ♦ Dashboard      │
│ ◇ Franquicia     │  ← Sidebar slide-in
│ ◇ Reportes       │
│ ◇ Clientes       │
│ ... más items    │
│ ─────────────    │
│ [Cerrar Menú]    │
└──────────────────┘
```

---

## 🐛 TROUBLESHOOTING

### Issue: Hamburguesa no aparece

**Solución:**
```
1. Verificar: class="lg:hidden" está en hamburguesa div
2. Verificar: DevTools está en 375px
3. Hard refresh: Ctrl+Shift+R
4. Limpiar caché: Ctrl+Shift+Delete
```

### Issue: Sidebar no abre

**Solución:**
```
1. Verificar: x-data en <html tag>
2. Verificar: @click="sidebarOpen = !sidebarOpen" en button
3. Verificar: Alpine.js está cargado (console: x-data)
4. Verificar: :class en <aside>
```

### Issue: Sidebar no se cierra

**Solución:**
```
1. Verificar: @click.away en <aside>
2. Verificar: @click="sidebarOpen = false" en botón
3. Verificar: overlay tiene @click="sidebarOpen = false"
4. Hard refresh: Ctrl+Shift+R
```

### Issue: Layout roto en desktop

**Solución:**
```
1. Verificar: lg:translate-x-0 en <aside>
2. Verificar: lg:ml-64 en <main>
3. Verificar: lg:hidden en hamburguesa
4. Verificar: Tailwind CDN está cargado
```

---

## 📞 SI ALGO FALLA

**Revisa:**
1. Console en DevTools (F12)
2. Revisa si hay errores de JavaScript
3. Copia exactamente el código (espacios importan)
4. Verifica que grabaste los cambios (Ctrl+S)

**Necesitas help:**
```
Documento: EJEMPLOS_VISUALES_CHECKLIST_TECNICO.md
Sección: 11 - Troubleshooting
→ Soluciones detalladas para cada error
```

---

## 🎉 ¡LISTO!

En 1 hora tienes:

```
✅ Hamburguesa funcionando
✅ Sidebar responsive
✅ Transiciones suaves
✅ Staff puede navegar en móvil
✅ Base para siguientes mejoras
```

**Siguiente paso:**

Implementar [Tablas responsive](SOLUCIONES_RESPONSIVIDAD_CODIGO.md#2️⃣-tablas-responsive) (2 horas)

---

## 📊 PROGRESO

```
✓ Hamburguesa (1 hora)    ✅
  └─ Staff navega en móvil

→ Tablas (2 horas)        ⏳ Siguiente
  └─ Datos completos en móvil

→ Formularios (1.5h)      📅
  └─ Inputs optimizados

→ Extras (1h)             📅
  └─ Imágenes, tipografía

TOTAL: 7 horas para 100% responsive
```

---

**¿Completaste esto?**

✅ SÍ → Pasa a [Tablas responsive](SOLUCIONES_RESPONSIVIDAD_CODIGO.md#2️⃣-tablas-responsive)

❌ NO → Revisa [Troubleshooting](#-troubleshooting)

🚀
