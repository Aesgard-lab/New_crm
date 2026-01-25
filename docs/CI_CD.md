# CI/CD - Guia de Configuracion

## Resumen de Workflows

| Workflow | Trigger | Descripcion |
|----------|---------|-------------|
| **CI** | Push/PR a main/develop | Tests, linting, security checks |
| **CD** | Push a main | Deploy automatico a produccion |
| **Security** | Semanal + PRs | Escaneo de vulnerabilidades |
| **Docker** | Releases | Build multi-arquitectura |

## Estructura de Archivos

```
.github/
├── workflows/
│   ├── ci.yml          # Continuous Integration
│   ├── cd.yml          # Continuous Deployment
│   ├── security.yml    # Security scanning
│   └── docker.yml      # Docker build & publish
├── dependabot.yml      # Actualizaciones automaticas
└── PULL_REQUEST_TEMPLATE.md
```

## Configuracion Inicial

### 1. Secrets Requeridos

Configura estos secrets en GitHub → Settings → Secrets and variables → Actions:

#### Obligatorios para CI
```
DJANGO_SECRET_KEY          # Clave secreta para tests de produccion
```

#### Obligatorios para CD (Deploy)
```
PRODUCTION_HOST            # IP o dominio del servidor
PRODUCTION_USER            # Usuario SSH
PRODUCTION_SSH_KEY         # Clave privada SSH
PRODUCTION_PATH            # Ruta del proyecto en servidor
PRODUCTION_DOMAIN          # Dominio de produccion
```

#### Opcionales (Staging)
```
STAGING_HOST
STAGING_USER
STAGING_SSH_KEY
STAGING_PATH
```

#### Opcionales (Notificaciones)
```
SLACK_WEBHOOK_URL          # Webhook de Slack
```

#### Opcionales (Docker Hub)
```
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

### 2. Configurar Servidor de Produccion

```bash
# En el servidor de produccion:

# 1. Instalar Docker y Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Clonar repositorio
git clone https://github.com/tu-usuario/tu-repo.git /opt/crm
cd /opt/crm

# 3. Crear archivo .env
cp .env.example .env
nano .env  # Configurar variables

# 4. Primer deploy manual
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Configurar SSH Key

```bash
# En tu maquina local:

# 1. Generar key especifica para deploy
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy

# 2. Copiar clave publica al servidor
ssh-copy-id -i ~/.ssh/github_deploy.pub user@servidor

# 3. Copiar clave privada a GitHub Secrets
cat ~/.ssh/github_deploy  # Copiar todo el contenido a PRODUCTION_SSH_KEY
```

## Flujo de Trabajo

### Desarrollo Normal

```
1. Crear branch desde develop
   git checkout develop
   git checkout -b feature/nueva-funcionalidad

2. Desarrollar y hacer commits
   git add .
   git commit -m "feat: nueva funcionalidad"

3. Crear Pull Request a develop
   - CI se ejecuta automaticamente
   - Security scan en el PR
   - Review de codigo

4. Merge a develop
   - Deploy automatico a staging (si configurado)

5. Merge develop → main
   - Deploy automatico a produccion
```

### Hotfix

```
1. Crear branch desde main
   git checkout main
   git checkout -b hotfix/fix-critico

2. Fix y commit
   git commit -m "fix: solucion critica"

3. PR directo a main
   - CI completo
   - Review rapido

4. Merge a main
   - Deploy automatico a produccion
```

## Jobs del CI

### Lint & Format
- **Ruff**: Linter rapido de Python
- **Black**: Formateo de codigo
- **isort**: Ordenamiento de imports

### Tests
- Ejecuta pytest con cobertura
- PostgreSQL y Redis como servicios
- Sube reporte a Codecov

### Security
- **Bandit**: Analisis estatico de seguridad
- **pip-audit**: Vulnerabilidades en dependencias

### Deploy Check
- Verifica `python manage.py check --deploy`
- Solo despues de que pasen los tests

## Escaneo de Seguridad

### Herramientas Utilizadas

| Herramienta | Que analiza |
|-------------|-------------|
| CodeQL | Codigo fuente |
| Bandit | Codigo Python |
| pip-audit | Dependencias Python |
| Semgrep | Patrones de seguridad |
| TruffleHog | Secrets en codigo |
| Gitleaks | Secrets en historial git |
| Trivy | Imagen Docker |

### Ver Resultados

1. GitHub → Security tab → Code scanning alerts
2. GitHub → Security tab → Dependabot alerts
3. Artifacts en cada workflow run

## Dependabot

Configurado para actualizar automaticamente:
- **pip**: Dependencias Python (lunes)
- **github-actions**: Actions (lunes)
- **docker**: Imagenes base (lunes)

### Gestionar PRs de Dependabot

```bash
# Aprobar y merge automatico (si CI pasa)
@dependabot merge

# Rebase
@dependabot rebase

# Cerrar y ignorar
@dependabot close
```

## Troubleshooting

### CI falla en tests

```bash
# Ejecutar tests localmente igual que CI
docker-compose up -d db redis
pytest -v
```

### Deploy falla por SSH

```bash
# Verificar conexion SSH
ssh -i ~/.ssh/github_deploy user@servidor

# Verificar que la key esta en el servidor
cat ~/.ssh/authorized_keys
```

### Imagen Docker muy grande

```bash
# Analizar capas
docker history crm:latest

# Usar .dockerignore
cat .dockerignore
```

## Metricas y Badges

Añadir al README.md:

```markdown
![CI](https://github.com/USER/REPO/workflows/CI/badge.svg)
![Security](https://github.com/USER/REPO/workflows/Security/badge.svg)
[![codecov](https://codecov.io/gh/USER/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/USER/REPO)
```

## Recursos

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [GitHub Security Features](https://docs.github.com/en/code-security)
