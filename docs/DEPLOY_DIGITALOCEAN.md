# DigitalOcean Deployment Guide — Gym CRM

## Overview

This guide deploys the Django CRM **without Docker** on a DigitalOcean Droplet.  
Docker is not recommended here because it adds unnecessary overhead (~2–3 GB RAM for container virtualization layers). Running bare metal keeps the footprint under **1 GB RAM**.

### Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **Droplet** | Basic $6/mo (1 vCPU, 1 GB) | Basic $12/mo (2 vCPU, 2 GB) |
| **OS** | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| **Disk** | 25 GB SSD (default) | 25 GB is fine |

### Architecture

```
Client → Nginx (port 80/443) → Gunicorn (port 8000) → Django
                                                        ↕
                                              PostgreSQL (local)
                                              Redis (local)
                                              Celery + Beat (background)
```

All services run as native **systemd** services. No Docker.

---

## 1. Create the Droplet

1. Go to [DigitalOcean](https://cloud.digitalocean.com/) → **Create** → **Droplets**
2. Choose **Ubuntu 24.04 LTS**
3. Plan: **Basic → Regular SSD → $12/mo** (2 vCPU, 2 GB RAM)
4. Datacenter: Choose closest to users (e.g., `FRA1` for Spain)
5. Authentication: **SSH key** (recommended) or password
6. Click **Create Droplet**

---

## 2. Initial Server Setup

SSH into the droplet:

```bash
ssh root@YOUR_DROPLET_IP
```

### 2a. Create non-root user

```bash
adduser crm --disabled-password --gecos ""
usermod -aG sudo crm
# Allow crm user to sudo without password (for service management)
echo "crm ALL=(ALL) NOPASSWD: /bin/systemctl" >> /etc/sudoers.d/crm

# Copy SSH keys
mkdir -p /home/crm/.ssh
cp /root/.ssh/authorized_keys /home/crm/.ssh/
chown -R crm:crm /home/crm/.ssh
chmod 700 /home/crm/.ssh
```

### 2b. Configure firewall

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

### 2c. Enable swap (important for 1–2 GB droplets)

```bash
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
# Tune swap behavior
echo 'vm.swappiness=10' >> /etc/sysctl.conf
sysctl -p
```

---

## 3. Install System Dependencies

```bash
apt update && apt upgrade -y

# Python 3.12
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt install -y python3.12 python3.12-venv python3.12-dev

# PostgreSQL 16
apt install -y postgresql postgresql-contrib

# Redis
apt install -y redis-server

# Nginx
apt install -y nginx

# Build dependencies (needed for pip packages like psycopg2, weasyprint)
apt install -y build-essential libpq-dev curl git

# WeasyPrint system dependencies (for PDF generation)
apt install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 libgirepository1.0-dev gir1.2-pango-1.0
```

---

## 4. Configure PostgreSQL

```bash
sudo -u postgres psql <<EOF
CREATE USER crm_user WITH PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
CREATE DATABASE crm_db OWNER crm_user;
ALTER USER crm_user CREATEDB;
\q
EOF
```

Optimize PostgreSQL for low-memory servers. Edit `/etc/postgresql/*/main/postgresql.conf`:

```ini
shared_buffers = 128MB
effective_cache_size = 256MB
maintenance_work_mem = 64MB
work_mem = 4MB
max_connections = 30
checkpoint_completion_target = 0.9
random_page_cost = 1.1
```

```bash
systemctl restart postgresql
```

---

## 5. Configure Redis (minimal resources)

Edit `/etc/redis/redis.conf`:

```ini
maxmemory 50mb
maxmemory-policy allkeys-lru
save ""
appendonly no
```

```bash
systemctl restart redis-server
```

---

## 6. Deploy the Application

Switch to the crm user for all following steps:

```bash
su - crm
```

### 6a. Clone the repository

```bash
mkdir -p /opt/crm
cd /opt/crm
git clone https://github.com/Aesgard-lab/New_crm.git app
```

### 6b. Create virtual environment

```bash
python3.12 -m venv /opt/crm/venv
source /opt/crm/venv/bin/activate
pip install --upgrade pip
pip install -r /opt/crm/app/requirements.txt
```

### 6c. Create environment file

```bash
cat > /opt/crm/.env <<'ENVEOF'
DJANGO_ENV=production
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=GENERATE_WITH_COMMAND_BELOW
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,YOUR_DROPLET_IP
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database
POSTGRES_DB=crm_db
POSTGRES_USER=crm_user
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0

# Email (SMTP)
EMAIL_HOST=smtp.yourprovider.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your_email_password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=your@email.com

# Stripe (if using payments)
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

# Sentry (optional, for error tracking)
SENTRY_DSN=
ENVEOF
```

Generate a secret key:

```bash
python3.12 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and replace `GENERATE_WITH_COMMAND_BELOW` in `/opt/crm/.env`.

### 6d. Run migrations and collect static files

```bash
cd /opt/crm/app
source /opt/crm/venv/bin/activate
export $(grep -v '^#' /opt/crm/.env | xargs)

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createsuperuser  # Create admin account
```

### 6e. Create logs directory

```bash
mkdir -p /opt/crm/logs
```

---

## 7. Create systemd Services

Run the following as **root** (`exit` from crm user, or prefix with `sudo`):

### 7a. Gunicorn (Django web server)

```bash
sudo tee /etc/systemd/system/crm-web.service <<'EOF'
[Unit]
Description=CRM Django (Gunicorn)
After=network.target postgresql.service redis-server.service
Requires=postgresql.service

[Service]
Type=notify
User=crm
Group=crm
WorkingDirectory=/opt/crm/app
EnvironmentFile=/opt/crm/.env
ExecStart=/opt/crm/venv/bin/gunicorn config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 2 \
    --worker-class sync \
    --timeout 120 \
    --max-requests 500 \
    --max-requests-jitter 50 \
    --keep-alive 5 \
    --log-level warning \
    --access-logfile /opt/crm/logs/access.log \
    --error-logfile /opt/crm/logs/error.log
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=5
KillMode=mixed
PrivateTmp=true
NoNewPrivileges=true
MemoryMax=512M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF
```

### 7b. Celery (background worker + scheduler combined)

```bash
sudo tee /etc/systemd/system/crm-celery.service <<'EOF'
[Unit]
Description=CRM Celery Worker + Beat
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=forking
User=crm
Group=crm
WorkingDirectory=/opt/crm/app
EnvironmentFile=/opt/crm/.env
ExecStart=/opt/crm/venv/bin/celery -A config worker \
    --beat \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --loglevel WARNING \
    --concurrency 1 \
    --max-tasks-per-child 100 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    --detach \
    --pidfile=/opt/crm/celery.pid \
    --logfile=/opt/crm/logs/celery.log
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always
RestartSec=10
MemoryMax=384M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF
```

### 7c. Enable and start services

```bash
sudo systemctl daemon-reload
sudo systemctl enable crm-web crm-celery
sudo systemctl start crm-web crm-celery

# Verify they are running
sudo systemctl status crm-web
sudo systemctl status crm-celery
```

---

## 8. Configure Nginx

```bash
sudo tee /etc/nginx/sites-available/crm <<'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 20M;

    # Static files (served directly by Nginx, not Django)
    location /static/ {
        alias /opt/crm/app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Media files (user uploads)
    location /media/ {
        alias /opt/crm/app/media/;
        expires 7d;
        access_log off;
    }

    # Django app (proxied to Gunicorn)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## 9. SSL Certificate (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot will automatically:
- Obtain the SSL certificate
- Configure Nginx for HTTPS
- Set up auto-renewal (via systemd timer)

---

## 10. DNS Configuration

In your domain registrar, add these DNS records pointing to the Droplet IP:

| Type | Name | Value |
|------|------|-------|
| A | @ | YOUR_DROPLET_IP |
| A | www | YOUR_DROPLET_IP |

---

## 11. Update Script

Create `/opt/crm/update.sh` for easy deployments:

```bash
sudo tee /opt/crm/update.sh <<'SCRIPT'
#!/bin/bash
set -e
cd /opt/crm/app
source /opt/crm/venv/bin/activate
export $(grep -v '^#' /opt/crm/.env | xargs)

echo "Pulling latest code..."
git pull origin main

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Restarting services..."
sudo systemctl restart crm-web crm-celery

echo "✅ Deployment complete!"
echo "Check status: sudo systemctl status crm-web crm-celery"
SCRIPT

chmod +x /opt/crm/update.sh
```

To deploy updates, simply run:

```bash
/opt/crm/update.sh
```

---

## Expected Resource Usage

Once deployed, expected consumption on a **$12/mo Droplet** (2 vCPU, 2 GB RAM):

| Service | RAM | CPU |
|---------|-----|-----|
| PostgreSQL | ~120 MB | < 5% |
| Redis | ~20 MB | < 1% |
| Gunicorn (2 workers) | ~250 MB | < 10% |
| Celery (1 worker + beat) | ~150 MB | < 5% |
| Nginx | ~10 MB | < 1% |
| **Total** | **~550 MB** | **< 20%** |

This leaves ~1.4 GB free for peaks and the OS itself.

---

## Useful Commands

```bash
# Check service status
sudo systemctl status crm-web crm-celery

# View real-time logs
sudo journalctl -u crm-web -f
sudo journalctl -u crm-celery -f
tail -f /opt/crm/logs/access.log
tail -f /opt/crm/logs/error.log

# Restart services
sudo systemctl restart crm-web crm-celery

# Django shell
cd /opt/crm/app && source /opt/crm/venv/bin/activate
python manage.py shell

# Check memory usage
free -h
ps aux --sort=-%mem | head -15

# PostgreSQL backup
sudo -u postgres pg_dump crm_db > /opt/crm/backup_$(date +%Y%m%d).sql
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `502 Bad Gateway` | Check Gunicorn: `sudo systemctl status crm-web` |
| `Static files not loading` | Run `python manage.py collectstatic --noinput` and restart Nginx |
| `Database connection refused` | Check PostgreSQL: `sudo systemctl status postgresql` |
| `Celery tasks not running` | Check Celery: `sudo systemctl status crm-celery` |
| `Permission denied` errors | Run `sudo chown -R crm:crm /opt/crm` |
| `Out of memory` | Verify swap is enabled: `free -h`, check for runaway processes |
| `SSL certificate expired` | Run `sudo certbot renew` |
