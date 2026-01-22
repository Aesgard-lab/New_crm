# Sistema de Anuncios Implementado - Flutter App

## ✅ Implementación Completada

Se ha implementado exitosamente el sistema de anuncios publicitarios en la aplicación Flutter con segmentación por pantalla, inspirado en el diseño limpio de Mindbody.

## 📂 Archivos Creados/Modificados

### Modelo
- **`mobile_app/lib/models/advertisement.dart`**
  - Clase `Advertisement` con todos los campos del backend
  - Método `fromJson` para parsear respuestas de la API
  - Propiedades calculadas: `displayImage`, `hasCta`

### Servicio API
- **`mobile_app/lib/api/api_service.dart`**
  - `getAdvertisements(screen, position)` - Obtener anuncios filtrados
  - `trackAdvertisementImpression(adId)` - Tracking de impresiones
  - `trackAdvertisementClick(adId)` - Tracking de clicks

### Widgets
- **`mobile_app/lib/widgets/promo_card.dart`**
  - Tarjeta individual de anuncio
  - Diseño horizontal scrollable (320x180px)
  - Imagen con gradiente overlay
  - Botón CTA flotante estilo Mindbody
  - Tracking automático de clicks

- **`mobile_app/lib/widgets/promo_section.dart`**
  - Sección completa de anuncios
  - Carga automática según pantalla (`screen` parameter)
  - ListView horizontal con múltiples PromoCards
  - Tracking automático de impresiones
  - Manejo de estados: loading, empty, error
  - Gestión de acciones CTA (BOOK_CLASS, VIEW_CATALOG, EXTERNAL_URL, VIEW_PROMO)

### Integración en Pantallas
Se integró `PromoSection` en las siguientes pantallas:

1. **`home_screen.dart`**
   - Screen: `'HOME'`
   - Position: `'HERO_CAROUSEL'`
   - Ubicación: Debajo de las estadísticas, antes de Gamificación

2. **`schedule_screen.dart`**
   - Screen: `'CLASS_CATALOG'`
   - Título: "Ofertas Especiales"
   - Ubicación: Al inicio del listado de clases

3. **`profile_screen.dart`**
   - Screen: `'PROFILE'`
   - Ubicación: Después de las estadísticas

4. **`shop_screen.dart`**
   - Screen: `'SHOP'`
   - Título: "Promociones Exclusivas"
   - Ubicación: Al inicio del tab de Planes

## 🎨 Diseño

### Estilo Visual (Inspirado en Mindbody)
- **Tarjetas**: 320x180px, border-radius 16px
- **Sombras**: Sutiles, elevación mínima
- **Gradiente**: Overlay negro transparente a opaco (0 → 60%)
- **Botones CTA**: 
  - Fondo blanco
  - Padding: 20px horizontal, 12px vertical
  - Border-radius: 24px (pill shape)
  - Icono de flecha derecha
  - Sombra suave

### Scroll Horizontal
- Padding lateral: 20px
- Spacing entre cards: 16px
- Snap behavior: Scroll fluido
- Indicador de más contenido: Tarjeta parcialmente visible

## 🔌 API Integration

### Endpoints Utilizados
```dart
GET /marketing/api/advertisements/active/?screen={SCREEN}&position={POSITION}
POST /marketing/api/advertisements/{id}/impression/
POST /marketing/api/advertisements/{id}/click/
```

### Screen Types
- `HOME` - Pantalla principal
- `CLASS_CATALOG` - Listado de clases
- `CLASS_DETAIL` - Detalle de clase
- `PROFILE` - Perfil del usuario
- `BOOKINGS` - Mis reservas
- `SHOP` - Tienda
- `CHECKIN` - Check-in
- `SETTINGS` - Configuración

### CTA Actions
- `BOOK_CLASS` - Reservar clase específica
- `VIEW_CATALOG` - Ver catálogo de clases
- `EXTERNAL_URL` - Abrir URL externa
- `VIEW_PROMO` - Ver detalle de promoción

## 📊 Analytics

### Tracking Automático
- **Impresiones**: Se registran automáticamente cuando los anuncios se cargan en pantalla
- **Clicks**: Se registran cuando el usuario toca la tarjeta o el botón CTA

### Deduplicación
- Solo se trackea una impresión por carga de pantalla
- Flag `_impressionsTracked` evita duplicados

## 🚀 Próximos Pasos Sugeridos

1. **Crear anuncio de ejemplo** en el backoffice Django
2. **Probar en emulador/dispositivo** Flutter
3. **Implementar navegación** para CTA actions
4. **Añadir PromoSection** en pantallas restantes (BOOKINGS, CHECKIN, SETTINGS)
5. **Configurar imágenes** optimizadas (1080x600px desktop, mobile optional)
6. **Testear analytics** en el dashboard del backoffice

## 📝 Notas de Uso

### Para crear un anuncio:
1. Ir a `/marketing/advertisements/create/`
2. Subir imagen (recomendado 1080x600px)
3. Configurar CTA (texto + acción + URL)
4. Seleccionar pantallas destino (checkboxes)
5. Configurar prioridad y duración
6. Activar anuncio

### Ejemplo de uso en código:
```dart
// Agregar en cualquier pantalla
const PromoSection(
  screen: 'HOME',  // O cualquier ScreenType
  position: 'HERO_CAROUSEL',  // Opcional
  title: 'Promociones',  // Opcional
  padding: EdgeInsets.symmetric(vertical: 16),  // Opcional
)
```

## 🎯 Resultado Final

Sistema completo de anuncios publicitarios con:
- ✅ Segmentación por pantalla
- ✅ Diseño limpio estilo Mindbody
- ✅ Tracking de analytics
- ✅ Manejo de CTAs
- ✅ Integración en 4 pantallas principales
- ✅ Backend completamente funcional
