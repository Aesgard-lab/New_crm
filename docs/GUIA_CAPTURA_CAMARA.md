# 📸 Guía de Captura de Fotos con Cámara

## Descripción
Esta funcionalidad permite capturar fotos de clientes directamente usando la cámara web o dispositivo móvil sin necesidad de subir archivos manualmente.

## Características
✅ **Captura en tiempo real** - Usa la cámara de tu dispositivo
✅ **Carga alternativa** - También puedes subir fotos existentes
✅ **Vista previa** - Ve la foto antes de guardar
✅ **Múltiples dispositivos** - Funciona en PC, tablet y móvil
✅ **Controles intuitivos** - Interfaz fácil de usar
✅ **Cierre rápido** - Presiona ESC para cerrar

## Cómo Usar

### 1. Abrir la Cámara
- Ve a **Crear Cliente** o **Editar Cliente**
- Haz clic en el botón **"📸 Capturar con Cámara"**

### 2. Capturar Foto
- Haz clic en **"Iniciar Cámara"**
- El navegador pedirá permiso para usar la cámara (✅ Acepta)
- Posiciónate frente a la cámara
- Haz clic en **"Capturar Foto"**

### 3. Subir Foto Existente (Alternativa)
- Haz clic en la pestaña **"📁 Subir Foto"**
- Selecciona una foto de tu dispositivo
- La foto se mostrará en preview

### 4. Guardar
- Verifica que la foto se vea correcta
- Haz clic en **"💾 Guardar Foto"**
- La foto se asignará automáticamente al cliente

## Requisitos

### Navegador Compatible
- **Chrome 60+** ✅
- **Firefox 55+** ✅
- **Safari 11+** ✅
- **Edge 79+** ✅
- **Opera 47+** ✅

### Permisos Necesarios
El navegador pedirá permiso para usar la cámara. **DEBES ACEPTAR** para que funcione.

## Resolución de Problemas

### "Permiso denegado"
1. Verifica que hayas aceptado el permiso de cámara
2. En Chrome: Configuración > Privacidad > Cámara > Permiso para el sitio
3. En Firefox: Preferencias > Privacidad > Permisos

### "No funciona en mi móvil"
- Algunos navegadores móviles requieren HTTPS (no funciona en localhost con HTTP)
- Prueba con:
  - Chrome (Android)
  - Safari (iOS)
  - Firefox (Android)

### "Imagen borrosa o de lado"
- Limpia la lente de tu cámara
- Asegúrate de tener buena iluminación
- En algunos móviles, gira el dispositivo para mejor enfoque

### "¿Dónde se guardan las fotos?"
Las fotos se guardan en la carpeta `/media/clients/photos/` del servidor.

## Consejos

📷 **Para mejores fotos:**
1. Asegúrate de buena iluminación (luz natural o LED)
2. Toma la foto de frente, centrado
3. La foto debe ocupar ~60% del frame de cámara
4. Evita contraluz (luz detrás de la persona)

🎯 **Requisitos comunes de foto de perfil:**
- Foto clara de frente
- Fondo simple o neutral
- Expresión natural
- Buena iluminación facial

## Compatibilidad por Dispositivo

| Dispositivo | Navegador | Estado |
|---|---|---|
| PC Windows | Chrome | ✅ Funciona perfecto |
| PC Windows | Firefox | ✅ Funciona perfecto |
| PC Mac | Safari | ✅ Funciona perfecto |
| PC Mac | Chrome | ✅ Funciona perfecto |
| Tablet iPad | Safari | ✅ Funciona (cámara frontal) |
| Tablet Android | Chrome | ✅ Funciona (cámara frontal) |
| Móvil iPhone | Safari | ✅ Funciona |
| Móvil Android | Chrome | ✅ Funciona |

## Especificaciones Técnicas

- **Resolución capturada:** Hasta 1280x720px
- **Formato guardado:** JPEG (95% calidad)
- **Tamaño máximo:** ~200KB por foto
- **Compatibilidad:** WebRTC (estándar web)

## Preguntas Frecuentes

**P: ¿Se puede cambiar la foto después?**
R: Sí, edita el cliente y sube una nueva foto.

**P: ¿Se pueden capturar múltiples fotos?**
R: Actualmente se guarda la última capturada. Puedes subir otra foto después.

**P: ¿Qué pasa si no doy permiso de cámara?**
R: Sigue siendo opcional. Puedes subir fotos manualmente desde tu dispositivo.

**P: ¿Funciona sin conexión a internet?**
R: La captura sí funciona, pero necesitas internet para guardar.

## Mejoras Futuras
- [ ] Filtros y ajustes de brillo/contraste
- [ ] Captura automática detectando rostro
- [ ] Recorte automático de foto
- [ ] Galería de fotos por cliente
