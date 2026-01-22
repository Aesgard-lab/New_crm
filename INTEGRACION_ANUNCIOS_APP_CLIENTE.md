# 📱 Integración de Anuncios en App del Cliente

## ✅ Completado

### 1. **Selección de Gimnasios** ✅
El campo `target_gyms` ya usa `SelectMultiple`, permitiendo:
- **Todos**: Dejar campo vacío
- **Algunos**: Seleccionar múltiples con Ctrl+Click
- **Uno solo**: Seleccionar solo uno

### 2. **Permisos Añadidos** ✅
Añadidos a `staff/perms.py`:
```python
"Marketing": [
    ...
    ("view_advertisement", "Ver Anuncios en App"),
    ("add_advertisement", "Crear Anuncios en App"),
    ("change_advertisement", "Editar Anuncios en App"),
    ("delete_advertisement", "Eliminar Anuncios en App"),
    ...
]
```

**Aplicar permisos a roles:**
1. Ir a: `Configuración > Roles y Permisos`
2. Editar rol (ej: Manager, Owner)
3. Marcar los permisos de "Marketing > Anuncios en App"
4. Guardar

### 3. **Anuncio de Prueba Creado** ✅
```
ID: 1
Título: Black Friday 50% OFF - Prueba
Posición: Hero Carousel (Home)
CTA: ¡Reserva Ahora!
Métricas: 451 vistas, 36 clicks, 7.98% CTR
```

**Ver en:**
- **Backoffice**: http://127.0.0.1:8000/marketing/advertisements/
- **Editar**: http://127.0.0.1:8000/marketing/advertisements/1/edit/

### 4. **API REST Implementada** ✅
4 endpoints funcionando:
- `GET /marketing/api/advertisements/active/` - Obtener anuncios activos
- `POST /marketing/api/advertisements/{id}/impression/` - Registrar impresión
- `POST /marketing/api/advertisements/{id}/click/` - Registrar click
- `GET /marketing/api/advertisements/positions/` - Listar posiciones

### 5. **Vista Demo Creada** ✅
**Ver demo visual**: http://127.0.0.1:8000/marketing/demo/

Incluye:
- 🎠 Hero Carousel con anuncios
- 📍 Banner footer sticky
- 📊 Tracking de clicks e impresiones en tiempo real
- ✨ Animaciones y transiciones

---

## 🔌 API para App del Cliente

### ✅ Endpoints Implementados y Probados

#### 1. **GET /marketing/api/advertisements/active/**
Obtener anuncios activos para el cliente actual

**Request:**
```http
GET /marketing/api/advertisements/active/?position=HERO_CAROUSEL
Authorization: Bearer <token>
```

**Query Parameters:**
- `position` (opcional): Filtrar por posición
  - `HERO_CAROUSEL` - Carrusel principal del home
  - `STICKY_FOOTER` - Banner inferior fijo
  - `INLINE_MIDDLE` - Banner intermedio
  - `STORIES` - Stories verticales

**Response (200 OK):**
```json
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "title": "Black Friday 50% OFF - Prueba",
      "position": "HERO_CAROUSEL",
      "ad_type": "INTERNAL_PROMO",
      "image_url": "http://127.0.0.1:8000/media/ads/desktop.jpg",
      "image_mobile_url": "http://127.0.0.1:8000/media/ads/mobile.jpg",
      "video_url": null,
      "cta": {
        "text": "¡Reserva Ahora!",
        "action": "BOOK_CLASS",
        "url": ""
      },
      "priority": 1,
      "duration_seconds": 5,
      "is_collapsible": true,
      "background_color": "#ffffff"
    }
  ]
}
```

#### 2. **POST /marketing/api/advertisements/{id}/impression/**
Registrar que el usuario vio el anuncio

**Request:**
```http
POST /marketing/api/advertisements/1/impression/
Authorization: Bearer <token>
Content-Type: application/json

{}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Impresión registrada"
}
```

**Efecto:** Incrementa el contador `impressions` del anuncio.

#### 3. **POST /marketing/api/advertisements/{id}/click/**
Registrar que el usuario hizo click en el CTA

**Request:**
```http
POST /marketing/api/advertisements/1/click/
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "BOOK_CLASS"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Click registrado",
  "redirect_to": "/portal/activities/",
  "action": "BOOK_CLASS"
}
```

