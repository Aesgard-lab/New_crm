# 📅 WIDGET DE HORARIO - GUÍA COMPLETA

## 🎯 ¿Qué es esto?

Un widget profesional que puedes embeber en tu sitio web para mostrar el horario de clases en tiempo real, con:
- ✅ Lista de clases con fotos de instructores
- ✅ Botones de reserva integrados
- ✅ Filtros por actividad
- ✅ Navegación por fechas
- ✅ Indicadores de capacidad disponible
- ✅ Diseño responsive (móvil, tablet, desktop)

---

## 🎨 OPCIONES DE DISEÑO

Tenemos **2 estilos** de widget:

### **Opción 1: Vista de Lista** 📋 (RECOMENDADA)
**URL:** `http://localhost:8000/embed/tu-gimnasio/schedule/`

**Características:**
- Lista vertical con toda la información
- Fotos de instructores
- Botones de reserva destacados
- Filtros por actividad
- Navegación día a día
- Indicadores de plazas disponibles

**Mejor para:** Landing pages, páginas principales, móviles

---

### **Opción 2: Vista de Calendario** 📆
**URL:** `http://localhost:8000/embed/tu-gimnasio/schedule/calendar/`

**Características:**
- Calendario mensual estilo Google Calendar
- Vista compacta de múltiples días
- Colores por tipo de actividad
- Modal con detalles al hacer clic

**Mejor para:** Vista mensual completa, escritorio

---

## 🚀 INTEGRACIÓN BÁSICA

### OPCIÓN 1: VISTA DE LISTA (Recomendada)

```html
<iframe 
    src="http://localhost:8000/embed/TU-GIMNASIO/schedule/"
    width="100%" 
    height="1200"
    frameborder="0"
    style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
</iframe>
```

**Con tema oscuro:**
```html
<iframe 
    src="http://localhost:8000/embed/TU-GIMNASIO/schedule/?theme=dark"
    width="100%" 
    height="1200"
    frameborder="0"
    style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
</iframe>
```

---

### OPCIÓN 2: VISTA DE CALENDARIO

```html
<iframe 
    src="http://localhost:8000/embed/TU-GIMNASIO/schedule/calendar/"
    width="100%" 
    height="800"
    frameborder="0"
    style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
</iframe>
```

---

## 🛠️ PARÁMETROS DE PERSONALIZACIÓN

| Parámetro | Valores | Descripción | Ejemplo |
|-----------|---------|-------------|---------|
| `theme` | `light`, `dark` | Tema del widget | `?theme=dark` |

**Ejemplo completo:**
```html
<iframe 
    src="http://localhost:8000/embed/qombo-arganzuela/schedule/?theme=light"
    width="100%" 
    height="1200">
</iframe>
```

---

## 🌐 INTEGRACIÓN EN PLATAFORMAS

### WordPress

1. Edita la página donde quieres el horario
2. Añade un bloque **"HTML Personalizado"**
3. Pega el código del iframe
4. **Ajusta la altura** según el número de clases (recomendado: 1200px)
5. Guarda y publica

**Bloque de ejemplo en WordPress:**
```html
<!-- wp:html -->
<div class="horario-gimnasio" style="max-width: 1200px; margin: 40px auto;">
    <iframe 
        src="http://localhost:8000/embed/tu-gimnasio/schedule/"
        width="100%" 
        height="1200"
        frameborder="0"
        style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
    </iframe>
</div>
<!-- /wp:html -->
```

---

### Wix

1. Haz clic en **"+ Añadir"** en el editor
2. Selecciona **"Más" → "HTML iframe"**
3. Pega la URL del widget: `http://localhost:8000/embed/tu-gimnasio/schedule/`
4. Ajusta el tamaño:
   - Ancho: **100%** o **1200px**
   - Alto: **1200px**
5. Publica los cambios

---

### Squarespace

1. Edita la página
2. Añade un bloque **"Código"** (Code Block)
3. Pega el código HTML del iframe
4. Guarda

---

### Shopify

