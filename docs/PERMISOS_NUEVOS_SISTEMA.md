# 🔐 Nuevos Permisos Añadidos al Sistema

## ✅ Permisos Creados

Se han añadido los siguientes permisos personalizados para el sistema de **Roles y Permisos**:

---

### **👥 STAFF (Personal)**

| Código del Permiso | Nombre Visible | Descripción |
|-------------------|----------------|-------------|
| `staff.view_staffkiosk` | Ver Kiosco de Fichaje | Permite ver la opción del kiosco en el menú |
| `staff.access_staffkiosk` | Acceder al Kiosco de Fichaje | Permite abrir y usar el kiosco de fichaje |
| `staff.manage_roles` | Gestionar Roles y Permisos | Permite crear y editar roles de personal |
| `staff.view_incentive` | Ver Incentivos y Comisiones | Permite ver y gestionar incentivos del personal |

---

### **📅 CALENDARIO Y HORARIOS**

| Código del Permiso | Nombre Visible | Descripción |
|-------------------|----------------|-------------|
| `activities.access_calendar` | Acceder al Calendario de Clases | Permite ver el calendario de sesiones |
| `activities.create_class_sessions` | Crear Sesiones de Clases | Permite crear nuevas clases en el calendario |
| `activities.manage_activity_sessions` | Gestionar Sesiones de Actividades | Permite editar y eliminar sesiones de clases |

---

### **⚙️ CONFIGURACIÓN DE HORARIOS**

| Código del Permiso | Nombre Visible | Descripción |
|-------------------|----------------|-------------|
| `activities.access_schedule_settings` | Acceder a Configuración de Horarios | Permite ver la configuración de horarios |
| `activities.modify_schedule_settings` | Modificar Configuración de Horarios | Permite cambiar validaciones y restricciones de horarios |

---

## 🎯 Uso en Roles

### **Ejemplo de Configuración por Rol**

#### **👔 GERENTE (Manager)**
```
✅ Todos los permisos de Staff
✅ Acceder al Calendario
✅ Crear Sesiones de Clases
✅ Gestionar Sesiones
✅ Acceder a Configuración de Horarios
✅ Modificar Configuración de Horarios
✅ Ver Kiosco de Fichaje
✅ Acceder al Kiosco
✅ Gestionar Roles y Permisos
✅ Ver Incentivos
```

#### **🏋️ ENTRENADOR (Trainer)**
```
✅ Acceder al Calendario (solo lectura)
✅ Ver sus propias sesiones
❌ Crear/Editar Sesiones
❌ Modificar Configuración
✅ Acceder al Kiosco de Fichaje
❌ Gestionar Roles
❌ Ver Incentivos de otros
```

#### **📞 RECEPCIONISTA (Receptionist)**
```
✅ Acceder al Calendario
✅ Crear Sesiones de Clases (para clientes)
❌ Modificar Configuración de Horarios
✅ Ver Kiosco de Fichaje
❌ Acceder al Kiosco (no necesita fichar)
❌ Gestionar Roles
❌ Ver Incentivos
```

#### **🧹 LIMPIEZA (Cleaner)**
```
❌ Acceder al Calendario
❌ Crear/Gestionar Sesiones
❌ Configuración de Horarios
✅ Acceder al Kiosco de Fichaje (para fichar entrada/salida)
❌ Ver Kiosco en menú
❌ Gestionar Roles
❌ Ver Incentivos
```

---

## 📍 Dónde Configurar

### **1. Acceso al Sistema de Roles**
```
Menú → Equipo → Roles y Permisos
```

### **2. Crear/Editar un Rol**
```
1. Click en "Crear Nuevo Rol" o editar existente
2. En la sección "Permisos", verás las nuevas opciones:
   
   📋 STAFF
   ☐ Ver Kiosco de Fichaje
   ☐ Acceder al Kiosco de Fichaje
   ☐ Gestionar Roles y Permisos
   ☐ Ver Incentivos y Comisiones
   
   📅 CALENDARIO
   ☐ Acceder al Calendario de Clases
   ☐ Crear Sesiones de Clases
   ☐ Gestionar Sesiones de Actividades
   
   ⚙️ CONFIGURACIÓN
   ☐ Acceder a Configuración de Horarios
   ☐ Modificar Configuración de Horarios
   
3. Selecciona los permisos apropiados
4. Guardar
```