**Efectos:**
- Incrementa el contador `clicks` del anuncio
- Actualiza automáticamente el **CTR** (Click-Through Rate)
- Retorna la URL de redirección según la acción

**Acciones CTA disponibles:**
- `BOOK_CLASS` → `/portal/activities/`
- `VIEW_CATALOG` → `/portal/catalog/`
- `VIEW_MEMBERSHIPS` → `/portal/memberships/`
- `VIEW_SERVICES` → `/portal/services/`
- `VIEW_PROFILE` → `/portal/profile/`
- `CONTACT_US` → `/portal/contact/`
- `EXTERNAL_URL` → URL personalizada del anuncio

#### 4. **GET /marketing/api/advertisements/positions/**
Obtener lista de posiciones disponibles

**Request:**
```http
GET /marketing/api/advertisements/positions/
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "positions": [
    {"value": "HERO_CAROUSEL", "label": "Hero Carousel (Home)"},
    {"value": "STICKY_FOOTER", "label": "Banner Inferior Fijo"},
    {"value": "INLINE_MIDDLE", "label": "Banner Intermedio"},
    {"value": "STORIES", "label": "Stories Verticales"}
  ]
}
```

---

### 🔐 Autenticación

Los endpoints requieren que el usuario esté autenticado:
```python
@login_required  # Django decorator
```

El cliente debe tener un objeto `Client` asociado al `User`.

---

### 📊 Analytics Automáticos

La API registra automáticamente:
- **Impresiones**: Cada vez que se muestra el anuncio
- **Clicks**: Cada vez que se hace click en el CTA
- **CTR**: Se calcula automáticamente como `(clicks / impressions) * 100`

Ver las métricas en el backoffice:
👉 http://127.0.0.1:8000/marketing/advertisements/

---

### ✅ Pruebas Realizadas

```bash
python test_advertisement_api.py
```

**Resultados:**
```
✅ Cliente encontrado: Demo Cliente (Qombo Arganzuela)
✅ GET /marketing/api/advertisements/active/ → 200 OK (1 anuncio)
✅ GET con filtro ?position=HERO_CAROUSEL → 1 anuncio
✅ POST impression → 450 → 451 impresiones
✅ POST click → 35 → 36 clicks (CTR: 7.98%)
✅ GET positions → 4 posiciones disponibles
```

---

## 📱 Componentes Frontend Recomendados

### 1. Hero Carousel Component (React/Vue/Flutter)

