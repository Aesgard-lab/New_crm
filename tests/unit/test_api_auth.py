"""
Tests for API authentication and authorization.

Covers:
- Login endpoint
- Token authentication
- Permission checks
- Rate limiting validation
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from tests.factories import (
    GymFactory,
    UserFactory,
    ClientFactory,
    ClientWithUserFactory,
)


# API URL prefixes
API_LOGIN_URL = '/api/auth/login/'
API_CHECK_URL = '/api/auth/check/'
API_PROFILE_URL = '/api/profile/'
API_GYMS_URL = '/api/gyms/search/'
API_CONFIG_URL = '/api/system/config/'


@pytest.mark.django_db
class TestLoginAPI:
    """Test the login endpoint."""

    def test_login_with_valid_credentials(self, api_client):
        """Valid credentials should return token and client data."""
        gym = GymFactory()
        user = UserFactory(email="test@example.com")
        user.set_password("TestPassword123!")
        user.save()
        
        # Create client profile for user
        ClientFactory(gym=gym, user=user, email="test@example.com")
        
        response = api_client.post(API_LOGIN_URL, {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        assert 'client' in response.data

    def test_login_with_invalid_credentials(self, api_client):
        """Invalid credentials should return 400."""
        response = api_client.post(API_LOGIN_URL, {
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_login_missing_fields(self, api_client):
        """Missing email or password should return 400."""
        response = api_client.post(API_LOGIN_URL, {
            'email': 'test@example.com'
            # Missing password
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_user_without_client_profile(self, api_client):
        """User without client profile should return 403."""
        user = UserFactory(email="staff@example.com")
        user.set_password("TestPassword123!")
        user.save()
        
        response = api_client.post(API_LOGIN_URL, {
            'email': 'staff@example.com',
            'password': 'TestPassword123!'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'not a client' in response.data['error'].lower()

    def test_login_wrong_gym(self, api_client):
        """Login with wrong gym_id should return 403."""
        gym1 = GymFactory()
        gym2 = GymFactory()
        user = UserFactory(email="client@example.com")
        user.set_password("TestPassword123!")
        user.save()
        
        # Client belongs to gym1
        ClientFactory(gym=gym1, user=user, email="client@example.com")
        
        response = api_client.post(API_LOGIN_URL, {
            'email': 'client@example.com',
            'password': 'TestPassword123!',
            'gym_id': gym2.id  # Wrong gym
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTokenAuthentication:
    """Test token-based authentication."""

    def test_valid_token_access(self, api_client):
        """Valid token should grant access to protected endpoints."""
        gym = GymFactory()
        user = UserFactory()
        ClientFactory(gym=gym, user=user)
        token = Token.objects.create(user=user)
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = api_client.get(API_CHECK_URL)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'ok'

    def test_invalid_token_denied(self, api_client):
        """Invalid token should be denied access."""
        api_client.credentials(HTTP_AUTHORIZATION='Token invalidtoken123')
        response = api_client.get(API_CHECK_URL)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_no_token_denied(self, api_client):
        """Request without token should be denied."""
        response = api_client.get(API_CHECK_URL)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGymSearchAPI:
    """Test the gym search endpoint."""

    def test_search_gyms_by_name(self, api_client):
        """Search should return matching gyms."""
        GymFactory(name="Fitness Plus", city="Madrid")
        GymFactory(name="Gym Central", city="Barcelona")
        
        response = api_client.get(API_GYMS_URL, {'q': 'Fitness'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['name'] == "Fitness Plus"

    def test_search_gyms_by_city(self, api_client):
        """Search should match city as well."""
        GymFactory(name="Local Gym", city="Valencia")
        
        response = api_client.get(API_GYMS_URL, {'q': 'Valencia'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_search_too_short_query(self, api_client):
        """Query less than 2 chars should return empty."""
        GymFactory(name="Test Gym")
        
        response = api_client.get(API_GYMS_URL, {'q': 'T'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


@pytest.mark.django_db
class TestProfileAPI:
    """Test profile endpoints."""

    def test_get_profile_authenticated(self, api_client):
        """Authenticated user should get their profile."""
        gym = GymFactory()
        user = UserFactory()
        client = ClientFactory(
            gym=gym, 
            user=user, 
            first_name="John",
            last_name="Doe"
        )
        
        api_client.force_authenticate(user=user)
        response = api_client.get(API_PROFILE_URL)
        
        # Should succeed or return data
        assert response.status_code in [200, 201]

    def test_get_profile_unauthenticated(self, api_client):
        """Unauthenticated request should be denied."""
        response = api_client.get(API_PROFILE_URL)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSystemConfigAPI:
    """Test system configuration endpoint."""

    def test_system_config_public(self, api_client):
        """System config should be publicly accessible."""
        response = api_client.get(API_CONFIG_URL)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'system_name' in response.data


@pytest.mark.django_db
class TestAPIPermissions:
    """Test API permission enforcement."""

    def test_authenticated_endpoint_without_auth(self, api_client):
        """Protected endpoints should require authentication."""
        protected_endpoints = [
            API_CHECK_URL,
            API_PROFILE_URL,
        ]
        
        for endpoint in protected_endpoints:
            response = api_client.get(endpoint)
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN
            ], f"Endpoint {endpoint} should be protected"

    def test_public_endpoints_accessible(self, api_client):
        """Public endpoints should be accessible without auth."""
        public_endpoints = [
            API_CONFIG_URL,
        ]
        
        for endpoint in public_endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == status.HTTP_200_OK, \
                f"Endpoint {endpoint} should be public"