```html
<!-- En tu tema: sections/schedule.liquid -->
<div class="schedule-widget-container">
  <iframe 
    src="{{ shop.metafields.custom.widget_url | default: 'http://localhost:8000/embed/tu-gimnasio/schedule/' }}"
    width="100%" 
    height="1200"
    frameborder="0"
    style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
  </iframe>
</div>
```

---

### HTML Estático

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Horario - Mi Gimnasio</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background-color: #f8fafc;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 20px;
            text-align: center;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5rem;
        }
        
        .widget-container {
            max-width: 1200px;
            margin: -40px auto 60px;
            padding: 0 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Nuestro Horario de Clases</h1>
        <p>Reserva tu clase favorita</p>
    </div>
    
    <div class="widget-container">
        <iframe 
            src="http://localhost:8000/embed/tu-gimnasio/schedule/"
            width="100%" 
            height="1200"
            frameborder="0"
            style="border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.12);">
        </iframe>
    </div>
</body>
</html>
```

---

### React / Next.js

```jsx
// components/ScheduleWidget.jsx
export default function ScheduleWidget({ gymSlug = 'tu-gimnasio', theme = 'light' }) {
  const widgetUrl = `http://localhost:8000/embed/${gymSlug}/schedule/?theme=${theme}`;
  
  return (
    <div className="schedule-widget">
      <iframe
        src={widgetUrl}
        width="100%"
        height="1200"
        frameBorder="0"
        style={{
          borderRadius: '12px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
        }}
        title="Horario de Clases"
      />
    </div>
  );
}

// Uso:
// <ScheduleWidget gymSlug="qombo-arganzuela" theme="light" />
```

---

### Vue.js / Nuxt

```vue
<!-- components/ScheduleWidget.vue -->
<template>
  <div class="schedule-widget">
    <iframe
      :src="widgetUrl"
      width="100%"
      height="1200"
      frameborder="0"
      style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);"
      title="Horario de Clases"
    />
  </div>
</template>

<script>
export default {
  props: {
    gymSlug: {
      type: String,
      default: 'tu-gimnasio'
    },
    theme: {
      type: String,
      default: 'light'
    }
  },
  computed: {
    widgetUrl() {
      return `http://localhost:8000/embed/${this.gymSlug}/schedule/?theme=${this.theme}`;
    }
  }
}
</script>

<!-- Uso: -->
<!-- <ScheduleWidget gym-slug="qombo-arganzuela" theme="light" /> -->
```

---

## 🔒 SEGURIDAD Y DOMINIOS PERMITIDOS

Por defecto, el widget funciona en cualquier dominio. Para restringirlo:

1. Ve al **Backoffice → Configuración → Organizations → Gimnasios → [Tu Gimnasio] → Editar**
2. Busca la sección **"Portal Público"**
3. Marca **"Permitir embedding"**
4. En **"Dominios permitidos para embedding"** añade tus dominios (uno por línea):

```
migimnasio.com
www.migimnasio.com
app.migimnasio.com
```

---

## 📱 DISEÑO RESPONSIVE

El widget es **100% responsive** y se adapta automáticamente:

| Dispositivo | Ancho | Comportamiento |
|-------------|-------|----------------|
| 📱 Móvil | < 640px | Lista vertical compacta, botones apilados |
| 📱 Tablet | 640px - 1024px | Layout optimizado para pantallas medianas |
| 💻 Desktop | > 1024px | Vista completa con todas las columnas |

**No necesitas hacer nada especial**, el widget detecta el tamaño automáticamente.

---

## 🎨 COLORES Y BRANDING

El widget usa automáticamente el **color de marca** de tu gimnasio:

✅ **Se aplica a:**
- Botones de reserva
- Elementos activos
- Filtros seleccionados
- Badges y destacados

**Para cambiar el color:**
1. **Backoffice → Configuración → Organizations → Gimnasios → [Tu Gimnasio]**
2. Campo **"Color de marca"** (Brand Color)
3. Introduce un color hexadecimal (ejemplo: `#06b6d4`)
4. Guarda

**El widget se actualizará automáticamente** sin necesidad de cambiar código.

---

## 🔄 ACTUALIZACIÓN EN TIEMPO REAL