```javascript
// HeroCarousel.jsx
import { Swiper, SwiperSlide } from 'swiper/react'
import { Autoplay, Pagination } from 'swiper/modules'
import { useState, useEffect } from 'react'

export default function HeroCarousel() {
  const [ads, setAds] = useState([])
  
  useEffect(() => {
    fetchAds()
  }, [])
  
  const fetchAds = async () => {
    try {
      const response = await fetch('/marketing/api/advertisements/active/?position=HERO_CAROUSEL', {
        headers: { 
          'Authorization': `Bearer ${localStorage.getItem('token')}` 
        }
      })
      const data = await response.json()
      setAds(data.results)
      
      // Track impressions
      data.results.forEach(ad => {
        trackImpression(ad.id)
      })
    } catch (error) {
      console.error('Error fetching ads:', error)
    }
  }
  
  const trackImpression = async (adId) => {
    try {
      await fetch(`/marketing/api/advertisements/${adId}/impression/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      })
    } catch (error) {
      console.error('Error tracking impression:', error)
    }
  }
  
  const handleCTA = async (ad) => {
    // Track click
    try {
      const response = await fetch(`/marketing/api/advertisements/${ad.id}/click/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: ad.cta.action })
      })
      const data = await response.json()
      
      // Redirect
      if (data.redirect_to) {
        if (ad.cta.action === 'EXTERNAL_URL') {
          window.open(data.redirect_to, '_blank')
        } else {
          window.location.href = data.redirect_to
        }
      }
    } catch (error) {
      console.error('Error tracking click:', error)
    }
  }
  
  if (ads.length === 0) return null
  
  return (
    <Swiper
      modules={[Autoplay, Pagination]}
      autoplay={{ delay: ads[0]?.duration_seconds * 1000 || 5000 }}
      pagination={{ clickable: true }}
      loop={true}
      className="hero-carousel"
    >
      {ads.map(ad => (
        <SwiperSlide key={ad.id}>
          <div className="relative">
            <img 
              src={ad.image_mobile_url || ad.image_url} 
              alt={ad.title}
              className="w-full h-64 object-cover"
            />
            {ad.cta && (
              <button 
                onClick={() => handleCTA(ad)}
                className="absolute bottom-4 right-4 bg-purple-600 text-white px-6 py-3 rounded-lg font-bold shadow-lg hover:bg-purple-700 transition"
              >
                {ad.cta.text}
              </button>
            )}
          </div>
        </SwiperSlide>
      ))}
    </Swiper>
  )
}
```

### 2. Sticky Footer Banner

```javascript
// StickyFooterBanner.jsx
import { useState, useEffect } from 'react'

export default function StickyFooterBanner() {
  const [ad, setAd] = useState(null)
  const [collapsed, setCollapsed] = useState(false)
  
  useEffect(() => {
    fetchAd()
  }, [])
  
  const fetchAd = async () => {
    try {
      const response = await fetch('/marketing/api/advertisements/active/?position=STICKY_FOOTER', {
        headers: { 
          'Authorization': `Bearer ${localStorage.getItem('token')}` 
        }
      })
      const data = await response.json()
      
      if (data.results.length > 0) {
        const banner = data.results[0]
        setAd(banner)
        trackImpression(banner.id)
      }
    } catch (error) {
      console.error('Error fetching banner:', error)
    }
  }
  
  const trackImpression = async (adId) => {
    try {
      await fetch(`/marketing/api/advertisements/${adId}/impression/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      })
    } catch (error) {
      console.error('Error tracking impression:', error)
    }
  }
  
  const handleCTA = async (ad) => {
    try {
      const response = await fetch(`/marketing/api/advertisements/${ad.id}/click/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: ad.cta.action })
      })
      const data = await response.json()
      
      // Redirect
      if (data.redirect_to) {
        if (ad.cta.action === 'EXTERNAL_URL') {
          window.open(data.redirect_to, '_blank')
        } else {
          window.location.href = data.redirect_to
        }
      }
    } catch (error) {
      console.error('Error tracking click:', error)
    }
  }
  
  if (!ad || collapsed) return null
  
  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white shadow-lg border-t">
      <div className="relative">
        <img 
          src={ad.image_mobile_url || ad.image_url} 
          alt={ad.title}
          className="w-full h-20 object-cover"
        />
        {ad.is_collapsible && (
          <button 
            onClick={() => setCollapsed(true)}
            className="absolute top-2 right-2 w-6 h-6 bg-black/50 rounded-full text-white flex items-center justify-center hover:bg-black/70 transition"
          >
            ✕
          </button>
        )}
        {ad.cta && (
          <button 
            onClick={() => handleCTA(ad)}
            className="absolute bottom-2 right-2 bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-bold shadow-lg hover:bg-purple-700 transition"
          >
            {ad.cta.text}
          </button>
        )}
      </div>
    </div>
  )
}
```

### 3. Advertisement Service (Reutilizable)

```javascript
// services/advertisementService.js

const API_BASE = '/marketing/api/advertisements'

export const advertisementService = {
  /**
   * Obtiene anuncios activos
   * @param {string} position - Filtro opcional por posición
   * @returns {Promise<Array>}
   */
  async getActiveAds(position = null) {
    try {
      const params = position ? `?position=${position}` : ''
      const response = await fetch(`${API_BASE}/active/${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      return data.results || []
    } catch (error) {
      console.error('Error fetching advertisements:', error)
      return []
    }
  },
  
  /**
   * Registra una impresión (el usuario vio el anuncio)
   * @param {number} adId
   */
  async trackImpression(adId) {
    try {
      await fetch(`${API_BASE}/${adId}/impression/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      })
    } catch (error) {
      console.error('Error tracking impression:', error)
    }
  },
  
  /**
   * Registra un click en el CTA y retorna la URL de redirección
   * @param {number} adId
   * @param {string} action
   * @returns {Promise<{redirect_to: string}>}
   */
  async trackClick(adId, action) {
    try {
      const response = await fetch(`${API_BASE}/${adId}/click/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error('Error tracking click:', error)
      return { redirect_to: '#' }
    }
  },
  
  /**
   * Obtiene las posiciones disponibles
   * @returns {Promise<Array>}
   */
  async getPositions() {
    try {
      const response = await fetch(`${API_BASE}/positions/`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      return data.positions || []
    } catch (error) {
      console.error('Error fetching positions:', error)
      return []
    }
  }
}

export default advertisementService
```

**Uso del service:**
```javascript
import advertisementService from '@/services/advertisementService'

// En tu componente
const ads = await advertisementService.getActiveAds('HERO_CAROUSEL')
await advertisementService.trackImpression(ad.id)
const result = await advertisementService.trackClick(ad.id, 'BOOK_CLASS')
```

---

## 🎯 Ejemplo de Implementación en Flutter

```dart
// Hero Carousel en Flutter
class HeroCarousel extends StatefulWidget {
  @override
  _HeroCarouselState createState() => _HeroCarouselState();
}

class _HeroCarouselState extends State<HeroCarousel> {
  List<Advertisement> ads = [];
  final PageController _controller = PageController();
  
  @override
  void initState() {
    super.initState();
    loadAds();
  }
  
  Future<void> loadAds() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/api/v1/advertisements/active/?position=HERO_CAROUSEL'),
      headers: {'Authorization': 'Bearer ${authService.token}'}
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      setState(() {
        ads = (data['results'] as List)
            .map((ad) => Advertisement.fromJson(ad))
            .toList();
      });
      
      // Track impressions
      for (var ad in ads) {
        trackImpression(ad.id);
      }
      
      // Auto-slide
      _startAutoSlide();
    }
  }
  
  void _startAutoSlide() {
    if (ads.isEmpty) return;
    
    Timer.periodic(Duration(seconds: ads[0].durationSeconds), (timer) {
      if (_controller.hasClients) {
        int nextPage = (_controller.page?.toInt() ?? 0) + 1;
        if (nextPage >= ads.length) nextPage = 0;
        _controller.animateToPage(
          nextPage,
          duration: Duration(milliseconds: 300),
          curve: Curves.easeInOut,
        );
      }
    });
  }
  
  @override
  Widget build(BuildContext context) {
    if (ads.isEmpty) return SizedBox.shrink();
    
    return Container(
      height: 200,
      child: PageView.builder(
        controller: _controller,
        itemCount: ads.length,
        itemBuilder: (context, index) {
          final ad = ads[index];
          return Stack(
            children: [
              Image.network(
                ad.imageMobileUrl ?? ad.imageUrl,
                width: double.infinity,
                height: 200,
                fit: BoxFit.cover,
              ),
              if (ad.cta.text != null)
                Positioned(
                  bottom: 16,
                  right: 16,
                  child: ElevatedButton(
                    onPressed: () => handleCTA(ad),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Color(0xFF9333ea),
                      padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                    ),
                    child: Text(ad.cta.text!),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
  
  void handleCTA(Advertisement ad) {
    trackClick(ad.id);
    
    switch (ad.cta.action) {
      case 'BOOK_CLASS':
        Navigator.pushNamed(context, '/classes');
        break;
      case 'VIEW_CATALOG':
        Navigator.pushNamed(context, '/catalog');
        break;
      case 'EXTERNAL_URL':
        launchUrl(Uri.parse(ad.cta.url!));
        break;
    }
  }
}
```

---

## 📊 Dashboard de Analytics (Ya Implementado)

El dashboard en el backoffice ya muestra:
- ✅ Total de anuncios
- ✅ Anuncios activos
- ✅ Impresiones totales
- ✅ Clicks totales
- ✅ CTR promedio

**Ver en:** http://127.0.0.1:8000/marketing/advertisements/

---

## 🚀 Próximos Pasos

1. **Implementar API REST** en `marketing/api.py`
2. **Crear componentes frontend** en tu app (React/Vue/Flutter)
3. **Probar tracking** de impresiones y clicks
4. **Añadir más anuncios** desde el backoffice
5. **Configurar permisos** en Roles

---

## 📸 Vista del Anuncio Creado

Accede a:
- **Lista**: http://127.0.0.1:8000/marketing/advertisements/
- **Editar**: http://127.0.0.1:8000/marketing/advertisements/1/edit/

Verás el anuncio con:
- 📢 Título: "Black Friday 50% OFF - Prueba"
- 🎯 Posición: Hero Carousel (Home)
- 🎨 Tipo: Promoción Interna
- 📱 CTA: "¡Reserva Ahora!" → Reservar Clase
- ✅ Estado: Activo
- 📊 Stats: 450 vistas, 35 clicks, 7.78% CTR
