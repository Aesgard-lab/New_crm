#!/bin/bash
# ==============================================
# SCRIPT DE INICIALIZACIÓN SSL - PRIMERA VEZ
# ==============================================
# Uso: ./scripts/init_ssl.sh tudominio.com email@tudominio.com
#
# Este script prepara todo para el primer certificado SSL

set -e

DOMAIN=${1:-""}
EMAIL=${2:-""}

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo -e "${RED}Error: Debes proporcionar dominio y email${NC}"
    echo "Uso: $0 tudominio.com email@tudominio.com"
    exit 1
fi

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   Inicialización SSL - ${DOMAIN}${NC}"
echo -e "${GREEN}===============================================${NC}"

# 1. Crear directorios
echo -e "${YELLOW}[1/4] Creando directorios...${NC}"
mkdir -p docker/certbot/conf
mkdir -p docker/certbot/www

# 2. Crear configuración temporal de nginx (sin SSL)
echo -e "${YELLOW}[2/4] Creando config temporal de Nginx...${NC}"
cat > docker/nginx/conf.d/default.conf << EOF
# Configuración temporal para obtener certificado SSL
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias /app/staticfiles/;
    }

    location /media/ {
        alias /app/media/;
    }
}
EOF

# 3. Levantar servicios (sin certbot)
echo -e "${YELLOW}[3/4] Levantando servicios...${NC}"
docker-compose -f docker-compose.prod.yml up -d db redis web nginx

echo "Esperando que los servicios estén listos..."
sleep 10

# 4. Obtener certificado
echo -e "${YELLOW}[4/4] Obteniendo certificado SSL...${NC}"
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot \
    -w /var/www/certbot \
    -d ${DOMAIN} \
    -d www.${DOMAIN} \
    --email ${EMAIL} \
    --agree-tos \
    --no-eff-email

# 5. Reemplazar config nginx con versión SSL
echo -e "${GREEN}Activando configuración SSL...${NC}"
cp docker/nginx/conf.d/ssl.conf docker/nginx/conf.d/default.conf

# Sustituir variable de dominio
sed -i "s/\${DOMAIN}/${DOMAIN}/g" docker/nginx/conf.d/default.conf

# 6. Reiniciar nginx
echo -e "${GREEN}Reiniciando Nginx con SSL...${NC}"
docker-compose -f docker-compose.prod.yml restart nginx

# 7. Levantar certbot para renovación automática
docker-compose -f docker-compose.prod.yml up -d certbot

echo ""
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   ✓ SSL CONFIGURADO!${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo -e "Tu sitio está disponible en: ${GREEN}https://${DOMAIN}${NC}"
echo ""
echo "Verifica tu SSL en:"
echo "  https://www.ssllabs.com/ssltest/analyze.html?d=${DOMAIN}"
echo ""
