# 🛠️ Guía de Desarrollo

Esta guía cubre las convenciones, estándares y flujos de trabajo para desarrollar en el CRM.

## 📋 Tabla de Contenidos

1. [Setup del Entorno](#setup-del-entorno)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Convenciones de Código](#convenciones-de-código)
4. [Testing](#testing)
5. [Git Workflow](#git-workflow)
6. [API Guidelines](#api-guidelines)

---

## 🚀 Setup del Entorno

### Requisitos

- Python 3.11+
- PostgreSQL 14+ (o SQLite para desarrollo)
- Redis 7+
- Node.js 18+ (para tests E2E)

### Instalación Local

```bash
# 1. Clonar repositorio
git clone <repo> && cd New_crm

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env según necesidades

# 5. Ejecutar migraciones
python manage.py migrate

# 6. Crear superusuario
python manage.py createsuperuser

# 7. Ejecutar servidor
python manage.py runserver
```

### Setup con Docker

```bash
# Desarrollo con hot-reload
docker-compose up -d

# Ver logs
docker-compose logs -f web
```

---

## 📁 Estructura del Proyecto

```
New_crm/
├── config/              # Configuración Django
│   ├── settings.py      # Settings principales
│   ├── urls.py          # URLs raíz
│   └── celery.py        # Config Celery
│
├── accounts/            # Usuarios y autenticación
├── activities/          # Actividades y clases
├── api/                 # API REST (mobile app)
├── clients/             # Gestión de clientes
├── finance/             # Finanzas, pagos, facturas
├── gyms/organizations/  # Multi-tenancy
├── memberships/         # Planes y membresías
├── public_portal/       # Portal público
├── staff/               # Gestión de personal
│
├── tests/               # Tests centralizados
│   ├── conftest.py      # Fixtures globales
│   ├── factories.py     # Factory Boy factories
│   └── unit/            # Tests unitarios
│
├── scripts/             # Scripts de utilidad
│   ├── diagnostics/     # Diagnósticos
│   ├── maintenance/     # Mantenimiento
│   └── setup/           # Setup inicial
│
├── docs/                # Documentación
├── e2e/                 # Tests E2E (Playwright)
├── docker/              # Configuraciones Docker
├── k8s/                 # Manifiestos Kubernetes
└── terraform/           # Infraestructura como código
```

---

## 📝 Convenciones de Código

### Python / Django

```python
# Imports ordenados (isort)
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from .services import MembershipService


# Modelos con docstrings
class MembershipPlan(models.Model):
    """
    Representa un plan de membresía configurable.
    
    Attributes:
        name: Nombre del plan
        base_price: Precio base sin impuestos
        is_recurring: Si es recurrente o bono
    """
    name = models.CharField(_("Nombre"), max_length=100)
    base_price = models.DecimalField(_("Precio Base"), max_digits=10, decimal_places=2)
    is_recurring = models.BooleanField(_("Es Recurrente"), default=True)


# Vistas con documentación
class MembershipDetailView(DetailView):
    """
    Vista de detalle de membresía.
    
    GET: Retorna datos de la membresía
    Permisos: membership.view
    """
    model = Membership
    template_name = "memberships/detail.html"
```

### Formateo

- **Ruff** para linting y formateo
- **Línea máxima**: 100 caracteres
- **Quotes**: Comillas dobles

```bash
# Ejecutar linter
ruff check .

# Auto-fix
ruff check --fix .

# Formatear
ruff format .
```

### Nombres

| Tipo | Convención | Ejemplo |
|------|------------|---------|
| Modelos | PascalCase | `ClientMembership` |
| Funciones | snake_case | `get_active_memberships()` |
| Constantes | UPPER_SNAKE | `MAX_RETRY_ATTEMPTS` |
| Templates | kebab-case | `membership-detail.html` |
| URLs | kebab-case | `/api/my-bookings/` |

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Con coverage
pytest --cov=. --cov-report=html

# Tests específicos
pytest tests/unit/test_memberships.py

# Por marker
pytest -m "django_db"

# Verbose
pytest -v
```

### Escribir Tests

```python
# tests/unit/test_memberships.py
import pytest
from tests.factories import ClientFactory, MembershipPlanFactory


@pytest.mark.django_db
class TestMembershipCreation:
    """Tests para creación de membresías."""
    
    def test_membership_with_valid_data(self):
        """Membresía se crea correctamente con datos válidos."""
        client = ClientFactory()
        plan = MembershipPlanFactory(gym=client.gym)
        
        membership = Membership.objects.create(
            client=client,
            plan=plan,
            start_date=date.today()
        )
        
        assert membership.status == 'ACTIVE'
        assert membership.price == plan.base_price
```

### Factories

```python
# tests/factories.py
from tests.factories import (
    GymFactory,
    ClientFactory,
    MembershipPlanFactory,
    ClientMembershipFactory,
)

# Crear con valores por defecto
client = ClientFactory()

# Crear con valores específicos
client = ClientFactory(
    first_name="Juan",
    status="ACTIVE"
)

# Crear con relaciones
membership = ClientMembershipFactory(
    client__gym=gym,
    plan__is_recurring=True
)
```

### Tests E2E

```bash
cd e2e
npm install
npx playwright test
```

---

## 🔀 Git Workflow

### Branches

- `main` - Producción estable
- `develop` - Desarrollo integrado
- `feature/*` - Nuevas funcionalidades
- `fix/*` - Correcciones de bugs
- `hotfix/*` - Fixes urgentes para producción

### Commits

Usar [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add membership pause functionality
fix: correct price calculation with taxes
docs: update API documentation
test: add tests for booking cancellation
refactor: simplify permission checking
chore: update dependencies
```

### Pull Requests

1. Crear branch desde `develop`
2. Hacer commits atómicos
3. Ejecutar tests localmente
4. Crear PR con descripción clara
5. Esperar review y CI verde
6. Merge con squash

```bash
# Crear feature branch
git checkout develop
git pull origin develop
git checkout -b feature/membership-pause

# Trabajar...
git add .
git commit -m "feat: add pause functionality to memberships"

# Push y crear PR
git push origin feature/membership-pause
```

---

## 🌐 API Guidelines

### Estructura de Endpoints

```
/api/
├── login/              POST   - Autenticación
├── check/              GET    - Verificar token
├── profile/            GET    - Perfil del usuario
├── gyms/               GET    - Buscar gimnasios
├── schedule/           GET    - Horario de clases
├── my-bookings/        GET    - Mis reservas
├── book/               POST   - Hacer reserva
└── cancel-booking/     POST   - Cancelar reserva
```

### Formato de Respuestas

```json
// Éxito
{
    "status": "ok",
    "data": { ... }
}

// Error
{
    "error": "Descripción del error",
    "code": "ERROR_CODE"
}

// Lista paginada
{
    "count": 100,
    "next": "/api/clients/?page=2",
    "previous": null,
    "results": [ ... ]
}
```

### Autenticación

```python
# Token en header
Authorization: Token <token-key>

# Endpoints públicos
permission_classes = [AllowAny]

# Endpoints protegidos
permission_classes = [IsAuthenticated]
```

### Rate Limiting

```python
from django_ratelimit.decorators import ratelimit

@method_decorator(ratelimit(key='ip', rate='30/m', method='GET'))
def get(self, request):
    ...
```

---

## 📚 Recursos Adicionales

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [Factory Boy](https://factoryboy.readthedocs.io/)

---

## ❓ FAQ

### ¿Cómo añadir una nueva app?

```bash
python manage.py startapp nueva_app
# Añadir a INSTALLED_APPS en settings.py
# Crear modelos, vistas, urls
# Incluir urls en config/urls.py
```

### ¿Cómo crear una migración?

```bash
python manage.py makemigrations app_name
python manage.py migrate
```

### ¿Cómo debuggear?

```python
# En código
import pdb; pdb.set_trace()

# O con breakpoint()
breakpoint()

# Django Debug Toolbar en desarrollo
# Ya está configurado, visible en /debug/
```
