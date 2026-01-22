# 🎯 GUÍA PARA EL STAFF DEL GIMNASIO

## 📍 DÓNDE ENCONTRAR TODO EN EL BACKOFFICE

### 1️⃣ **CONFIGURAR EL PORTAL PÚBLICO**

**Ubicación:** `Configuración → Organizations → Gimnasios → [Tu Gimnasio] → Editar`

Busca la sección **"Portal Público"** y verás:

- ✅ **Portal público habilitado** (checkbox)
- ✅ **Slug público** (tu-gimnasio-nombre) ← Este es tu identificador único
- ✅ **Permitir auto-registro** (checkbox)
- ✅ **Mostrar horario** (checkbox)
- ✅ **Mostrar precios** (checkbox)
- ✅ **Mostrar servicios** (checkbox)
- ✅ **Mostrar tienda** (checkbox)
- ✅ **Permitir embedding** (checkbox) ← Activa esto para usar el widget
- ✅ **Dominios permitidos para embedding** (textarea) ← Escribe aquí tus dominios

---

### 2️⃣ **HACER ACTIVIDADES VISIBLES ONLINE**

**Ubicación:** `Actividades → Clases → [Seleccionar Actividad] → Editar`

En el formulario de edición encontrarás:

- ✅ **Visible online** (checkbox) ← Marca esto para que aparezca en el widget

**¿Qué significa?**
- Si está marcado: La actividad aparece en el widget embebible y el portal público
- Si NO está marcado: Solo se ve en el backoffice (no es pública)

---

### 3️⃣ **HACER PLANES VISIBLES ONLINE**

**Ubicación:** `Membresías → Planes → [Seleccionar Plan] → Editar`

En el formulario encontrarás:

- ✅ **Visible online** (checkbox) ← Marca esto para que aparezca en precios
- ✅ **Orden de visualización** (número) ← Define el orden (1, 2, 3...)
- ✅ **Contrato requerido** (checkbox)
- ✅ **Imagen del plan** (opcional)

---

### 4️⃣ **CONFIGURAR CAMPOS PERSONALIZADOS DE REGISTRO**

**Ubicación:** `Clientes → Campos Personalizados → [Seleccionar Campo] → Editar`

Verás opciones como:

- ✅ **Mostrar en registro público** (checkbox) ← Activa esto para que aparezca en el formulario
- ✅ **Orden de visualización** (número)
- ✅ **Obligatorio** (checkbox)

**Ejemplos de campos:**
- ¿Cómo nos conociste?
- Objetivos de entrenamiento
- Nivel de experiencia
- Condiciones médicas

---

### 5️⃣ **CONFIGURAR MÉTODOS DE PAGO ONLINE**

**Ubicación:** `Finanzas → Métodos de Pago → [Seleccionar Método] → Editar`

Opciones importantes:

- ✅ **Activo** (checkbox)
- ✅ **Disponible para compra online** (checkbox) ← Marca esto para portal público
- ✅ **Orden de visualización** (número)
- ✅ **Pasarela de pago** (dropdown)
  - Sin pasarela (Efectivo/Manual)
  - Stripe
  - Redsys
  - PayPal

**Métodos recomendados para online:**
- Transferencia Bancaria (manual)
- Tarjeta Online (Stripe o Redsys)

---

### 6️⃣ **OBTENER EL CÓDIGO DEL WIDGET EMBEBIBLE** 🔥

**Ubicación en el Backoffice:** `Configuración → Organizations → Código del Widget`

**O accede directamente desde el navegador:**
```
http://localhost:8000/organizations/widget-code/
```

En esta página encontrarás:

✅ **Código HTML listo para copiar** (con botón de copiado rápido)
✅ **Vista previa en tiempo real** de ambos widgets
✅ **Dos estilos para elegir:**
   - Vista de Lista (recomendada) - Diseño profesional con fotos
   - Vista de Calendario - Calendario mensual estilo Google
✅ **Opciones de tema:** Claro y oscuro
✅ **Instrucciones de integración** para diferentes plataformas

**Pasos para usar el widget:**

1. Ve a la página (URL de arriba)
2. Elige el estilo que prefieras (Lista o Calendario)
3. Haz clic en el botón **"Copiar"**
4. Pega el código en tu sitio web

**El código se ve así:**
```html
<iframe 
    src="http://localhost:8000/embed/tu-gimnasio/schedule/"
    width="100%" 
    height="1200"
    frameborder="0"
    style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
</iframe>
```

---

### 7️⃣ **VER RESERVAS DE CLIENTES**

**Ubicación:** `Actividades → Reservas` o `Clientes → [Cliente] → Reservas`

Aquí verás:
- Todas las reservas realizadas desde el portal público
- Estado de cada reserva (confirmada, cancelada)
- Fecha y hora
- Cliente que reservó
- Actividad reservada

---

### 7️⃣ **VER COMPRAS DE MEMBRESÍAS**

**Ubicación:** `Membresías → Membresías Activas` o `Clientes → [Cliente] → Membresías`

Verás:
- Membresías compradas desde el portal público
- Estado (Activa, Pendiente de Pago, Pausada)
- Plan seleccionado
- Método de pago usado
- Fechas de inicio/fin

---

## 🌐 TUS URLs PERSONALIZADAS

Una vez configurado todo, tus URLs serán:

### Portal Público Completo:
```
https://tudominio.com/public/gym/TU-SLUG/
https://tudominio.com/public/gym/TU-SLUG/schedule/
https://tudominio.com/public/gym/TU-SLUG/pricing/
https://tudominio.com/public/gym/TU-SLUG/services/
https://tudominio.com/public/gym/TU-SLUG/shop/
```

