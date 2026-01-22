# 📱 GUÍA DE INTEGRACIÓN - WIDGET DE HORARIO

## 🎯 ¿Qué es esto?

Un widget que puedes poner en tu página web para mostrar el horario de clases de tu gimnasio en tiempo real.

---

## 🚀 OPCIÓN 1: CÓDIGO PARA COPIAR Y PEGAR (MÁS FÁCIL)

### Paso 1: Copia este código
```html
<div style="max-width: 1200px; margin: 40px auto; padding: 0 20px;">
    <iframe 
        src="TU_URL_AQUI/embed/TU-GIMNASIO/schedule/" 
        width="100%" 
        height="800px" 
        frameborder="0"
        style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
    </iframe>
</div>

<script>
// Ajuste automático de altura
window.addEventListener('message', function(e) {
    if (e.data.type === 'resize') {
        var iframe = document.querySelector('iframe[src*="schedule"]');
        if (iframe) iframe.style.height = e.data.height + 'px';
    }
});
</script>
```

### Paso 2: Reemplaza estos valores:

1. **TU_URL_AQUI** → La URL de tu sistema (ejemplo: `https://micrm.com`)
2. **TU-GIMNASIO** → El slug de tu gimnasio (te lo damos nosotros)

### Paso 3: Pega el código en tu web

- Si usas **WordPress**: Añade un bloque "HTML Personalizado"
- Si usas **Wix**: Añade un elemento "Código HTML"
- Si usas **Squarespace**: Añade un bloque "Código"
- Si tienes web propia: Pégalo donde quieras mostrar el horario

---

## 🎨 PERSONALIZACIÓN

### Tema Oscuro
```html
<iframe src="TU_URL/embed/TU-GIMNASIO/schedule/?theme=dark" ...>
```

### Tema Claro (por defecto)
```html
<iframe src="TU_URL/embed/TU-GIMNASIO/schedule/?theme=light" ...>
```

### Mostrar solo una actividad
```html
<iframe src="TU_URL/embed/TU-GIMNASIO/schedule/?activity=5" ...>
```
*(Reemplaza "5" con el ID de la actividad que quieras mostrar)*

---

## 📋 URLs DE EJEMPLO PARA CADA GIMNASIO

### Para LOCALHOST (desarrollo):
```
Verify Gym:
http://localhost:8000/embed/verify-gym/schedule/

Qombo Madrid Central:
http://localhost:8000/embed/qombo-madrid-central/schedule/

Qombo Barcelona Beach:
http://localhost:8000/embed/qombo-barcelona-beach/schedule/

Qombo Valencia City:
http://localhost:8000/embed/qombo-valencia-city/schedule/

Qombo Sevilla Sur:
http://localhost:8000/embed/qombo-sevilla-sur/schedule/

Qombo Arganzuela:
http://localhost:8000/embed/qombo-arganzuela/schedule/

HQ Madrid:
http://localhost:8000/embed/hq-madrid/schedule/

Sucursal Barcelona:
http://localhost:8000/embed/sucursal-barcelona/schedule/

FitChain Sucursal Demo:
http://localhost:8000/embed/fitchain-sucursal-demo/schedule/
```

### Para PRODUCCIÓN:
Reemplaza `http://localhost:8000` por tu dominio real (ej: `https://tucrm.com`)

---

## 🌐 EJEMPLO COMPLETO PARA WORDPRESS

### Método 1: Gutenberg (Editor de Bloques)

1. Ve a **Páginas → Editar Página**
2. Haz clic en el botón **+** para añadir un bloque
3. Busca **"HTML Personalizado"**
4. Pega este código:

```html
<div style="max-width: 1200px; margin: 40px auto;">
    <h2 style="text-align: center; margin-bottom: 30px;">Nuestro Horario de Clases</h2>
    <iframe 
        src="https://tudominio.com/embed/tu-gimnasio/schedule/" 
        width="100%" 
        height="800px" 
        frameborder="0"
        style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
    </iframe>
</div>

<script>
window.addEventListener('message', function(e) {
    if (e.data.type === 'resize') {
        var iframe = document.querySelector('iframe[src*="schedule"]');
        if (iframe) iframe.style.height = e.data.height + 'px';
    }
});
</script>
```

5. **Actualiza/Publica** la página
6. ¡Listo! 🎉

---

## 📱 RESPONSIVE (MÓVILES)

El widget se adapta automáticamente a todos los dispositivos:
- ✅ Móviles
- ✅ Tablets
- ✅ Desktop
- ✅ Pantallas grandes

**No necesitas hacer nada extra**, ya está optimizado.

---

## 🔧 CONFIGURACIÓN AVANZADA

### Altura Personalizada
```html
<iframe ... height="600px">  <!-- Para widget más pequeño -->
<iframe ... height="1000px"> <!-- Para widget más grande -->
```

