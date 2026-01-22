"""
Comprehensive Tests for Staff Roles and Permissions System

This module provides exhaustive testing for the permission system including:
- Permission model operations
- GymMembership and FranchiseMembership models
- user_has_gym_permission function
- require_gym_permission decorator
- Role (Django Groups) management

Test Categories:
1. Model Tests - CRUD operations for permission-related models
2. Permission Logic Tests - user_has_gym_permission function
3. Decorator Tests - require_gym_permission behavior
4. Role Management Tests - Django Groups with custom permissions
5. Edge Cases - Boundary conditions and error handling
"""

from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal
from unittest.mock import patch, MagicMock

from accounts.models_memberships import Permission as CustomPermission, GymMembership, FranchiseMembership
from accounts.permissions import user_has_gym_permission
from accounts.decorators import require_gym_permission
from organizations.models import Franchise, Gym
from staff.models import StaffProfile
from staff.perms import PERMISSION_STRUCTURE, get_all_managed_permissions


User = get_user_model()


class PermissionModelTests(TestCase):
    """Tests for the custom Permission model"""
    
    def test_create_permission(self):
        """Test creating a new permission"""
        perm = CustomPermission.objects.create(
            code="test.view",
            label="Ver Test"
        )
        self.assertEqual(perm.code, "test.view")
        self.assertEqual(perm.label, "Ver Test")
        self.assertEqual(str(perm), "test.view")
    
    def test_permission_code_unique(self):
        """Test that permission codes must be unique"""
        CustomPermission.objects.create(code="unique.perm", label="Unique 1")
        with self.assertRaises(Exception):
            CustomPermission.objects.create(code="unique.perm", label="Unique 2")
    
    def test_permission_str_method(self):
        """Test string representation of permission"""
        perm = CustomPermission.objects.create(code="clients.create", label="Crear Clientes")
        self.assertEqual(str(perm), "clients.create")
    
    def test_permission_with_long_code(self):
        """Test permission with maximum length code"""
        long_code = "a" * 100
        perm = CustomPermission.objects.create(code=long_code, label="Long code")
        self.assertEqual(len(perm.code), 100)
    
    def test_permission_with_special_characters(self):
        """Test permission with special characters in code"""
        perm = CustomPermission.objects.create(
            code="module.sub-module_action",
            label="Special Characters"
        )
        self.assertEqual(perm.code, "module.sub-module_action")


