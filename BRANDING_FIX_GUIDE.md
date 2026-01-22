
# ⚠️ Guía de Solución de Problemas: Branding e Interfaz

Este documento detalla la solución al problema recurrente donde el branding (colores corporativos) deja de funcionar en la interfaz, mostrándose botones en blanco y sin efectos hover.

## 🚨 El Problema

### Síntomas
- El botón de "Cobrar" en la barra superior aparece **totalmente blanco**.
- Los efectos **hover** (pasar el ratón por encima) en los menús laterales y textos **no funcionan**.
- El badge de recuento de clientes en el sidebar muestra código roto (ej: `request.gym...`).

### Causa Técnica
El problema se debe a cómo el motor de plantillas de Django (Jinja2-like) interpreta las etiquetas dentro de bloques `<style>`.

1.  **Formateo Automático**: Algunos editores o procesos de formateo dividen la etiqueta del template en múltiples líneas.
    *   **Incorrecto**:
        ```css
        --brand-color: {
            {
            request.gym.brand_color|default: "#0f172a"
          }
        }
        ```
    *   Los navegadores **no entienden** saltos de línea dentro de definiciones de variables CSS cuando hay basura de por medio o simplemente porque la sintaxis de Django rota no se renderiza correctamente como un valor válido de color.

2.  **Renderizado de Texto**: Etiquetas de template complejas en HTML (como el conteo de clientes) también pueden romperse si se introducen saltos de línea arbitrarios dentro de los `{{ }}`.

## 🛠️ La Solución

### 1. Arreglar `base.html` (CSS Variables)

El archivo `templates/base/base.html` define la variable raíz `--brand-color`. Esta definición **DEBE** estar en una sola línea para garantizar que Django la renderice como un string de color hexadecimal válido (ej: `#0f172a`) antes de que llegue al navegador.

**Código Correcto:**
```html
<style>
  :root {
    /* MANTENER EN UNA SOLA LÍNEA */
    --brand-color: {{ request.gym.brand_color|default:"#0f172a" }};
  }
  /* ... resto de estilos ... */
</style>
```

### 2. Arreglar `sidebar.html` (Badges)

En `templates/base/sidebar.html`, cualquier etiqueta que imprima valores directos dentro de atributos o texto visible debe estar colapsada.

**Código Correcto:**
```html
<span class="...">{{ request.gym.clients.count }}</span>
```

## 📝 Prevención

Para evitar que esto vuelva a ocurrir:
1.  **Evitar formateadores agresivos** en archivos HTML que contengan sintaxis de template de Django compleja dentro de bloques `<style>` o `<script>`.
2.  Si se usa "Format Document", **revisar siempre** el bloque `:root` en `base.html`.
3.  Mantener las interpolaciones de variables simples de Django en una sola línea siempre que sea posible.

---

**Última Corrección:** 19 de Enero de 2026
**Archivos Afectados:** `templates/base/base.html`, `templates/base/sidebar.html`