### Sin sombra y bordes redondeados
```html
<iframe ... style="border: none;">
```

### Centrado con ancho máximo
```html
<div style="max-width: 1400px; margin: 0 auto;">
    <iframe ...>
</div>
```

---

## ❓ PREGUNTAS FRECUENTES

### ¿El horario se actualiza solo?
**Sí**, cada vez que cambies algo en el backoffice, se verá automáticamente en el widget.

### ¿Los clientes pueden reservar desde el widget?
**Sí**, al hacer clic en una clase se abre una ventana con los detalles y un botón para reservar que los lleva al portal completo.

### ¿Funciona en mi web actual?
**Sí**, funciona en cualquier web que permita insertar HTML personalizado:
- WordPress
- Wix
- Squarespace
- Shopify
- Weebly
- HTML/CSS propio
- React, Vue, Angular

### ¿Puedo cambiar los colores?
**Los colores se toman automáticamente** de la configuración de tu gimnasio en el backoffice (campo "Color de Marca").

### ¿Hay límite de visitas?
**No**, el widget puede recibir todas las visitas que necesites.

---

## 🎯 EJEMPLO VISUAL

Abre este archivo en tu navegador para ver el widget funcionando:
```
ejemplo_widget_embed.html
```

*(Está en la raíz del proyecto)*

---

## 📞 SOPORTE

Si tienes problemas o preguntas, contacta con soporte técnico.

---

## ✅ CHECKLIST ANTES DE PUBLICAR

- [ ] He reemplazado `TU_URL_AQUI` por mi dominio real
- [ ] He reemplazado `TU-GIMNASIO` por mi slug correcto
- [ ] He probado el widget en la página
- [ ] Se ve bien en móvil
- [ ] Los clientes pueden hacer clic en las clases
- [ ] El botón "Reservar" funciona

---

## 🚀 CÓDIGO FINAL LISTO PARA USAR

### Para tu gimnasio específico:

**1. Encuentra tu slug** en el backoffice (Configuración → Portal Público)

**2. Usa este código exacto:**

```html
<!-- HORARIO DE CLASES - Widget Embebible -->
<div style="max-width: 1200px; margin: 40px auto; padding: 0 20px;">
    <iframe 
        src="https://CAMBIA-ESTO.com/embed/CAMBIA-SLUG/schedule/" 
        width="100%" 
        height="800px" 
        frameborder="0"
        style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);"
        title="Horario de Clases">
    </iframe>
</div>

<script>
window.addEventListener('message', function(e) {
    if (e.data.type === 'resize') {
        var iframe = document.querySelector('iframe[src*="schedule"]');
        if (iframe) iframe.style.height = e.data.height + 'px';
    }
});
</script>
```

**3. Reemplaza:**
- `CAMBIA-ESTO.com` → Tu dominio (ej: `tucrm.com`)
- `CAMBIA-SLUG` → Tu slug (ej: `qombo-arganzuela`)

**4. Pégalo en tu web**

**5. ¡Ya está! 🎉**

---

## 🎬 DEMOSTRACIÓN EN VIVO

Puedes ver todos los gimnasios disponibles aquí:

**Portal completo:**
```
http://localhost:8000/public/gym/qombo-arganzuela/
```

**Solo horario embebible:**
```
http://localhost:8000/embed/qombo-arganzuela/schedule/
```

---

## 💡 TIPS PRO

### 1. Añade un título arriba
```html
<h2 style="text-align: center; margin: 40px 0 30px 0; font-size: 2rem; color: #1e293b;">
    📅 Nuestro Horario de Clases
</h2>
<iframe ...>
```

### 2. Añade un enlace al portal completo
```html
<iframe ...></iframe>

<div style="text-align: center; margin-top: 20px;">
    <a href="https://tucrm.com/public/gym/tu-slug/" 
       style="background: #667eea; color: white; padding: 12px 30px; border-radius: 8px; text-decoration: none; font-weight: bold;">
        Ver Portal Completo →
    </a>
</div>
```

### 3. Añade instrucciones para tus clientes
```html
<div style="max-width: 800px; margin: 20px auto; padding: 20px; background: #f1f5f9; border-radius: 12px;">
    <h3 style="margin-top: 0;">ℹ️ Cómo reservar:</h3>
    <ol style="color: #475569;">
        <li>Haz clic en la clase que te interesa</li>
        <li>Revisa los detalles y plazas disponibles</li>
        <li>Haz clic en "Reservar Plaza"</li>
        <li>Inicia sesión o regístrate</li>
        <li>¡Confirma tu reserva!</li>
    </ol>
</div>
<iframe ...>
```

---

**¿Todo listo?** ¡Perfecto! Si tienes dudas, no dudes en preguntar. 🚀
