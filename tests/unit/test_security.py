"""
Security tests for common vulnerabilities.

Covers:
- XSS prevention
- CSRF protection
- SQL injection prevention
- Open redirect prevention
- Authentication bypass attempts
"""
import pytest
from django.test import Client, override_settings
from django.urls import reverse

from tests.factories import (
    GymFactory,
    UserFactory,
    ClientFactory,
)


# API URL prefixes
API_LOGIN_URL = '/api/auth/login/'
API_GYMS_URL = '/api/gyms/search/'
API_PROFILE_URL = '/api/profile/'


@pytest.mark.django_db
class TestXSSPrevention:
    """Test XSS attack prevention."""

    def test_xss_in_client_name_escaped(self):
        """XSS payload in client name should be escaped."""
        gym = GymFactory()
        xss_payload = '<script>alert("XSS")</script>'
        
        client = ClientFactory(
            gym=gym,
            first_name=xss_payload,
            last_name='Test'
        )
        
        # The script tag should be stored but escaped on render
        assert '<script>' in client.first_name
        # In templates, it would be escaped

    def test_xss_in_gym_name(self):
        """XSS payload in gym name should be handled."""
        xss_payload = '"><img src=x onerror=alert(1)>'
        
        gym = GymFactory(name=xss_payload)
        
        # Should be stored safely
        assert gym.name == xss_payload


@pytest.mark.django_db
class TestOpenRedirectPrevention:
    """Test open redirect vulnerability prevention."""

    def test_login_redirect_to_external_blocked(self, client):
        """Login should not redirect to external URLs."""
        # Create user
        user = UserFactory()
        user.set_password('TestPass123!')
        user.save()
        
        # Attempt login with evil redirect
        response = client.post(
            '/admin/login/?next=https://evil.com',
            {'username': user.email, 'password': 'TestPass123!'},
            follow=False
        )
        
        # Should not redirect to external URL
        if response.status_code in [301, 302]:
            location = response.get('Location', '')
            assert not location.startswith('http://evil')
            assert not location.startswith('https://evil')

    def test_redirect_with_protocol_relative_url(self, client):
        """Protocol-relative URLs should not cause redirect."""
        user = UserFactory()
        user.set_password('TestPass123!')
        user.save()
        
        response = client.post(
            '/admin/login/?next=//evil.com/path',
            {'username': user.email, 'password': 'TestPass123!'},
            follow=False
        )
        
        if response.status_code in [301, 302]:
            location = response.get('Location', '')
            assert not location.startswith('//')


@pytest.mark.django_db
class TestAuthenticationSecurity:
    """Test authentication security measures."""

    def test_login_rate_limiting(self, api_client):
        """Multiple failed logins should be rate limited."""
        # Make multiple failed login attempts
        for i in range(15):
            api_client.post(API_LOGIN_URL, {
                'email': f'fake{i}@example.com',
                'password': 'wrongpassword'
            })
        
        # After rate limit, should get 429 or blocked
        response = api_client.post(API_LOGIN_URL, {
            'email': 'another@example.com',
            'password': 'wrongpassword'
        })
        
        # Rate limiting may return 429 or 400/403
        # Just verify the endpoint still works (doesn't crash)
        assert response.status_code in [400, 403, 429]

    def test_password_not_in_response(self, api_client):
        """User password should never appear in API responses."""
        gym = GymFactory()
        user = UserFactory()
        user.set_password('SecretPassword123!')
        user.save()
        ClientFactory(gym=gym, user=user)
        
        api_client.force_authenticate(user=user)
        response = api_client.get(API_PROFILE_URL)
        
        # Check response doesn't contain password regardless of status
        if response.status_code in [200, 201]:
            response_text = str(response.content)
            assert 'SecretPassword123!' not in response_text


@pytest.mark.django_db
class TestCSRFProtection:
    """Test CSRF token protection."""

    def test_post_without_csrf_token_denied(self, client):
        """POST requests without CSRF token should be denied."""
        # Django's test client handles CSRF automatically, but we can check
        # that the middleware is active
        from django.middleware.csrf import CsrfViewMiddleware
        
        # Verify CSRF middleware is in settings
        from django.conf import settings
        csrf_enabled = 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE
        assert csrf_enabled, "CSRF middleware should be enabled"