### Widget Embebible (para tu web):
```
https://tudominio.com/embed/TU-SLUG/schedule/
https://tudominio.com/embed/TU-SLUG/schedule/?theme=dark
```

**Reemplaza:**
- `tudominio.com` → Tu dominio real (ej: `micrm.com`)
- `TU-SLUG` → Tu slug configurado (ej: `qombo-arganzuela`)

---

## 📋 CHECKLIST DE CONFIGURACIÓN

### Para activar el portal público:

- [ ] 1. Ir a **Configuración → Organizations → [Tu Gimnasio]**
- [ ] 2. Marcar **"Portal público habilitado"**
- [ ] 3. Verificar el **"Slug público"** (tu identificador único)
- [ ] 4. Marcar opciones deseadas:
  - [ ] Permitir auto-registro
  - [ ] Mostrar horario
  - [ ] Mostrar precios
  - [ ] Mostrar servicios
  - [ ] Permitir embedding (para widget)
- [ ] 5. Guardar cambios

### Para publicar actividades:

- [ ] 1. Ir a **Actividades → Clases**
- [ ] 2. Para cada actividad que quieras publicar:
  - [ ] Abrir la actividad
  - [ ] Marcar **"Visible online"**
  - [ ] Guardar
- [ ] 3. Verificar en el widget que aparezcan

### Para publicar planes:

- [ ] 1. Ir a **Membresías → Planes**
- [ ] 2. Para cada plan que quieras vender online:
  - [ ] Abrir el plan
  - [ ] Marcar **"Visible online"**
  - [ ] Configurar **"Orden de visualización"** (1, 2, 3...)
  - [ ] Guardar
- [ ] 3. Verificar en `/pricing/` que aparezcan

### Para configurar pagos online:

- [ ] 1. Ir a **Finanzas → Métodos de Pago**
- [ ] 2. Para cada método online:
  - [ ] Marcar **"Activo"**
  - [ ] Marcar **"Disponible para compra online"**
  - [ ] Seleccionar **pasarela** si aplica (Stripe/Redsys)
  - [ ] Guardar
- [ ] 3. Verificar en página de compra que aparezcan

---

## 🔍 CÓMO ENCONTRAR TU SLUG

Tu slug es tu identificador único en las URLs. Para encontrarlo:

1. Ve a **Configuración → Organizations → Gimnasios**
2. Haz clic en tu gimnasio
3. Busca el campo **"Slug público"**
4. Ese es tu identificador (ejemplo: `qombo-arganzuela`)

Si no tiene slug asignado, el sistema lo genera automáticamente del nombre del gimnasio.

---

## 💡 CONSEJOS RÁPIDOS

### ✅ Para que el widget funcione:
1. Portal público habilitado ✓
2. "Permitir embedding" activado ✓
3. Al menos 1 actividad con "Visible online" ✓
4. Horarios de clases creados ✓

### ✅ Para vender planes online:
1. Portal público habilitado ✓
2. "Mostrar precios" activado ✓
3. Al menos 1 plan con "Visible online" ✓
4. Al menos 1 método de pago con "Disponible online" ✓

### ✅ Para registro de clientes:
1. Portal público habilitado ✓
2. "Permitir auto-registro" activado ✓
3. Campos personalizados configurados (opcional) ✓

---

## 🆘 PROBLEMAS COMUNES

### "No veo el widget en mi web"
- ✓ Verifica que "Permitir embedding" esté activado
- ✓ Si configuraste dominios permitidos, verifica que tu web esté en la lista
- ✓ Revisa que el iframe tenga la URL correcta con tu slug

### "No aparecen mis actividades en el widget"
- ✓ Verifica que las actividades tengan marcado "Visible online"
- ✓ Verifica que haya horarios creados para esas actividades
- ✓ Recarga la página del widget (Ctrl+F5)

### "No aparecen mis planes en precios"
- ✓ Verifica que "Mostrar precios" esté activado en configuración
- ✓ Verifica que los planes tengan marcado "Visible online"
- ✓ Verifica que los planes estén "Activos"

### "Los clientes no pueden comprar"
- ✓ Verifica que haya métodos de pago con "Disponible online"
- ✓ Verifica que los métodos de pago estén "Activos"
- ✓ Si usas pasarelas (Stripe/Redsys), verifica credenciales

---

## 📞 SOPORTE

Si tienes dudas o problemas, contacta con el administrador del sistema o soporte técnico.

---

## 🎯 RESUMEN VISUAL

```
BACKOFFICE
    │
    ├── Configuración
    │   └── Organizations
    │       └── [Tu Gimnasio]
    │           └── ✅ Portal Público (configuración general)
    │
    ├── Actividades
    │   └── Clases
    │       └── [Actividad]
    │           └── ✅ Visible online
    │
    ├── Membresías
    │   └── Planes
    │       └── [Plan]
    │           └── ✅ Visible online
    │           └── ✅ Orden de visualización
    │
    ├── Finanzas
    │   └── Métodos de Pago
    │       └── [Método]
    │           └── ✅ Disponible para compra online
    │           └── ✅ Pasarela de pago
    │
    └── Clientes
        └── Campos Personalizados
            └── [Campo]
                └── ✅ Mostrar en registro público
```

---

**¿Todo claro?** ¡Perfecto! Si necesitas ayuda, no dudes en preguntar. 🚀