✅ El widget muestra datos en **tiempo real**:
- Cambios en el horario aparecen inmediatamente
- Plazas disponibles se actualizan al reservar
- Nuevas actividades aparecen automáticamente
- Cambios de instructor se reflejan al instante

**No necesitas actualizar ni volver a publicar el widget.**

---

## ❓ PREGUNTAS FRECUENTES

### ¿El widget se actualiza solo?
✅ **Sí.** Cualquier cambio en el backoffice aparece automáticamente.

### ¿Los clientes pueden reservar directamente?
✅ **Sí.** Con botones de reserva integrados. Necesitan iniciar sesión o crear cuenta.

### ¿Funciona en móviles?
✅ **Totalmente responsive.** Se adapta a todos los dispositivos.

### ¿Puedo usar ambas vistas (lista y calendario)?
✅ **Sí.** Puedes poner ambas en diferentes páginas o dejar que el usuario elija.

### ¿Afecta la velocidad de mi web?
✅ **No.** El widget carga en un iframe independiente y no ralentiza tu sitio.

### ¿Qué pasa si no hay clases ese día?
✅ Muestra un mensaje amigable: **"No hay clases programadas"**

### ¿Puedo cambiar la altura del iframe?
✅ **Sí.** Cambia el valor `height="1200"` al que necesites. Recomendado:
- Vista de lista: **1200px - 1600px**
- Vista de calendario: **800px - 1000px**

### ¿Se puede personalizar más allá del color?
⚠️ Por ahora solo el color de marca. Más opciones próximamente.

---

## 🆘 SOPORTE TÉCNICO

**¿Problemas con el widget?**

Contacta con soporte incluyendo:
1. **URL de tu gimnasio** (slug)
2. **Captura de pantalla** del problema
3. **Navegador** y versión (Chrome, Firefox, Safari...)
4. **Dispositivo** (móvil, tablet, desktop)
5. **URL de tu web** donde está el widget

---

## 📊 EJEMPLOS REALES

### Ejemplo 1: Página de Horarios Completa
```html
<!DOCTYPE html>
<html>
<head>
    <title>Horarios - Qombo Arganzuela</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; background: #f8fafc;">
    <div style="max-width: 1400px; margin: 0 auto; padding: 40px 20px;">
        <h1 style="text-align: center; color: #1e293b; margin-bottom: 40px;">
            Horario de Clases
        </h1>
        
        <iframe 
            src="http://localhost:8000/embed/qombo-arganzuela/schedule/"
            width="100%" 
            height="1400"
            frameborder="0"
            style="border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.12);">
        </iframe>
    </div>
</body>
</html>
```

### Ejemplo 2: Sección en Landing Page
```html
<section class="schedule-section" style="background: #f8fafc; padding: 80px 0;">
    <div class="container" style="max-width: 1200px; margin: 0 auto; padding: 0 20px;">
        <div style="text-align: center; margin-bottom: 60px;">
            <h2 style="font-size: 2.5rem; color: #1e293b; margin-bottom: 16px;">
                Encuentra tu Clase Perfecta
            </h2>
            <p style="font-size: 1.25rem; color: #64748b;">
                Reserva en segundos. Más de 50 clases semanales.
            </p>
        </div>
        
        <iframe 
            src="http://localhost:8000/embed/qombo-arganzuela/schedule/"
            width="100%" 
            height="1200"
            frameborder="0"
            style="border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.15);">
        </iframe>
    </div>
</section>
```

---

## 🎯 CHECKLIST ANTES DE PUBLICAR

Antes de poner el widget en producción, verifica:

- [ ] Has reemplazado **TU-GIMNASIO** con el slug correcto
- [ ] Has cambiado **localhost:8000** por tu dominio real
- [ ] El widget se ve bien en **móvil, tablet y desktop**
- [ ] Los colores coinciden con tu marca
- [ ] Las actividades están marcadas como **"Visible online"**
- [ ] Has configurado los **dominios permitidos** (opcional)
- [ ] El botón de reserva funciona correctamente
- [ ] Has probado el flujo completo de reserva

---

**¡Listo! Tu widget está funcionando. 🎉**