class FranchiseMembershipModelTests(TestCase):
    """Tests for the FranchiseMembership model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@test.com",
            password="testpass123"
        )
        self.franchise = Franchise.objects.create(name="Test Franchise")
    
    def test_create_franchise_membership(self):
        """Test creating a franchise membership"""
        membership = FranchiseMembership.objects.create(
            user=self.user,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        self.assertEqual(membership.user, self.user)
        self.assertEqual(membership.franchise, self.franchise)
        self.assertEqual(membership.role, "OWNER")
    
    def test_franchise_membership_unique_together(self):
        """Test that user+franchise+role combination must be unique"""
        FranchiseMembership.objects.create(
            user=self.user,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        with self.assertRaises(Exception):
            FranchiseMembership.objects.create(
                user=self.user,
                franchise=self.franchise,
                role=FranchiseMembership.Role.OWNER
            )
    
    def test_franchise_membership_str_method(self):
        """Test string representation"""
        membership = FranchiseMembership.objects.create(
            user=self.user,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        self.assertIn(str(self.user), str(membership))
        self.assertIn(str(self.franchise), str(membership))
    
    def test_franchise_membership_created_at(self):
        """Test created_at is automatically set"""
        membership = FranchiseMembership.objects.create(
            user=self.user,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        self.assertIsNotNone(membership.created_at)


class GymMembershipModelTests(TestCase):
    """Tests for the GymMembership model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email="staff@test.com",
            password="testpass123"
        )
        self.franchise = Franchise.objects.create(name="Test Franchise")
        self.gym = Gym.objects.create(name="Test Gym", franchise=self.franchise)
        
        # Create some custom permissions
        self.view_clients = CustomPermission.objects.create(code="clients.view", label="Ver Clientes")
        self.edit_clients = CustomPermission.objects.create(code="clients.edit", label="Editar Clientes")
    
    def test_create_admin_membership(self):
        """Test creating an admin gym membership"""
        membership = GymMembership.objects.create(
            user=self.user,
            gym=self.gym,
            role=GymMembership.Role.ADMIN,
            is_active=True
        )
        self.assertEqual(membership.role, "ADMIN")
        self.assertTrue(membership.is_active)
    
    def test_create_staff_membership_with_permissions(self):
        """Test creating a staff membership with specific permissions"""
        membership = GymMembership.objects.create(
            user=self.user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(self.view_clients)
        
        self.assertEqual(membership.role, "STAFF")
        self.assertIn(self.view_clients, membership.permissions.all())
    
    def test_gym_membership_unique_together(self):
        """Test that user+gym combination must be unique"""
        GymMembership.objects.create(
            user=self.user,
            gym=self.gym,
            role=GymMembership.Role.ADMIN
        )
        with self.assertRaises(Exception):
            GymMembership.objects.create(
                user=self.user,
                gym=self.gym,
                role=GymMembership.Role.STAFF
            )
    
    def test_inactive_membership(self):
        """Test inactive membership"""
        membership = GymMembership.objects.create(
            user=self.user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=False
        )
        self.assertFalse(membership.is_active)
    
    def test_add_multiple_permissions(self):
        """Test adding multiple permissions to membership"""
        membership = GymMembership.objects.create(
            user=self.user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(self.view_clients, self.edit_clients)
        
        self.assertEqual(membership.permissions.count(), 2)
    
    def test_remove_permission(self):
        """Test removing a permission from membership"""
        membership = GymMembership.objects.create(
            user=self.user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(self.view_clients, self.edit_clients)
        membership.permissions.remove(self.view_clients)
        
        self.assertEqual(membership.permissions.count(), 1)
        self.assertNotIn(self.view_clients, membership.permissions.all())
    
    def test_clear_all_permissions(self):
        """Test clearing all permissions"""
        membership = GymMembership.objects.create(
            user=self.user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(self.view_clients, self.edit_clients)
        membership.permissions.clear()
        
        self.assertEqual(membership.permissions.count(), 0)


class UserHasGymPermissionTests(TestCase):
    """Tests for the user_has_gym_permission function - Core permission logic"""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name="Test Franchise")
        self.gym = Gym.objects.create(name="Test Gym", franchise=self.franchise)
        self.other_gym = Gym.objects.create(name="Other Gym", franchise=self.franchise)
        
        # Create custom permissions
        self.view_clients = CustomPermission.objects.create(code="clients.view", label="Ver Clientes")
        self.edit_clients = CustomPermission.objects.create(code="clients.edit", label="Editar Clientes")
        self.manage_staff = CustomPermission.objects.create(code="staff.manage", label="Gestionar Staff")
    
    def test_superuser_always_has_permission(self):
        """Test that superusers always have all permissions"""
        superuser = User.objects.create_superuser(
            email="super@test.com",
            password="testpass123"
        )
        self.assertTrue(user_has_gym_permission(superuser, self.gym.id, "any.permission"))
        self.assertTrue(user_has_gym_permission(superuser, self.gym.id, "clients.view"))
        self.assertTrue(user_has_gym_permission(superuser, self.gym.id, "nonexistent.perm"))
    
    def test_superuser_has_permission_without_membership(self):
        """Test superuser doesn't need gym membership"""
        superuser = User.objects.create_superuser(
            email="super@test.com",
            password="testpass123"
        )
        # No membership created
        self.assertTrue(user_has_gym_permission(superuser, self.gym.id, "clients.view"))
    
    def test_franchise_owner_has_all_permissions(self):
        """Test that franchise owners have all permissions on gyms in their franchise"""
        owner = User.objects.create_user(email="owner@test.com", password="testpass123")
        FranchiseMembership.objects.create(
            user=owner,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        
        self.assertTrue(user_has_gym_permission(owner, self.gym.id, "clients.view"))
        self.assertTrue(user_has_gym_permission(owner, self.gym.id, "any.permission"))
        self.assertTrue(user_has_gym_permission(owner, self.other_gym.id, "any.permission"))
    
    def test_franchise_owner_all_gyms_in_franchise(self):
        """Test franchise owner has access to ALL gyms in their franchise"""
        owner = User.objects.create_user(email="owner@test.com", password="testpass123")
        FranchiseMembership.objects.create(
            user=owner,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        
        # Create multiple gyms in same franchise
        gym2 = Gym.objects.create(name="Gym 2", franchise=self.franchise)
        gym3 = Gym.objects.create(name="Gym 3", franchise=self.franchise)
        
        self.assertTrue(user_has_gym_permission(owner, self.gym.id, "any.permission"))
        self.assertTrue(user_has_gym_permission(owner, gym2.id, "any.permission"))
        self.assertTrue(user_has_gym_permission(owner, gym3.id, "any.permission"))
    
    def test_franchise_owner_no_permission_other_franchise(self):
        """Test franchise owner has NO permissions on other franchises"""
        owner = User.objects.create_user(email="owner@test.com", password="testpass123")
        FranchiseMembership.objects.create(
            user=owner,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        
        # Create gym in different franchise
        other_franchise = Franchise.objects.create(name="Other Franchise")
        other_gym = Gym.objects.create(name="Other Franchise Gym", franchise=other_franchise)
        
        self.assertFalse(user_has_gym_permission(owner, other_gym.id, "clients.view"))
    
    def test_gym_admin_has_all_permissions(self):
        """Test that gym admins have all permissions on their gym"""
        admin = User.objects.create_user(email="admin@test.com", password="testpass123")
        GymMembership.objects.create(
            user=admin,
            gym=self.gym,
            role=GymMembership.Role.ADMIN,
            is_active=True
        )
        
        self.assertTrue(user_has_gym_permission(admin, self.gym.id, "clients.view"))
        self.assertTrue(user_has_gym_permission(admin, self.gym.id, "staff.manage"))
        self.assertTrue(user_has_gym_permission(admin, self.gym.id, "any.permission"))
    
    def test_gym_admin_no_permission_other_gym(self):
        """Test that gym admins don't have permissions on other gyms"""
        admin = User.objects.create_user(email="admin@test.com", password="testpass123")
        GymMembership.objects.create(
            user=admin,
            gym=self.gym,
            role=GymMembership.Role.ADMIN,
            is_active=True
        )
        
        self.assertFalse(user_has_gym_permission(admin, self.other_gym.id, "clients.view"))
    
    def test_staff_with_explicit_permission(self):
        """Test staff with explicitly granted permissions"""
        staff = User.objects.create_user(email="staff@test.com", password="testpass123")
        membership = GymMembership.objects.create(
            user=staff,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(self.view_clients)
        
        self.assertTrue(user_has_gym_permission(staff, self.gym.id, "clients.view"))
        self.assertFalse(user_has_gym_permission(staff, self.gym.id, "clients.edit"))
    
    def test_staff_without_permission(self):
        """Test staff without specific permission"""
        staff = User.objects.create_user(email="staff@test.com", password="testpass123")
        GymMembership.objects.create(
            user=staff,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        
        self.assertFalse(user_has_gym_permission(staff, self.gym.id, "clients.view"))
    
    def test_inactive_membership_no_permission(self):
        """Test that inactive memberships don't grant permissions"""
        staff = User.objects.create_user(email="staff@test.com", password="testpass123")
        membership = GymMembership.objects.create(
            user=staff,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=False
        )
        membership.permissions.add(self.view_clients)
        
        self.assertFalse(user_has_gym_permission(staff, self.gym.id, "clients.view"))
    
    def test_inactive_admin_no_permission(self):
        """Test that inactive admin memberships don't grant permissions"""
        admin = User.objects.create_user(email="admin@test.com", password="testpass123")
        GymMembership.objects.create(
            user=admin,
            gym=self.gym,
            role=GymMembership.Role.ADMIN,
            is_active=False
        )
        
        self.assertFalse(user_has_gym_permission(admin, self.gym.id, "any.permission"))
    
    def test_no_membership_no_permission(self):
        """Test that users without any membership have no permission"""
        user = User.objects.create_user(email="nobody@test.com", password="testpass123")
        
        self.assertFalse(user_has_gym_permission(user, self.gym.id, "clients.view"))
    
    def test_nonexistent_gym(self):
        """Test permission check for non-existent gym"""
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        
        self.assertFalse(user_has_gym_permission(user, 99999, "clients.view"))
    
    def test_multiple_permissions(self):
        """Test staff with multiple permissions"""
        staff = User.objects.create_user(email="staff@test.com", password="testpass123")
        membership = GymMembership.objects.create(
            user=staff,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(self.view_clients, self.edit_clients)
        
        self.assertTrue(user_has_gym_permission(staff, self.gym.id, "clients.view"))
        self.assertTrue(user_has_gym_permission(staff, self.gym.id, "clients.edit"))
        self.assertFalse(user_has_gym_permission(staff, self.gym.id, "staff.manage"))
    
    def test_permission_check_case_sensitive(self):
        """Test that permission codes are case-sensitive"""
        staff = User.objects.create_user(email="staff@test.com", password="testpass123")
        membership = GymMembership.objects.create(
            user=staff,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(self.view_clients)
        
        self.assertTrue(user_has_gym_permission(staff, self.gym.id, "clients.view"))
        self.assertFalse(user_has_gym_permission(staff, self.gym.id, "CLIENTS.VIEW"))
        self.assertFalse(user_has_gym_permission(staff, self.gym.id, "Clients.View"))


class RequireGymPermissionDecoratorTests(TestCase):
    """Tests for the require_gym_permission decorator"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.franchise = Franchise.objects.create(name="Test Franchise")
        self.gym = Gym.objects.create(name="Test Gym", franchise=self.franchise)
        
        self.view_perm = CustomPermission.objects.create(code="test.view", label="Ver Test")
        
        # Create a simple view for testing
        @require_gym_permission("test.view")
        def test_view(request):
            return MagicMock(status_code=200)
        
        self.test_view = test_view
    
    def test_decorator_no_gym_in_session(self):
        """Test decorator redirects when no gym in session"""
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        
        request = self.factory.get('/test/')
        request.user = user
        request.session = {}
        
        response = self.test_view(request)
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_decorator_no_permission(self):
        """Test decorator redirects when user lacks permission"""
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        
        request = self.factory.get('/test/')
        request.user = user
        request.session = {'current_gym_id': self.gym.id}
        
        response = self.test_view(request)
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_decorator_with_permission(self):
        """Test decorator allows access when user has permission"""
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        membership = GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(self.view_perm)
        
        request = self.factory.get('/test/')
        request.user = user
        request.session = {'current_gym_id': self.gym.id}
        
        response = self.test_view(request)
        self.assertEqual(response.status_code, 200)
    
    def test_decorator_admin_always_allowed(self):
        """Test decorator allows admin access"""
        user = User.objects.create_user(email="admin@test.com", password="testpass123")
        GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.ADMIN,
            is_active=True
        )
        
        request = self.factory.get('/test/')
        request.user = user
        request.session = {'current_gym_id': self.gym.id}
        
        response = self.test_view(request)
        self.assertEqual(response.status_code, 200)
    
    def test_decorator_superuser_always_allowed(self):
        """Test decorator allows superuser access"""
        superuser = User.objects.create_superuser(email="super@test.com", password="testpass123")
        
        request = self.factory.get('/test/')
        request.user = superuser
        request.session = {'current_gym_id': self.gym.id}
        
        response = self.test_view(request)
        self.assertEqual(response.status_code, 200)
    
    def test_decorator_franchise_owner_allowed(self):
        """Test decorator allows franchise owner access"""
        owner = User.objects.create_user(email="owner@test.com", password="testpass123")
        FranchiseMembership.objects.create(
            user=owner,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        
        request = self.factory.get('/test/')
        request.user = owner
        request.session = {'current_gym_id': self.gym.id}
        
        response = self.test_view(request)
        self.assertEqual(response.status_code, 200)


class PermissionStructureTests(TestCase):
    """Tests for the PERMISSION_STRUCTURE constant and helper functions"""
    
    def test_permission_structure_not_empty(self):
        """Test that PERMISSION_STRUCTURE has entries"""
        self.assertGreater(len(PERMISSION_STRUCTURE), 0)
    
    def test_permission_structure_has_required_modules(self):
        """Test required modules exist in structure"""
        required_modules = ["Clientes", "Finanzas", "Marketing", "Staff (Equipo)"]
        for module in required_modules:
            self.assertIn(module, PERMISSION_STRUCTURE)
    
    def test_get_all_managed_permissions(self):
        """Test get_all_managed_permissions returns flat list"""
        all_perms = get_all_managed_permissions()
        self.assertIsInstance(all_perms, list)
        self.assertGreater(len(all_perms), 0)
        
        # Check some expected permissions exist
        self.assertIn("view_client", all_perms)
        self.assertIn("view_staffprofile", all_perms)
    
    def test_permission_structure_format(self):
        """Test that each entry has correct format (codename, label)"""
        for module, permissions in PERMISSION_STRUCTURE.items():
            for perm in permissions:
                self.assertEqual(len(perm), 2)  # (codename, label)
                self.assertIsInstance(perm[0], str)  # codename
                self.assertIsInstance(perm[1], str)  # label
    
    def test_no_duplicate_permission_codes(self):
        """Test that there are no duplicate permission codes"""
        all_perms = get_all_managed_permissions()
        self.assertEqual(len(all_perms), len(set(all_perms)))


class HierarchyPermissionTests(TestCase):
    """Tests for permission hierarchy (Superuser > Owner > Admin > Staff)"""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name="Test Franchise")
        self.gym = Gym.objects.create(name="Test Gym", franchise=self.franchise)
        
        self.perm = CustomPermission.objects.create(code="test.action", label="Test Action")
    
    def test_permission_hierarchy_superuser(self):
        """Superuser has highest permission level"""
        superuser = User.objects.create_superuser(
            email="super@test.com",
            password="testpass123"
        )
        self.assertTrue(user_has_gym_permission(superuser, self.gym.id, "any.perm"))
    
    def test_permission_hierarchy_franchise_owner(self):
        """Franchise owner has permissions on all gyms in franchise"""
        owner = User.objects.create_user(email="owner@test.com", password="testpass123")
        FranchiseMembership.objects.create(
            user=owner,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        
        # Create second gym in same franchise
        gym2 = Gym.objects.create(name="Gym 2", franchise=self.franchise)
        
        self.assertTrue(user_has_gym_permission(owner, self.gym.id, "test.action"))
        self.assertTrue(user_has_gym_permission(owner, gym2.id, "test.action"))
    
    def test_permission_hierarchy_franchise_owner_other_franchise(self):
        """Franchise owner has no permissions on other franchises"""
        owner = User.objects.create_user(email="owner@test.com", password="testpass123")
        FranchiseMembership.objects.create(
            user=owner,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        
        # Create gym in different franchise
        other_franchise = Franchise.objects.create(name="Other Franchise")
        other_gym = Gym.objects.create(name="Other Gym", franchise=other_franchise)
        
        self.assertFalse(user_has_gym_permission(owner, other_gym.id, "test.action"))
    
    def test_permission_hierarchy_gym_admin(self):
        """Gym admin has all permissions on their gym only"""
        admin = User.objects.create_user(email="admin@test.com", password="testpass123")
        GymMembership.objects.create(
            user=admin,
            gym=self.gym,
            role=GymMembership.Role.ADMIN,
            is_active=True
        )
        
        # Create second gym
        gym2 = Gym.objects.create(name="Gym 2", franchise=self.franchise)
        
        self.assertTrue(user_has_gym_permission(admin, self.gym.id, "test.action"))
        self.assertFalse(user_has_gym_permission(admin, gym2.id, "test.action"))
    
    def test_permission_hierarchy_staff_explicit_only(self):
        """Staff only has explicitly granted permissions"""
        staff = User.objects.create_user(email="staff@test.com", password="testpass123")
        membership = GymMembership.objects.create(
            user=staff,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        
        # Without explicit permission
        self.assertFalse(user_has_gym_permission(staff, self.gym.id, "test.action"))
        
        # With explicit permission
        membership.permissions.add(self.perm)
        self.assertTrue(user_has_gym_permission(staff, self.gym.id, "test.action"))


class EdgeCaseTests(TestCase):
    """Tests for edge cases and boundary conditions"""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name="Test Franchise")
        self.gym = Gym.objects.create(name="Test Gym", franchise=self.franchise)
    
    def test_user_with_both_admin_and_owner_roles(self):
        """User can be both franchise owner and gym admin"""
        user = User.objects.create_user(email="both@test.com", password="testpass123")
        
        FranchiseMembership.objects.create(
            user=user,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.ADMIN,
            is_active=True
        )
        
        # Should still have all permissions
        self.assertTrue(user_has_gym_permission(user, self.gym.id, "any.perm"))
    
    def test_gym_without_franchise(self):
        """Gym without franchise (standalone gym)"""
        standalone_gym = Gym.objects.create(name="Standalone Gym", franchise=None)
        
        admin = User.objects.create_user(email="admin@test.com", password="testpass123")
        GymMembership.objects.create(
            user=admin,
            gym=standalone_gym,
            role=GymMembership.Role.ADMIN,
            is_active=True
        )
        
        self.assertTrue(user_has_gym_permission(admin, standalone_gym.id, "any.perm"))
    
    def test_multiple_gym_memberships(self):
        """User with memberships to multiple gyms"""
        user = User.objects.create_user(email="multi@test.com", password="testpass123")
        gym2 = Gym.objects.create(name="Gym 2", franchise=self.franchise)
        
        perm1 = CustomPermission.objects.create(code="perm.one", label="Perm One")
        perm2 = CustomPermission.objects.create(code="perm.two", label="Perm Two")
        
        # Admin in gym 1
        GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.ADMIN,
            is_active=True
        )
        
        # Staff in gym 2 with limited permissions
        membership2 = GymMembership.objects.create(
            user=user,
            gym=gym2,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership2.permissions.add(perm1)
        
        # Check permissions per gym
        self.assertTrue(user_has_gym_permission(user, self.gym.id, "perm.one"))  # Admin - all perms
        self.assertTrue(user_has_gym_permission(user, self.gym.id, "perm.two"))
        
        self.assertTrue(user_has_gym_permission(user, gym2.id, "perm.one"))
        self.assertFalse(user_has_gym_permission(user, gym2.id, "perm.two"))
    
    def test_special_characters_in_permission_code(self):
        """Permission with special characters in code"""
        special_perm = CustomPermission.objects.create(
            code="test.special-chars_123",
            label="Special Chars"
        )
        
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        membership = GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(special_perm)
        
        self.assertTrue(user_has_gym_permission(user, self.gym.id, "test.special-chars_123"))
    
    def test_admin_empty_permission_code(self):
        """Admin should have permission even for empty permission code"""
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.ADMIN,
            is_active=True
        )
        
        # Admin should still have permission for empty code (returns True for any permission)
        self.assertTrue(user_has_gym_permission(user, self.gym.id, ""))


class StaffProfilePermissionIntegrationTests(TestCase):
    """Integration tests combining StaffProfile with permissions"""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name="Test Franchise")
        self.gym = Gym.objects.create(name="Test Gym", franchise=self.franchise)
        
        self.manager_user = User.objects.create_user(
            email="manager@test.com",
            password="testpass123"
        )
        self.trainer_user = User.objects.create_user(
            email="trainer@test.com",
            password="testpass123"
        )
    
    def test_staff_profile_with_gym_membership(self):
        """Staff profile should be created alongside gym membership"""
        # Create gym membership
        membership = GymMembership.objects.create(
            user=self.manager_user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        
        # Create staff profile
        staff_profile = StaffProfile.objects.create(
            user=self.manager_user,
            gym=self.gym,
            role=StaffProfile.Role.MANAGER
        )
        
        self.assertEqual(staff_profile.gym, self.gym)
        self.assertEqual(staff_profile.role, "MANAGER")
    
    def test_different_staff_roles_same_gym_membership(self):
        """Staff profile role is separate from gym membership role"""
        # Staff membership
        membership = GymMembership.objects.create(
            user=self.trainer_user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        
        # Trainer profile
        staff_profile = StaffProfile.objects.create(
            user=self.trainer_user,
            gym=self.gym,
            role=StaffProfile.Role.TRAINER
        )
        
        # GymMembership role is STAFF (for permissions)
        # StaffProfile role is TRAINER (for scheduling, display)
        self.assertEqual(membership.role, "STAFF")
        self.assertEqual(staff_profile.role, "TRAINER")


class ConcurrencyAndStateChangeTests(TestCase):
    """Tests for permission behavior during state changes"""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name="Test Franchise")
        self.gym = Gym.objects.create(name="Test Gym", franchise=self.franchise)
    
    def test_permission_check_after_membership_deactivation(self):
        """Permission should fail after membership is deactivated"""
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        perm = CustomPermission.objects.create(code="test.perm", label="Test")
        
        membership = GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(perm)
        
        # Has permission
        self.assertTrue(user_has_gym_permission(user, self.gym.id, "test.perm"))
        
        # Deactivate
        membership.is_active = False
        membership.save()
        
        # No longer has permission
        self.assertFalse(user_has_gym_permission(user, self.gym.id, "test.perm"))
    
    def test_permission_check_after_permission_removal(self):
        """Permission should fail after specific permission is removed"""
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        perm = CustomPermission.objects.create(code="test.perm", label="Test")
        
        membership = GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(perm)
        
        # Has permission
        self.assertTrue(user_has_gym_permission(user, self.gym.id, "test.perm"))
        
        # Remove permission
        membership.permissions.remove(perm)
        
        # No longer has permission
        self.assertFalse(user_has_gym_permission(user, self.gym.id, "test.perm"))
    
    def test_role_upgrade_from_staff_to_admin(self):
        """Upgrading from STAFF to ADMIN should grant all permissions"""
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        
        membership = GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        
        # No permission as staff
        self.assertFalse(user_has_gym_permission(user, self.gym.id, "any.perm"))
        
        # Upgrade to admin
        membership.role = GymMembership.Role.ADMIN
        membership.save()
        
        # Now has all permissions
        self.assertTrue(user_has_gym_permission(user, self.gym.id, "any.perm"))
    
    def test_role_downgrade_from_admin_to_staff(self):
        """Downgrading from ADMIN to STAFF should remove all implicit permissions"""
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        
        membership = GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.ADMIN,
            is_active=True
        )
        
        # Has permission as admin
        self.assertTrue(user_has_gym_permission(user, self.gym.id, "any.perm"))
        
        # Downgrade to staff
        membership.role = GymMembership.Role.STAFF
        membership.save()
        
        # No longer has implicit permissions
        self.assertFalse(user_has_gym_permission(user, self.gym.id, "any.perm"))
    
    def test_membership_reactivation(self):
        """Reactivating membership should restore permissions"""
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        perm = CustomPermission.objects.create(code="test.perm", label="Test")
        
        membership = GymMembership.objects.create(
            user=user,
            gym=self.gym,
            role=GymMembership.Role.STAFF,
            is_active=True
        )
        membership.permissions.add(perm)
        
        # Deactivate
        membership.is_active = False
        membership.save()
        self.assertFalse(user_has_gym_permission(user, self.gym.id, "test.perm"))
        
        # Reactivate
        membership.is_active = True
        membership.save()
        self.assertTrue(user_has_gym_permission(user, self.gym.id, "test.perm"))


class RoleGroupManagementTests(TestCase):
    """Tests for Django Group (Role) management functionality"""
    
    def setUp(self):
        # Create a test role/group
        self.test_role = Group.objects.create(name="Test Trainer Role")
    
    def test_create_group(self):
        """Test creating a new Django Group"""
        role = Group.objects.create(name="New Role")
        self.assertTrue(Group.objects.filter(name="New Role").exists())
    
    def test_add_permission_to_group(self):
        """Test adding Django permission to a group"""
        content_type = ContentType.objects.get_for_model(StaffProfile)
        perm, _ = Permission.objects.get_or_create(
            codename='test_perm',
            content_type=content_type,
            defaults={'name': 'Test Permission'}
        )
        
        self.test_role.permissions.add(perm)
        self.assertIn(perm, self.test_role.permissions.all())
    
    def test_remove_permission_from_group(self):
        """Test removing permission from group"""
        content_type = ContentType.objects.get_for_model(StaffProfile)
        perm, _ = Permission.objects.get_or_create(
            codename='test_perm',
            content_type=content_type,
            defaults={'name': 'Test Permission'}
        )
        
        self.test_role.permissions.add(perm)
        self.test_role.permissions.remove(perm)
        
        self.assertNotIn(perm, self.test_role.permissions.all())
    
    def test_group_name_unique(self):
        """Test that group names must be unique"""
        with self.assertRaises(Exception):
            Group.objects.create(name="Test Trainer Role")


class OwnerWithoutFranchiseMembershipTests(TestCase):
    """Test scenarios where franchise ownership structure varies"""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name="Test Franchise")
        self.gym = Gym.objects.create(name="Test Gym", franchise=self.franchise)
    
    def test_user_is_admin_but_franchise_has_owner(self):
        """Gym admin should work even when franchise has a different owner"""
        owner = User.objects.create_user(email="owner@test.com", password="testpass123")
        FranchiseMembership.objects.create(
            user=owner,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        
        admin = User.objects.create_user(email="admin@test.com", password="testpass123")
        GymMembership.objects.create(
            user=admin,
            gym=self.gym,
            role=GymMembership.Role.ADMIN,
            is_active=True
        )
        
        # Both should have permissions
        self.assertTrue(user_has_gym_permission(owner, self.gym.id, "any.perm"))
        self.assertTrue(user_has_gym_permission(admin, self.gym.id, "any.perm"))
    
    def test_franchise_with_multiple_owners(self):
        """Multiple owners should all have permissions"""
        owner1 = User.objects.create_user(email="owner1@test.com", password="testpass123")
        owner2 = User.objects.create_user(email="owner2@test.com", password="testpass123")
        
        FranchiseMembership.objects.create(
            user=owner1,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        FranchiseMembership.objects.create(
            user=owner2,
            franchise=self.franchise,
            role=FranchiseMembership.Role.OWNER
        )
        
        self.assertTrue(user_has_gym_permission(owner1, self.gym.id, "any.perm"))
        self.assertTrue(user_has_gym_permission(owner2, self.gym.id, "any.perm"))
