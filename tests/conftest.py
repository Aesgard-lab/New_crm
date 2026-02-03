"""
Global pytest configuration and fixtures for the CRM test suite.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def db_access_without_rollback_and_truncate(request, django_db_setup, django_db_blocker):
    """Allow database access without rolling back transactions."""
    django_db_blocker.unblock()
    request.addfinalizer(django_db_blocker.restore)


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def user_password():
    """Default password for test users."""
    return "TestPassword123!"


@pytest.fixture
def superuser(db, user_password):
    """Create a superuser for testing admin functionality."""
    user = User.objects.create_superuser(
        email="admin@test.com",
        password=user_password,
    )
    return user


@pytest.fixture
def staff_user(db, user_password):
    """Create a staff user for testing staff functionality."""
    user = User.objects.create_user(
        email="staff@test.com",
        password=user_password,
    )
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def regular_user(db, user_password):
    """Create a regular user for testing client functionality."""
    user = User.objects.create_user(
        email="user@test.com",
        password=user_password,
    )
    return user


# ============================================================================
# HTTP Client Fixtures
# ============================================================================

@pytest.fixture
def anonymous_client():
    """HTTP client without authentication."""
    return Client()


@pytest.fixture
def authenticated_client(regular_user, user_password):
    """HTTP client authenticated as regular user."""
    client = Client()
    client.login(username=regular_user.email, password=user_password)
    return client


@pytest.fixture
def staff_client(staff_user, user_password):
    """HTTP client authenticated as staff user."""
    client = Client()
    client.login(username=staff_user.email, password=user_password)
    return client


@pytest.fixture
def admin_client(superuser, user_password):
    """HTTP client authenticated as superuser."""
    client = Client()
    client.login(username=superuser.email, password=user_password)
    return client


# ============================================================================
# API Client Fixtures (DRF)
# ============================================================================

@pytest.fixture
def api_client():
    """DRF API client without authentication."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_api_client(regular_user):
    """DRF API client authenticated as regular user."""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=regular_user)
    return client


@pytest.fixture
def staff_api_client(staff_user):
    """DRF API client authenticated as staff user."""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def admin_api_client(superuser):
    """DRF API client authenticated as superuser."""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=superuser)
    return client
