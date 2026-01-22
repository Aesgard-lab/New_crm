# 🎯 Guía Rápida: Sistema de Anuncios

## ¿Qué se ha implementado?

Un sistema completo de anuncios publicitarios para la app móvil que permite:
- Mostrar banners promocionales en diferentes pantallas
- Segmentar anuncios según la pantalla de la app
- Trackear impresiones y clicks automáticamente
- Diseño limpio inspirado en Mindbody

## 🖼️ ¿Dónde se ven los anuncios?

Los anuncios aparecen como tarjetas horizontales deslizables en:

1. **Pantalla Principal (HOME)**
   - Sección "Promociones"
   - Debajo de las estadísticas del usuario

2. **Catálogo de Clases (SCHEDULE)**
   - Sección "Ofertas Especiales"
   - Al inicio del listado de clases

3. **Mi Perfil (PROFILE)**
   - Después de las estadísticas personales

4. **Tienda (SHOP)**
   - Sección "Promociones Exclusivas"
   - En el tab de Planes

## 📱 ¿Cómo se ven?

```
┌─────────────────────────────────────┐
│  Promociones                        │
├─────────────────────────────────────┤
│                                     │
│  ┌───────┐  ┌───────┐  ┌───────┐  │
│  │ IMG 1 │  │ IMG 2 │  │ IMG 3 │  │ ← Scroll horizontal
│  │       │  │       │  │       │  │
│  │ [CTA] │  │ [CTA] │  │ [CTA] │  │
│  └───────┘  └───────┘  └───────┘  │
│                                     │
└─────────────────────────────────────┘
```

## ✨ Características

- **Scroll horizontal** suave
- **Botones CTA** flotantes (ej: "¡Reserva Ahora!")
- **Imágenes atractivas** con gradiente
- **Tracking automático** de vistas y clicks

## 🎯 ¿Cómo crear un anuncio?

### Paso 1: Ir al Backoffice
Navega a: **Marketing → Anuncios Publicitarios → Crear Anuncio**

URL: `http://127.0.0.1:8000/marketing/advertisements/create/`

### Paso 2: Completar el formulario

**Información Básica:**
- **Título**: "Black Friday 50% OFF" (interno, no se ve en app)
- **Posición**: Hero Carousel (recomendado)
- **Tipo**: Promoción Interna

**Multimedia:**
- **Imagen Desktop**: Subir imagen 1080x600px ⭐
- **Imagen Mobile**: Opcional (si no, usa desktop)

**Call to Action:**
- **Texto CTA**: "¡Aprovecha Ahora!"
- **Acción**: Ver Catálogo / Reservar Clase / URL Externa
- **URL/Parámetro**: Según la acción

**Segmentación:**
- **Pantallas donde mostrar**: Marcar checkboxes
  - ☑️ Inicio/Dashboard → Aparece en HOME
  - ☑️ Tienda → Aparece en SHOP
  - ☐ Catálogo de Clases
  - ☐ Mi Perfil
  - etc.
- **Dejar vacío** = Se muestra en TODAS las pantallas

**Programación:**
- **Fecha Inicio**: Ahora
- **Fecha Fin**: Opcional (vacío = indefinido)
- **Prioridad**: 1 (menor = se muestra primero)
- **Duración**: 5 segundos (en carrusel)

**Configuración:**
- ☑️ **Activo**: Para que se muestre

### Paso 3: Guardar y Verificar

1. Click en "Guardar"
2. Ir a la app Flutter
3. Navegar a la pantalla seleccionada (ej: HOME)
4. Ver el anuncio en la sección "Promociones"

## 📊 Ver Estadísticas

En el listado de anuncios verás:
- **Impresiones**: Cuántas veces se vio
- **Clicks**: Cuántos clicks en el CTA
- **CTR**: Porcentaje de clicks (clicks/impresiones × 100)

## 🎨 Recomendaciones de Diseño

### Tamaños de Imagen
- **Horizontal**: 1080x600px (ideal para Hero Carousel)
- **Vertical**: 1080x1920px (para Stories)
- **Cuadrada**: 1080x1080px

### Contenido Visual
- ✅ Imágenes llamativas y de alta calidad
- ✅ Texto legible (no mucho texto en la imagen)
- ✅ Colores acordes a la marca
- ❌ Evitar imágenes pixeladas
- ❌ Evitar texto muy pequeño

### Call to Action
- ✅ Corto y directo: "Reserva Ya", "Ver Más", "Aprovecha"
- ✅ Acción clara: Qué va a pasar al hacer click
- ❌ Evitar CTAs largos: "Click aquí para ver más información"

## 🔄 Flujo Completo de Uso

```
1. Crear Anuncio en Backoffice
   ↓
2. Subir Imagen (1080x600px)
   ↓
3. Configurar CTA y Pantallas
   ↓
4. Activar Anuncio
   ↓
5. Usuario abre app Flutter
   ↓
6. Anuncio aparece en pantalla seleccionada
   ↓
7. Se trackea impresión automáticamente
   ↓
8. Usuario hace click en CTA
   ↓
9. Se trackea click + ejecuta acción
   ↓
10. Ver estadísticas en backoffice
```

## 🚀 Ejemplos de Uso

### Ejemplo 1: Promoción de Clase Nueva
```
Título: [DEMO] Nueva Clase de Yoga
Pantallas: ☑️ Inicio  ☑️ Catálogo de Clases
CTA: "Reserva tu Plaza"
Acción: Reservar Clase
URL: ID de la clase
```

### Ejemplo 2: Oferta en Tienda
```
Título: [DEMO] Black Friday 50% OFF
Pantallas: ☑️ Inicio  ☑️ Tienda
CTA: "¡Aprovecha Ahora!"
Acción: Ver Catálogo
```

### Ejemplo 3: Contenido Educativo
```
Título: [DEMO] Reto 30 Días
Pantallas: ☑️ Inicio  ☑️ Mi Perfil
CTA: "Unirse al Reto"
Acción: URL Externa
URL: https://ejemplo.com/reto
```

## 💡 Tips Pro

1. **Prioridad**: Usa números secuenciales (1, 2, 3...) para controlar el orden
2. **Fechas**: Programa anuncios estacionales con fecha de fin
3. **Testing**: Crea el anuncio inactivo, revisa cómo se ve, luego activa
4. **Segmentación**: Usa diferentes anuncios para diferentes pantallas
5. **A/B Testing**: Crea variantes y compara CTR

## ⚠️ Notas Importantes

- Los anuncios SIN imagen NO se mostrarán en la app
- Las fechas de inicio/fin se respetan automáticamente
- Los anuncios inactivos no aparecen aunque estén en el rango de fechas
- El tracking de impresiones se registra una vez por sesión de pantalla

## 📞 ¿Necesitas Ayuda?

- Ver ejemplos creados: Listado de Anuncios (filtrar por "[DEMO]")
- Documentación técnica: `ADVERTISEMENT_SYSTEM_COMPLETE.md`
- Implementación Flutter: `FLUTTER_ADVERTISEMENTS_IMPLEMENTATION.md`
