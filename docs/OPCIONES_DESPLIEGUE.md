# Opciones de Despliegue - Comparativa de Recursos

## El problema

Docker dentro de virtualización anidada (Docker → VM → Hypervisor) genera un
overhead considerable. Cada contenedor consume ~50-150MB de RAM base adicional.
Con el `docker-compose.prod.yml` estándar se levantan **7 contenedores**:

| Contenedor | RAM estimada |
|-----------|-------------|
| PostgreSQL | 256-512 MB |
| Redis | 64-128 MB |
| Django/Gunicorn (4 workers) | 400-800 MB |
| Celery Worker (concurrency 4) | 300-600 MB |
| Celery Beat | 150-200 MB |
| Nginx | 32-64 MB |
| Certbot | 32-64 MB |
| **Docker overhead (7 cont.)** | **350-700 MB** |
| **TOTAL** | **1.5 - 3 GB** |

---

## 4 opciones disponibles (de más a menos Docker)

### Opción 1: `docker-compose.prod.yml` (Producción estándar)
```bash
docker-compose -f docker-compose.prod.yml up -d
```
- **7 contenedores** | RAM: ~3 GB | Para servidores dedicados potentes

### Opción 2: `docker-compose.lightweight.yml` (Reducido)
```bash
docker-compose -f docker-compose.lightweight.yml up -d
```
- **4 contenedores** (Celery+Beat combinados, sin Nginx, sin Certbot)
- RAM: ~1.5 GB | Para VPS medianos

### Opción 3: `docker-compose.single.yml` ⭐ NUEVO
```bash
docker-compose -f docker-compose.single.yml up -d
```
- **2 contenedores** (PostgreSQL + App all-in-one)
- **1 contenedor** si usas BD externa/managed
- RAM: ~1 GB
- Incluye Redis, Nginx, Gunicorn y Celery **dentro de un solo contenedor**
- Ideal para virtualización anidada

### Opción 4: Sin Docker ⭐ NUEVO
```bash
# Ver guía completa: docs/DEPLOY_SIN_DOCKER.md
```
- **0 contenedores** | RAM: ~700 MB
- Todo instalado nativamente con systemd
- Máximo rendimiento, cero overhead de virtualización
- Ideal cuando el hosting no soporta Docker o es muy caro

---

## Resumen de recursos

| Opción | Contenedores | RAM mínima | Ideal para |
|--------|:-----------:|:----------:|------------|
| prod | 7 | 3 GB | Servidor dedicado |
| lightweight | 4 | 1.5 GB | VPS con 4GB RAM |
| **single** | **1-2** | **1 GB** | **VPS con 2GB / VM anidada** |
| **sin docker** | **0** | **700 MB** | **Mínimos recursos / hosting compartido** |

---

## Cómo usar la opción single (recomendada para tu caso)

```bash
# 1. Construir la imagen
docker-compose -f docker-compose.single.yml build

# 2. Levantar (solo 2 contenedores)
docker-compose -f docker-compose.single.yml up -d

# 3. Ver logs
docker-compose -f docker-compose.single.yml logs -f app

# Con BD externa (1 solo contenedor):
# Edita docker-compose.single.yml, comenta el servicio 'db'
# y configura POSTGRES_HOST=tu-servidor-bd-externo
```

## Optimizaciones adicionales aplicadas

1. **Gunicorn `--preload`**: Comparte memoria entre workers (ahorra ~30% RAM)
2. **`CELERY_TASK_IGNORE_RESULT`**: No guarda resultados de tareas en BD
3. **Redis embebido**: 50MB máximo, sin persistencia (solo broker)
4. **Workers mínimos**: 2 Gunicorn + 1 Celery (ajustable vía env vars)
5. **`--max-requests`**: Recicla workers para evitar memory leaks
