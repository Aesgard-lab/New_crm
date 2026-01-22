# 📋 Guía de Importación de Clientes

## Descripción
Esta funcionalidad permite importar masivamente clientes desde un archivo CSV, facilitando la migración desde otros sistemas de gestión de gimnasios.

## Características
✅ **Detección automática de columnas** - El sistema reconoce automáticamente los nombres de columnas (independientemente del idioma)
✅ **Deduplicación** - Detecta automáticamente clientes duplicados por email, DNI o nombre+teléfono
✅ **Actualización inteligente** - Opción para actualizar clientes existentes sin duplicar información
✅ **Validación robusta** - Parsea automáticamente fechas en múltiples formatos
✅ **Manejo de errores** - Reporta errores específicos por fila y permite continuar con la importación
✅ **Soporte multiidioma** - Reconoce columnas en español e inglés

## Campos Soportados

### Obligatorios
- **Nombre** (aliases: `nombre`, `first_name`, `nombre_cliente`)

### Opcionales Recomendados
- **Apellido** (aliases: `apellido`, `last_name`, `apellidos`, `apellido_cliente`)
- **Email** (aliases: `email`, `correo`, `email_cliente`)
- **Teléfono** (aliases: `teléfono`, `telefono`, `phone`, `celular`, `movil`)
- **DNI** (aliases: `dni`, `nif`, `id`, `document`, `cedula`)
- **Fecha Nacimiento** (aliases: `fecha_nacimiento`, `birth_date`, `nacimiento`)
- **Género** (aliases: `género`, `genero`, `gender`, `sexo`)
- **Dirección** (aliases: `dirección`, `direccion`, `address`, `domicilio`)
- **Estado** (aliases: `estado`, `status`, `estatus`)

## Formatos de Fecha Soportados
- `DD/MM/YYYY` (ej: 15/05/1990)
- `DD-MM-YYYY` (ej: 15-05-1990)
- `YYYY-MM-DD` (ej: 1990-05-15)
- `DD.MM.YYYY` (ej: 15.05.1990)
- `DD/MM/YY` (ej: 15/05/90)

## Mapeo de Géneros
- **M** / Male / Masculino / Hombre → Masculino
- **F** / Female / Femenino / Mujer → Femenino
- **O** / Otro / Other → Otro
- **X** / Not Specified / No especificado → No especificado

## Mapeo de Estados
- **LEAD** / Prospecto / Prospect → Prospecto
- **ACTIVE** / Activo → Activo
- **INACTIVE** / Inactivo → Inactivo
- **PAUSED** / Excedencia → Excedencia
- **BLOCKED** / Bloqueado → Bloqueado

## Ejemplo de CSV

```csv
nombre,apellido,email,teléfono,dni,fecha_nacimiento,género,dirección,estado
Juan,García López,juan.garcia@example.com,+34 612 345 678,12345678A,1990-05-15,M,Calle Principal 123,ACTIVE
María,Rodríguez,maria.rodriguez@example.com,+34 678 901 234,98765432B,1985-08-22,F,Calle Secundaria 456,ACTIVE
```

## Cómo Usar

### 1. Preparar el CSV
- Abre tu archivo en Excel o Google Sheets
- Asegúrate de que tenga al menos una columna de **nombre**
- Opcionalmente agrega las demás columnas
- Guarda como CSV (UTF-8)

### 2. Acceder a la importación
1. Ve a **Clientes** en el panel
2. Haz clic en **Importar CSV**
3. Selecciona tu archivo

### 3. Configurar opciones
- **Actualizar clientes existentes**: Si está marcado, los clientes duplicados se actualizarán con la nueva información
- **Saltar filas con errores**: Si está marcado, continúa la importación aunque haya errores

### 4. Ver resultados
El sistema mostrará:
- ✅ Clientes creados
- 🔄 Clientes actualizados
- ⏭️ Clientes omitidos
- ❌ Errores específicos (si los hay)

## Deduplicación

El sistema verifica duplicados en este orden de prioridad:

1. **Email** (si existe)
2. **DNI** (si existe)
3. **Nombre + Teléfono** (si existen)

Si se encuentra una coincidencia y tienes marcada la opción "Actualizar clientes existentes", se actualizará el cliente existente sin crear uno nuevo.

## Limitaciones

- Máximo 10MB por archivo
- Se actualiza el campo solo si está vacío en el cliente existente (excepto el estado)
- No actualiza usuarios ni contraseñas
- No importa fotos (deben subirse manualmente después)

## Resolución de Errores

### "No se encontró columna de nombre"
Asegúrate que haya una columna llamada `nombre`, `first_name` o similar.

### "No se pudo parsear fecha"
Usa uno de los formatos soportados (DD/MM/YYYY, YYYY-MM-DD, etc.)

### "Correo inválido"
Verifica que el email tenga formato correcto (usuario@dominio.com)

## Archivo de Ejemplo
Descarga el archivo `ejemplo_importacion_clientes.csv` del repositorio para ver el formato exacto.