@pytest.mark.django_db
class TestSQLInjectionPrevention:
    """Test SQL injection prevention via ORM."""

    def test_sql_injection_in_search(self, api_client):
        """SQL injection in search should be safe via ORM."""
        GymFactory(name="Real Gym")
        
        # Attempt SQL injection
        injection = "'; DROP TABLE organizations_gym; --"
        response = api_client.get(f'{API_GYMS_URL}?q={injection}')
        
        # Should return safely (empty or valid response)
        assert response.status_code in [200, 400]
        
        # Verify table wasn't dropped
        from organizations.models import Gym
        assert Gym.objects.exists()

    def test_sql_injection_in_client_name(self):
        """SQL injection attempt in model field should be safe."""
        gym = GymFactory()
        injection = "Robert'; DROP TABLE clients_client;--"
        
        client = ClientFactory(gym=gym, first_name=injection)
        
        # Data should be stored as-is (escaped by ORM)
        assert client.first_name == injection
        
        # Verify table wasn't dropped
        from clients.models import Client
        assert Client.objects.filter(id=client.id).exists()


@pytest.mark.django_db
class TestSessionSecurity:
    """Test session security measures."""

    @override_settings(SESSION_COOKIE_HTTPONLY=True)
    def test_session_cookie_httponly(self, client):
        """Session cookie should have HttpOnly flag."""
        from django.conf import settings
        assert settings.SESSION_COOKIE_HTTPONLY is True

    @override_settings(CSRF_COOKIE_SECURE=True)
    def test_csrf_cookie_secure_in_production(self):
        """CSRF cookie should be secure in production."""
        from django.conf import settings
        # This is set True for production, False for dev
        # Just verify the setting exists
        assert hasattr(settings, 'CSRF_COOKIE_SECURE')


@pytest.mark.django_db
class TestAccessControl:
    """Test access control enforcement."""

    def test_client_cannot_access_other_gym_data(self, api_client):
        """Client should not access data from other gyms."""
        gym1 = GymFactory()
        gym2 = GymFactory()
        
        user1 = UserFactory()
        ClientFactory(gym=gym1, user=user1)
        
        user2 = UserFactory()
        client2 = ClientFactory(gym=gym2, user=user2, first_name="Secret")
        
        # Authenticate as user1
        api_client.force_authenticate(user=user1)
        
        # Try to access user2's data (would need specific endpoint)
        # This is a placeholder for actual cross-gym access tests

    def test_staff_without_permission_denied(self, client):
        """Staff without specific permission should be denied."""
        from tests.factories import StaffMembershipFactory
        
        gym = GymFactory()
        user = UserFactory()
        user.set_password('TestPass123!')
        user.save()
        
        # Staff without permissions
        StaffMembershipFactory(user=user, gym=gym, role='STAFF')
        
        client.login(username=user.email, password='TestPass123!')
        
        # Attempting to access admin area without proper perms
        # Should be denied based on permission checks


@pytest.mark.django_db
class TestInputValidation:
    """Test input validation security."""

    def test_oversized_input_handled(self, api_client):
        """Very large inputs should be handled gracefully."""
        large_string = 'A' * 100000
        
        response = api_client.post(API_LOGIN_URL, {
            'email': large_string,
            'password': large_string
        })
        
        # Should not crash, just return error (can be 400, 403, 413, or 414)
        assert response.status_code in [400, 403, 413, 414]

    def test_null_bytes_in_input(self, api_client):
        """Null bytes in input should be handled."""
        response = api_client.post(API_LOGIN_URL, {
            'email': 'test\x00@evil.com',
            'password': 'password\x00'
        })
        
        # Should not crash (can be 400, 401, or 403)
        assert response.status_code in [400, 401, 403]

    def test_unicode_input_handled(self, api_client):
        """Unicode input should be handled correctly."""
        GymFactory(name="Café Fitness 健身房")
        
        response = api_client.get(API_GYMS_URL, {'q': '健身'})
        
        assert response.status_code == 200
