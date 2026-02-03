#!/bin/bash
# ==============================================
# SCRIPT DE CONFIGURACIÓN SSL CON LET'S ENCRYPT
# ==============================================
# Uso: ./scripts/setup_ssl.sh tudominio.com email@tudominio.com
#
# Este script:
# 1. Instala Certbot si no existe
# 2. Genera certificados SSL
# 3. Configura renovación automática

set -e

DOMAIN=${1:-""}
EMAIL=${2:-""}

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   Setup SSL con Let's Encrypt${NC}"
echo -e "${GREEN}===============================================${NC}"

# Validar argumentos
if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo -e "${RED}Error: Debes proporcionar dominio y email${NC}"
    echo "Uso: $0 tudominio.com email@tudominio.com"
    exit 1
fi

echo -e "${YELLOW}Dominio: ${DOMAIN}${NC}"
echo -e "${YELLOW}Email: ${EMAIL}${NC}"
echo ""

# ----------------------------------------------
# 1. Instalar Certbot
# ----------------------------------------------
echo -e "${GREEN}[1/5] Verificando Certbot...${NC}"
if ! command -v certbot &> /dev/null; then
    echo "Instalando Certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
else
    echo "Certbot ya instalado"
fi

# ----------------------------------------------
# 2. Crear directorio para challenges
# ----------------------------------------------
echo -e "${GREEN}[2/5] Creando directorios...${NC}"
mkdir -p /var/www/certbot

# ----------------------------------------------
# 3. Generar certificado
# ----------------------------------------------
echo -e "${GREEN}[3/5] Generando certificado SSL...${NC}"
echo ""

# Opción A: Si Nginx está corriendo, usar plugin nginx
# Opción B: Si es primera vez, usar standalone

if docker ps | grep -q nginx; then
    echo "Usando método webroot (Nginx corriendo)..."
    certbot certonly \
        --webroot \
        -w /var/www/certbot \
        -d ${DOMAIN} \
        -d www.${DOMAIN} \
        --email ${EMAIL} \
        --agree-tos \
        --no-eff-email \
        --force-renewal
else
    echo "Usando método standalone (Nginx detenido)..."
    certbot certonly \
        --standalone \
        -d ${DOMAIN} \
        -d www.${DOMAIN} \
        --email ${EMAIL} \
        --agree-tos \
        --no-eff-email
fi

# ----------------------------------------------
# 4. Verificar certificados
# ----------------------------------------------
echo -e "${GREEN}[4/5] Verificando certificados...${NC}"
if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    echo -e "${GREEN}✓ Certificado generado correctamente${NC}"
    echo ""
    openssl x509 -in /etc/letsencrypt/live/${DOMAIN}/fullchain.pem -text -noout | grep -A2 "Validity"
else
    echo -e "${RED}✗ Error: Certificado no encontrado${NC}"
    exit 1
fi

# ----------------------------------------------
# 5. Configurar renovación automática
# ----------------------------------------------
echo -e "${GREEN}[5/5] Configurando renovación automática...${NC}"

# Crear cron job para renovación
CRON_JOB="0 3 * * * certbot renew --quiet --post-hook 'docker exec crm_nginx_prod nginx -s reload'"

# Verificar si ya existe
if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cron job de renovación añadido (3:00 AM diario)"
else
    echo "Cron job de renovación ya existe"
fi

# ----------------------------------------------
# Resumen
# ----------------------------------------------
echo ""
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   ✓ SSL CONFIGURADO CORRECTAMENTE${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo "Certificados en: /etc/letsencrypt/live/${DOMAIN}/"
echo ""
echo "Próximos pasos:"
echo "  1. Actualiza .env con: DOMAIN=${DOMAIN}"
echo "  2. Reinicia los contenedores:"
echo "     docker-compose -f docker-compose.prod.yml down"
echo "     docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "  3. Verifica SSL: https://www.ssllabs.com/ssltest/analyze.html?d=${DOMAIN}"
echo ""
