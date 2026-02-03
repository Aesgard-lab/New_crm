#!/bin/bash
# ==============================================
# DIAGNÓSTICO DE ARCHIVOS ESTÁTICOS Y MEDIA
# ==============================================
# Uso: ./scripts/diagnose_static.sh
#
# Verifica que static y media estén correctamente configurados

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   Diagnóstico de Static/Media Files${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""

# ----------------------------------------------
# 1. Verificar contenedor web
# ----------------------------------------------
echo -e "${YELLOW}[1/6] Verificando contenedor web...${NC}"
if docker ps | grep -q crm_web_prod; then
    echo -e "  ${GREEN}✓ Contenedor web corriendo${NC}"
else
    echo -e "  ${RED}✗ Contenedor web NO está corriendo${NC}"
    exit 1
fi

# ----------------------------------------------
# 2. Verificar que collectstatic se ejecutó
# ----------------------------------------------
echo -e "${YELLOW}[2/6] Verificando archivos estáticos...${NC}"
STATIC_COUNT=$(docker exec crm_web_prod ls -la /app/staticfiles/ 2>/dev/null | wc -l)
if [ "$STATIC_COUNT" -gt 5 ]; then
    echo -e "  ${GREEN}✓ Directorio staticfiles tiene archivos ($STATIC_COUNT items)${NC}"
else
    echo -e "  ${RED}✗ Directorio staticfiles vacío o con pocos archivos${NC}"
    echo "  Ejecutando collectstatic..."
    docker exec crm_web_prod python manage.py collectstatic --noinput
fi

# ----------------------------------------------
# 3. Verificar permisos
# ----------------------------------------------
echo -e "${YELLOW}[3/6] Verificando permisos...${NC}"
docker exec crm_web_prod ls -la /app/staticfiles/ | head -5
docker exec crm_web_prod ls -la /app/media/ | head -5

# ----------------------------------------------
# 4. Verificar que Nginx puede acceder
# ----------------------------------------------
echo -e "${YELLOW}[4/6] Verificando acceso de Nginx...${NC}"
NGINX_STATIC=$(docker exec crm_nginx_prod ls /app/staticfiles/ 2>/dev/null | wc -l)
if [ "$NGINX_STATIC" -gt 0 ]; then
    echo -e "  ${GREEN}✓ Nginx puede ver los archivos estáticos${NC}"
else
    echo -e "  ${RED}✗ Nginx NO puede ver los archivos estáticos${NC}"
    echo "  Verifica los volúmenes en docker-compose.prod.yml"
fi

# ----------------------------------------------
# 5. Verificar URLs accesibles
# ----------------------------------------------
echo -e "${YELLOW}[5/6] Verificando URLs...${NC}"

# Verificar /static/
STATIC_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/admin/css/base.css 2>/dev/null || echo "000")
if [ "$STATIC_RESPONSE" = "200" ]; then
    echo -e "  ${GREEN}✓ /static/ accesible (HTTP $STATIC_RESPONSE)${NC}"
else
    echo -e "  ${RED}✗ /static/ NO accesible (HTTP $STATIC_RESPONSE)${NC}"
fi

# Verificar /media/ (puede estar vacío)
MEDIA_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/media/ 2>/dev/null || echo "000")
echo -e "  Media: HTTP $MEDIA_RESPONSE (403 es normal si está vacío)"

# ----------------------------------------------
# 6. Verificar configuración Nginx
# ----------------------------------------------
echo -e "${YELLOW}[6/6] Configuración de Nginx...${NC}"
docker exec crm_nginx_prod nginx -T 2>/dev/null | grep -A2 "location /static" || echo "  No se encontró configuración de /static/"

echo ""
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   Diagnóstico completado${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo "Si hay problemas, ejecuta:"
echo "  docker exec crm_web_prod python manage.py collectstatic --noinput"
echo "  docker-compose -f docker-compose.prod.yml restart nginx"
