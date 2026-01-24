# 🎯 Plan de Mejora: Sistema de Anuncios Estilo Mindbody

## 📱 Análisis de la Imagen de Mindbody

De la captura veo:
- **Sección "Promociones"** limpia con cards horizontales
- Cards con imagen atractiva y texto corto
- Diseño minimalista y espaciado generoso
- Sin sobrecarga visual
- Fácil scroll horizontal

## 🔍 Estado Actual del Sistema

### ✅ Lo que YA tenemos:
1. **Modelo `Advertisement`** completo con:
   - Múltiples posiciones (HERO_CAROUSEL, STICKY_FOOTER, INLINE_MIDDLE, STORIES)
   - Segmentación por gimnasios
   - Tracking de métricas (impressions, clicks, CTR)
   - Imágenes desktop/mobile
   - CTAs configurables
   - Programación de fechas

2. **API REST funcional**:
   - GET `/marketing/api/advertisements/active/`
   - POST `/marketing/api/advertisements/{id}/impression/`
   - POST `/marketing/api/advertisements/{id}/click/`

3. **Backoffice** para gestionar anuncios

### ❌ Lo que FALTA (vs software puntero):

#### 1. **Segmentación por Pantallas Específicas**
**Problema actual:** Solo tenemos posiciones visuales, no segmentación por pantalla de la app.

**Software puntero (Mindbody, Gympass, ClassPass):**
- Home/Dashboard
- Catálogo de Clases
- Detalles de Clase
- Mi Perfil
- Historial de Reservas
- Tienda/Shop
- Check-in
- Configuración

#### 2. **Targeting Avanzado**
**Problema actual:** Solo filtramos por gimnasio.

**Software puntero:**
- Por tipo de membresía
- Por historial de compras
- Por días de inactividad
- Por clases favoritas
- Por ubicación geográfica
- Por hora del día
- Por días de la semana

#### 3. **Tipos de Presentación**
**Problema actual:** Solo carousel básico.

**Software puntero:**
- **Stories** (verticales, efímeros, fullscreen)
- **Cards horizontales** (como Mindbody en la imagen)
- **Banner sticky** (no invasivo)
- **Overlay modal** (importante, one-time)
- **Inline cards** (entre contenido)
- **Push notifications** vinculadas

#### 4. **A/B Testing**
- Crear variantes de un mismo anuncio
- Medir cuál convierte mejor
- Rotación inteligente

#### 5. **Smart Scheduling**
- Mostrar anuncios de clases matutinas solo en la mañana
- Promociones de fin de semana solo jueves-domingo
- Ofertas de última hora

#### 6. **Frecuencia y Límites**
- No mostrar el mismo anuncio más de X veces
- Cooldown entre anuncios
- Prioridad dinámica según engagement

---

## 🎨 Propuesta de Mejora - FASE 1: Pantallas

### 1. Agregar campo `target_screens` al modelo

```python
class Advertisement(models.Model):
    class ScreenType(models.TextChoices):
        ALL = 'ALL', _('Todas las Pantallas')
        HOME = 'HOME', _('Inicio/Dashboard')
        CLASS_CATALOG = 'CLASS_CATALOG', _('Catálogo de Clases')
        CLASS_DETAIL = 'CLASS_DETAIL', _('Detalle de Clase')
        PROFILE = 'PROFILE', _('Mi Perfil')
        BOOKINGS = 'BOOKINGS', _('Mis Reservas')
        SHOP = 'SHOP', _('Tienda')
        CHECKIN = 'CHECKIN', _('Check-in')
        SETTINGS = 'SETTINGS', _('Configuración')
    
    # NUEVO CAMPO
    target_screens = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de pantallas donde mostrar. Vacío = todas"
    )
```

### 2. Mejorar el API

```python
# Query actualizado
@login_required
def api_get_active_advertisements(request):
    screen = request.GET.get('screen', 'HOME')  # NUEVO
    position = request.GET.get('position', None)
    
    ads_query = Advertisement.objects.filter(
        # ... filtros existentes ...
    )
    
    # NUEVO: Filtrar por pantalla
    ads_query = ads_query.filter(
        Q(target_screens=[]) | 
        Q(target_screens__contains=[screen])
    )
```

