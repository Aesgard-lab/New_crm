# Reconocimiento Facial para Check-in

## Descripción

Este módulo permite a los gimnasios utilizar reconocimiento facial como método alternativo de check-in para sus clientes. Funciona como complemento al sistema de QR existente.

## Requisitos

### Hardware
- **Tablet o teléfono** con cámara frontal (mínimo 720p recomendado)
- Conexión a internet estable

### Software
```bash
pip install face_recognition dlib
```

> **Nota**: La librería `face_recognition` requiere `dlib` que puede tardar en compilarse. En Windows, puede ser necesario instalar Visual Studio Build Tools.

## Cómo funciona

1. **Registro**: El cliente se toma una foto desde su móvil o en recepción
2. **Procesamiento**: La imagen se convierte en un "encoding" de 128 números únicos
3. **Almacenamiento**: Solo se guarda el encoding, NO la foto (cumplimiento RGPD)
4. **Verificación**: Al llegar, la cámara captura la cara y compara con los encodings guardados
5. **Check-in automático**: Si coincide (>60% confianza por defecto), se hace el check-in

## Configuración

### 1. Panel de Administración

Accede a: **Panel → Reconocimiento Facial** (en el menú lateral)

Opciones disponibles:
- **Activar/Desactivar**: Toggle principal del sistema
- **Métodos de check-in**: QR, Facial, Manual (puedes combinarlos)
- **Umbral de confianza**: 0.3 (permisivo) a 0.9 (estricto)
- **Modo kiosko**: Para tablets en la entrada

### 2. Modo Kiosko (Tablet)

URL para el kiosko: `/face-recognition/kiosk/`

Características:
- Pantalla completa optimizada para tablets
- Detección automática continua
- Mensaje de bienvenida personalizado
- Opción de QR como fallback

### 3. Registro de Clientes

Los clientes pueden registrar su rostro desde:
- **Portal de clientes**: Perfil → Configurar acceso facial
- **Recepción**: El staff puede registrar desde la configuración

## API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/face-recognition/api/status/` | GET | Estado del sistema |
| `/face-recognition/api/register/` | POST | Registrar rostro |
| `/face-recognition/api/verify/` | POST | Verificar rostro |
| `/face-recognition/api/delete/` | DELETE | Eliminar datos (RGPD) |
| `/face-recognition/api/stats/` | GET | Estadísticas |
| `/face-recognition/api/kiosk/<gym_id>/verify/` | POST | Verificación en kiosko |

## Integración con Actividades

El reconocimiento facial se integra automáticamente con:
- Check-in de clases grupales
- Reservas de actividades
- Control de acceso general

Cuando un cliente es reconocido, el sistema:
1. Busca reservas activas para hoy
2. Hace check-in automático si hay una sesión próxima
3. Registra el método de check-in como "FACE"

## Privacidad y RGPD

El sistema cumple con el RGPD:
- **Consentimiento explícito** requerido para registro
- **No se almacenan fotos**, solo encodings matemáticos
- **Derecho al olvido**: Los clientes pueden eliminar sus datos en cualquier momento
- **Logs de auditoría** para todas las operaciones

## Troubleshooting

### La librería no se instala
```bash
# En Windows, primero instala:
pip install cmake
pip install dlib
pip install face_recognition
```

### La detección es muy lenta
- Asegúrate de usar imágenes de máximo 720p
- Considera usar GPU con CUDA si está disponible

### No reconoce bien
- Aumenta el umbral de confianza a 0.5-0.7
- Asegúrate de buena iluminación
- Pide a los clientes registrarse sin gafas de sol

## Costes

- **Librería**: Gratuita (open source)
- **Hardware**: Tablet económica ~150€
- **Sin costes recurrentes** (todo se procesa localmente)

## Archivos del módulo

```
facial_checkin/
├── models.py          # Modelos de datos
├── services.py        # Lógica de reconocimiento
├── api.py             # Endpoints REST
├── views.py           # Vistas web
├── urls.py            # Configuración de URLs
├── admin.py           # Admin Django
└── migrations/        # Migraciones DB

templates/face_recognition/
├── settings.html      # Panel de configuración
├── register.html      # Registro de clientes
├── kiosk.html         # Pantalla de kiosko
├── kiosk_setup.html   # Kiosko no configurado
└── kiosk_disabled.html # Kiosko deshabilitado
```