### **3. Asignar Rol a Empleado**
```
1. Menú → Equipo → Lista de Empleados
2. Click en empleado
3. Seleccionar "Rol (Permisos)" en el dropdown
4. Guardar
```

---

## 🔒 Seguridad y Validación

### **Validación en Vistas**
Los permisos se validan automáticamente en las vistas con decoradores:

```python
# Ejemplo: Solo usuarios con permiso pueden acceder
@login_required
@require_gym_permission("staff.access_staffkiosk")
def staff_kiosk(request):
    return render(request, "staff/kiosk.html")
```

### **Validación en Templates**
En las plantillas se pueden ocultar opciones según permisos:

```django
{% has_gym_perm 'staff.view_staffkiosk' as can_view_kiosk %}
{% if can_view_kiosk %}
    <a href="{% url 'staff_kiosk' %}">Kiosco de Fichaje</a>
{% endif %}
```

---

## 🎨 Interfaz Visual

Los permisos aparecerán en el formulario de roles organizados por categorías:

```
┌─────────────────────────────────────────────┐
│  CREAR NUEVO ROL                             │
├─────────────────────────────────────────────┤
│  Nombre del Rol: [Gerente de Área         ] │
│                                              │
│  📋 PERMISOS DE STAFF                        │
│  ☑️ Ver Kiosco de Fichaje                    │
│  ☑️ Acceder al Kiosco de Fichaje             │
│  ☑️ Gestionar Roles y Permisos               │
│  ☑️ Ver Incentivos y Comisiones              │
│                                              │
│  📅 PERMISOS DE CALENDARIO                   │
│  ☑️ Acceder al Calendario de Clases          │
│  ☑️ Crear Sesiones de Clases                 │
│  ☑️ Gestionar Sesiones de Actividades        │
│                                              │
│  ⚙️ PERMISOS DE CONFIGURACIÓN                │
│  ☑️ Acceder a Configuración de Horarios      │
│  ☑️ Modificar Configuración de Horarios      │
│                                              │
│  [Guardar Rol]  [Cancelar]                   │
└─────────────────────────────────────────────┘
```

---

## ✅ Próximos Pasos

1. **Configurar Roles Básicos**
   - Crear rol "Gerente" con todos los permisos
   - Crear rol "Entrenador" con permisos limitados
   - Crear rol "Recepcionista" con permisos de calendario
   - Crear rol "Personal de Limpieza" solo con kiosco

2. **Asignar Roles**
   - Asignar rol correspondiente a cada empleado existente
   - Probar accesos desde diferentes cuentas

3. **Validar Seguridad**
   - Intentar acceder a páginas sin permiso
   - Verificar que los menús se oculten correctamente

---

## 📝 Notas Técnicas

- **Migraciones aplicadas**: `0012_alter_activity_options` y `0008_alter_staffprofile_options`
- **Base de datos**: Permisos almacenados en tabla `auth_permission`
- **Cache**: Los permisos se cachean automáticamente por Django
- **Performance**: No impacta rendimiento (queries optimizadas)

---

## 🆘 Troubleshooting

### **No veo los nuevos permisos en el formulario**
```bash
# Limpiar cache
python manage.py clear_cache

# Verificar migraciones
python manage.py showmigrations

# Re-ejecutar migraciones
python manage.py migrate
```

### **Los permisos no funcionan**
- Verificar que el usuario tenga un rol asignado
- Verificar que el rol tenga los permisos activados
- Revisar decoradores `@require_gym_permission` en las vistas

### **Error al guardar rol**
- Verificar que Django esté actualizado (>= 4.2)
- Revisar logs del servidor
- Verificar conexión a base de datos