### 3. En Flutter

```dart
// Llamar desde cada pantalla
class HomeScreen extends StatelessWidget {
  Future<List<Advertisement>> _loadAds() {
    return AdService.getActiveAds(
      screen: 'HOME',
      position: 'HERO_CAROUSEL'
    );
  }
}

class ClassCatalogScreen extends StatelessWidget {
  Future<List<Advertisement>> _loadAds() {
    return AdService.getActiveAds(
      screen: 'CLASS_CATALOG',
      position: 'INLINE_MIDDLE'
    );
  }
}
```

---

## 🎯 Propuesta de Mejora - FASE 2: Diseño Limpio

### Componentes de Flutter Estilo Mindbody

#### 1. **PromoCard** (Horizontal Scrollable)
```dart
class PromoCard extends StatelessWidget {
  final Advertisement ad;
  
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 280,
      margin: EdgeInsets.only(right: 16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 12,
            offset: Offset(0, 4),
          )
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Stack(
          children: [
            // Imagen
            CachedNetworkImage(
              imageUrl: ad.imageUrl,
              height: 160,
              width: double.infinity,
              fit: BoxFit.cover,
            ),
            // Gradiente overlay
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: Container(
                padding: EdgeInsets.all(16),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.transparent,
                      Colors.black.withOpacity(0.7),
                    ],
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      ad.title,
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    if (ad.cta != null)
                      SizedBox(height: 8),
                      ElevatedButton(
                        onPressed: () => _handleCTA(ad),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.white,
                          foregroundColor: Colors.black,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(20),
                          ),
                          padding: EdgeInsets.symmetric(
                            horizontal: 20,
                            vertical: 10,
                          ),
                        ),
                        child: Text(ad.cta!.text),
                      ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

#### 2. **PromoSection** (Container con título)
```dart
class PromoSection extends StatelessWidget {
  final List<Advertisement> ads;
  
  @override
  Widget build(BuildContext context) {
    if (ads.isEmpty) return SizedBox.shrink();
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          child: Text(
            'Promociones',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
            ),
          ),
        ),
        SizedBox(
          height: 200,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            padding: EdgeInsets.symmetric(horizontal: 20),
            itemCount: ads.length,
            itemBuilder: (context, index) {
              return PromoCard(ad: ads[index]);
            },
          ),
        ),
      ],
    );
  }
}
```

---

## 📋 Recomendaciones de Software Puntero

### **Mindbody** (Líder del sector)
✅ Stories efímeros en Home  
✅ Cards horizontales de promociones  
✅ Banner sticky no invasivo  
✅ Segmentación por tipo de cliente  
✅ Deep linking a clases específicas  

### **ClassPass**
✅ Notificaciones push vinculadas a anuncios  
✅ Countdown timers en ofertas limitadas  
✅ Badges "NUEVO" o "POPULAR"  
✅ Favoritos guardados  

### **Gympass**
✅ Carrusel automático con dots  
✅ Filtros por tipo de actividad  
✅ Anuncios contextuales (mostrar yoga si reservaste yoga)  

### **Wellhub**
✅ Microanimaciones suaves  
✅ Skeleton loaders mientras carga  
✅ Placeholder si no hay anuncios  

---

## 🚀 Plan de Implementación

### **Semana 1: Backend**
1. Agregar campo `target_screens` al modelo
2. Crear migración
3. Actualizar API para filtrar por pantalla
4. Actualizar formulario de backoffice

### **Semana 2: Flutter - Home**
1. Crear `PromoCard` widget
2. Crear `PromoSection` widget
3. Integrar en HomeScreen
4. Tracking de impressions

### **Semana 3: Flutter - Otras Pantallas**
1. Class Catalog
2. Profile
3. Shop
4. Configurar por pantalla

### **Semana 4: Polish**
1. Animaciones
2. Skeleton loaders
3. Error handling
4. Analytics dashboard

---

## 💡 Consejo Final

**Software puntero = Menos es más**
- 3-4 anuncios máximo por pantalla
- Rotación inteligente
- No interrumpir la experiencia del usuario
- Dar valor, no spam

¿Empezamos por agregar el campo `target_screens` al modelo?
