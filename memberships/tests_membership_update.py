"""
Tests exhaustivos para la funcionalidad de actualización de membresías existentes
al editar planes de membresía.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from organizations.models import Gym, Franchise
from memberships.models import MembershipPlan
from clients.models import Client as ClientModel, ClientMembership

User = get_user_model()


class MembershipPlanUpdateTestCase(TestCase):
    """Tests para actualización de planes de membresía"""
    
    def setUp(self):
        """Configuración inicial para todos los tests"""
        # Crear franquicia y gimnasio
        self.franchise = Franchise.objects.create(
            name='Test Franchise'
        )
        
        self.gym = Gym.objects.create(
            franchise=self.franchise,
            name='Test Gym',
            commercial_name='Test Gym',
        )
        
        # Crear usuario con permisos (será dueño de la franquicia)
        self.user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            is_superuser=True,  # Simplificamos usando superuser
            is_staff=True
        )
        
        # Agregar como owner de la franquicia
        self.franchise.owners.add(self.user)
        
        # Crear plan de membresía
        self.plan = MembershipPlan.objects.create(
            gym=self.gym,
            name='Plan Mensual Original',
            base_price=Decimal('50.00'),
            is_recurring=True,
            frequency_amount=1,
            frequency_unit='MONTH'
        )
        
        # Crear clientes de prueba
        self.client1 = ClientModel.objects.create(
            gym=self.gym,
            first_name='Juan',
            last_name='Pérez',
            email='juan@test.com',
            status='ACTIVE'
        )
        
        self.client2 = ClientModel.objects.create(
            gym=self.gym,
            first_name='María',
            last_name='García',
            email='maria@test.com',
            status='ACTIVE'
        )
        
        self.client3 = ClientModel.objects.create(
            gym=self.gym,
            first_name='Pedro',
            last_name='López',
            email='pedro@test.com',
            status='INACTIVE'
        )
        
        # Cliente HTTP
        self.http_client = Client()
        self.http_client.login(email='admin@test.com', password='testpass123')
        
        # Guardar el ID del gym en sesión
        session = self.http_client.session
        session['current_gym_id'] = self.gym.id
        session.save()
    
    def test_create_plan_no_update_option(self):
        """Al crear un plan nuevo, no debe aparecer la opción de actualizar membresías"""
        url = reverse('membership_plan_create')
        response = self.http_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # No debe aparecer el texto de actualización
        self.assertNotContains(response, 'Actualizar Clientes Existentes')
        self.assertNotContains(response, 'update_existing_memberships')
    
    def test_edit_plan_shows_update_option(self):
        """Al editar un plan, debe aparecer la opción de actualizar membresías"""
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        response = self.http_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Actualizar Clientes Existentes')
        self.assertContains(response, 'update_existing_memberships')
    
    def test_edit_plan_with_no_active_memberships(self):
        """Al editar un plan sin membresías activas, debe mostrar mensaje informativo"""
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        response = self.http_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay clientes con membresías activas')
        self.assertEqual(response.context['affected_memberships_count'], 0)
    
    def test_edit_plan_counts_active_memberships_correctly(self):
        """Debe contar correctamente solo las membresías activas, pendientes y en proceso de pago"""
        # Crear membresía activa
        active_membership = ClientMembership.objects.create(
            client=self.client1,
            gym=self.gym,
            plan=self.plan,
            name=self.plan.name,
            start_date=date.today(),
            price=self.plan.base_price,
            status='ACTIVE'
        )
        
        # Crear membresía pendiente
        pending_membership = ClientMembership.objects.create(
            client=self.client2,
            gym=self.gym,
            plan=self.plan,
            name=self.plan.name,
            start_date=date.today(),
            price=self.plan.base_price,
            status='PENDING'
        )
        
        # Crear membresía cancelada (NO debe contarse)
        cancelled_membership = ClientMembership.objects.create(
            client=self.client3,
            gym=self.gym,
            plan=self.plan,
            name=self.plan.name,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() - timedelta(days=1),
            price=self.plan.base_price,
            status='CANCELLED'
        )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        response = self.http_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Debe contar solo las activas y pendientes (2), no la cancelada
        self.assertEqual(response.context['affected_memberships_count'], 2)
        self.assertContains(response, '2 membresías activas')
    
    def test_update_plan_without_checkbox_does_not_update_memberships(self):
        """Al guardar sin marcar el checkbox, no debe actualizar membresías existentes"""
        # Crear membresía activa
        membership = ClientMembership.objects.create(
            client=self.client1,
            gym=self.gym,
            plan=self.plan,
            name=self.plan.name,
            start_date=date.today(),
            price=self.plan.base_price,
            status='ACTIVE'
        )
        
        original_name = membership.name
        original_price = membership.price
        
        # Actualizar el plan sin marcar el checkbox
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        response = self.http_client.post(url, {
            'name': 'Plan Mensual Actualizado',
            'base_price': '75.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': True,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            # NO incluimos 'update_existing_memberships'
        })
        
        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 302)
        
        # Recargar la membresía desde la base de datos
        membership.refresh_from_db()
        
        # La membresía NO debe haberse actualizado
        self.assertEqual(membership.name, original_name)
        self.assertEqual(membership.price, original_price)
        
        # El plan sí debe haberse actualizado
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.name, 'Plan Mensual Actualizado')
        self.assertEqual(self.plan.base_price, Decimal('75.00'))
    
    def test_update_plan_with_checkbox_updates_memberships(self):
        """Al marcar el checkbox, debe actualizar todas las membresías activas"""
        # Crear varias membresías
        membership1 = ClientMembership.objects.create(
            client=self.client1,
            gym=self.gym,
            plan=self.plan,
            name='Old Name 1',
            start_date=date.today(),
            price=Decimal('50.00'),
            status='ACTIVE'
        )
        
        membership2 = ClientMembership.objects.create(
            client=self.client2,
            gym=self.gym,
            plan=self.plan,
            name='Old Name 2',
            start_date=date.today(),
            price=Decimal('50.00'),
            status='PENDING_PAYMENT'
        )
        
        # Actualizar el plan CON el checkbox marcado
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        response = self.http_client.post(url, {
            'name': 'Plan Premium',
            'base_price': '99.99',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': True,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',  # CHECKBOX MARCADO
        })
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        
        # Recargar membresías
        membership1.refresh_from_db()
        membership2.refresh_from_db()
        
        # Ambas membresías deben haberse actualizado
        self.assertEqual(membership1.name, 'Plan Premium')
        self.assertEqual(membership1.price, Decimal('99.99'))
        self.assertEqual(membership2.name, 'Plan Premium')
        self.assertEqual(membership2.price, Decimal('99.99'))
    
    def test_update_only_affects_active_statuses(self):
        """La actualización solo debe afectar a membresías activas, pendientes o en proceso de pago"""
        # Crear membresías con diferentes estados
        active = ClientMembership.objects.create(
            client=self.client1,
            gym=self.gym,
            plan=self.plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=date.today()
        )
        
        expired = ClientMembership.objects.create(
            client=self.client2,
            gym=self.gym,
            plan=self.plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='EXPIRED',
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=1)
        )
        
        cancelled = ClientMembership.objects.create(
            client=self.client3,
            gym=self.gym,
            plan=self.plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='CANCELLED',
            start_date=date.today()
        )
        
        # Actualizar con checkbox marcado
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'Plan Nuevo',
            'base_price': '80.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': True,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        # Recargar
        active.refresh_from_db()
        expired.refresh_from_db()
        cancelled.refresh_from_db()
        
        # Solo la activa debe actualizarse
        self.assertEqual(active.name, 'Plan Nuevo')
        self.assertEqual(active.price, Decimal('80.00'))
        
        # Las demás NO deben cambiar
        self.assertEqual(expired.name, 'Old Name')
        self.assertEqual(expired.price, Decimal('50.00'))
        self.assertEqual(cancelled.name, 'Old Name')
        self.assertEqual(cancelled.price, Decimal('50.00'))
    
    def test_success_message_shows_update_count(self):
        """El mensaje de éxito debe mostrar cuántas membresías se actualizaron"""
        # Crear 3 membresías activas
        for i in range(3):
            ClientMembership.objects.create(
                client=self.client1 if i == 0 else self.client2 if i == 1 else self.client3,
                gym=self.gym,
                plan=self.plan,
                name='Old',
                price=Decimal('50.00'),
                status='ACTIVE',
                start_date=date.today()
            )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        response = self.http_client.post(url, {
            'name': 'Plan Actualizado',
            'base_price': '60.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': True,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        }, follow=True)
        
        # Verificar mensaje de éxito
        messages = list(response.context['messages'])
        self.assertTrue(any('3 membresías de clientes antiguos' in str(m) for m in messages))
    
    def test_success_message_without_update(self):
        """Si no se actualiza, el mensaje debe indicar que solo afecta a nuevos clientes"""
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        response = self.http_client.post(url, {
            'name': 'Plan Actualizado',
            'base_price': '60.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': True,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            # NO marcamos el checkbox
        }, follow=True)
        
        # Verificar mensaje
        messages = list(response.context['messages'])
        self.assertTrue(any('solo afecta a nuevos clientes' in str(m) for m in messages))
    
    def test_update_preserves_other_membership_fields(self):
        """La actualización solo debe cambiar nombre y precio, no otros campos"""
        # Crear membresía con datos completos
        original_start = date.today() - timedelta(days=10)
        original_end = date.today() + timedelta(days=20)
        
        membership = ClientMembership.objects.create(
            client=self.client1,
            gym=self.gym,
            plan=self.plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=original_start,
            end_date=original_end,
            is_recurring=True,
            sessions_total=10,
            sessions_used=3
        )
        
        # Actualizar plan
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'New Name',
            'base_price': '75.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': True,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        
        # Verificar que solo cambiaron nombre y precio
        self.assertEqual(membership.name, 'New Name')
        self.assertEqual(membership.price, Decimal('75.00'))
        
        # El resto debe permanecer igual
        self.assertEqual(membership.start_date, original_start)
        self.assertEqual(membership.end_date, original_end)
        self.assertEqual(membership.status, 'ACTIVE')
        self.assertEqual(membership.sessions_total, 10)
        self.assertEqual(membership.sessions_used, 3)
        self.assertTrue(membership.is_recurring)
    
    def test_update_works_with_multiple_gyms(self):
        """Solo debe actualizar membresías del gimnasio actual, no de otros"""
        # Crear otro gimnasio
        other_gym = Gym.objects.create(
            franchise=self.franchise,
            name='Other Gym',
            slug='other-gym'
        )
        
        # Crear plan igual en el otro gimnasio
        other_plan = MembershipPlan.objects.create(
            gym=other_gym,
            name='Plan Mensual Original',
            base_price=Decimal('50.00'),
            is_recurring=True
        )
        
        # Crear cliente y membresía en el otro gimnasio
        other_client = Client.objects.create(
            gym=other_gym,
            first_name='Carlos',
            last_name='Otro',
            email='carlos@test.com'
        )
        
        other_membership = ClientMembership.objects.create(
            client=other_client,
            gym=other_gym,
            plan=other_plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=date.today()
        )
        
        # Crear membresía en nuestro gimnasio
        our_membership = ClientMembership.objects.create(
            client=self.client1,
            gym=self.gym,
            plan=self.plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=date.today()
        )
        
        # Actualizar NUESTRO plan
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'Updated Plan',
            'base_price': '100.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': True,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        # Recargar
        our_membership.refresh_from_db()
        other_membership.refresh_from_db()
        
        # Solo nuestra membresía debe actualizarse
        self.assertEqual(our_membership.name, 'Updated Plan')
        self.assertEqual(our_membership.price, Decimal('100.00'))
        
        # La del otro gimnasio NO debe cambiar
        self.assertEqual(other_membership.name, 'Old Name')
        self.assertEqual(other_membership.price, Decimal('50.00'))


class EdgeCasesTestCase(TestCase):
    """Tests para casos extremos y situaciones inusuales"""
    
    def setUp(self):
        """Setup básico"""
        self.franchise = Franchise.objects.create(name='Test', slug='test')
        self.gym = Gym.objects.create(franchise=self.franchise, name='Gym', slug='gym')
        self.user = User.objects.create_user(email='test@test.com', password='pass')
        self.user.current_gym = self.gym
        self.user.save()
        
        self.plan = MembershipPlan.objects.create(
            gym=self.gym,
            name='Plan',
            base_price=Decimal('50.00')
        )
        
        self.http_client = Client()
        self.http_client.login(email='test@test.com', password='pass')
        session = self.http_client.session
        session['current_gym_id'] = self.gym.id
        session.save()
    
    def test_update_with_zero_price(self):
        """Debe poder actualizar a precio 0 (plan gratuito)"""
        client_obj = Client.objects.create(gym=self.gym, first_name='Test', last_name='User')
        membership = ClientMembership.objects.create(
            client=client_obj,
            gym=self.gym,
            plan=self.plan,
            name='Old',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=date.today()
        )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'Plan Gratuito',
            'base_price': '0.00',
            'is_recurring': False,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': False,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        self.assertEqual(membership.price, Decimal('0.00'))
        self.assertEqual(membership.name, 'Plan Gratuito')
    
    def test_update_with_very_high_price(self):
        """Debe manejar precios muy altos correctamente"""
        client_obj = Client.objects.create(gym=self.gym, first_name='Test', last_name='VIP')
        membership = ClientMembership.objects.create(
            client=client_obj,
            gym=self.gym,
            plan=self.plan,
            name='Old',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=date.today()
        )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'Plan Elite',
            'base_price': '999999.99',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'YEAR',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': False,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        self.assertEqual(membership.price, Decimal('999999.99'))
    
    def test_update_with_special_characters_in_name(self):
        """Debe manejar caracteres especiales en el nombre"""
        client_obj = Client.objects.create(gym=self.gym, first_name='Test', last_name='User')
        membership = ClientMembership.objects.create(
            client=client_obj,
            gym=self.gym,
            plan=self.plan,
            name='Old',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=date.today()
        )
        
        special_name = 'Plan "Premium" & VIP 100% ñáéíóú'
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': special_name,
            'base_price': '75.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': False,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        self.assertEqual(membership.name, special_name)


class FieldPreservationTestCase(TestCase):
    """Tests para verificar que solo se actualizan los campos correctos (nombre y precio)"""
    
    def setUp(self):
        """Setup básico"""
        self.franchise = Franchise.objects.create(name='Test Franchise')
        self.gym = Gym.objects.create(franchise=self.franchise, name='Gym', commercial_name='Gym')
        self.user = User.objects.create_user(
            email='test@test.com', 
            password='pass',
            is_superuser=True,
            is_staff=True
        )
        self.franchise.owners.add(self.user)
        
        self.plan = MembershipPlan.objects.create(
            gym=self.gym,
            name='Plan Original',
            base_price=Decimal('50.00'),
            is_recurring=True,
            frequency_amount=1,
            frequency_unit='MONTH'
        )
        
        self.http_client = Client()
        self.http_client.login(email='test@test.com', password='pass')
        session = self.http_client.session
        session['current_gym_id'] = self.gym.id
        session.save()
    
    def test_billing_dates_not_changed(self):
        """Las fechas de facturación no deben cambiar al actualizar el plan"""
        from clients.models import Client as ClientModel
        client = ClientModel.objects.create(gym=self.gym, first_name='Test', last_name='User')
        
        original_period_start = date.today()
        original_period_end = date.today() + timedelta(days=30)
        original_next_billing = date.today() + timedelta(days=30)
        
        membership = ClientMembership.objects.create(
            client=client,
            gym=self.gym,
            plan=self.plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=date.today(),
            current_period_start=original_period_start,
            current_period_end=original_period_end,
            next_billing_date=original_next_billing
        )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'New Name',
            'base_price': '75.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': True,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        
        # Billing dates should NOT change
        self.assertEqual(membership.current_period_start, original_period_start)
        self.assertEqual(membership.current_period_end, original_period_end)
        self.assertEqual(membership.next_billing_date, original_next_billing)
        
        # But name and price should change
        self.assertEqual(membership.name, 'New Name')
        self.assertEqual(membership.price, Decimal('75.00'))
    
    def test_sessions_not_changed(self):
        """Las sesiones totales y usadas no deben cambiar"""
        from clients.models import Client as ClientModel
        client = ClientModel.objects.create(gym=self.gym, first_name='Test', last_name='User')
        
        membership = ClientMembership.objects.create(
            client=client,
            gym=self.gym,
            plan=self.plan,
            name='Old Bono',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=date.today(),
            sessions_total=20,
            sessions_used=8
        )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'New Bono',
            'base_price': '60.00',
            'is_recurring': False,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': False,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        
        # Sessions should NOT change
        self.assertEqual(membership.sessions_total, 20)
        self.assertEqual(membership.sessions_used, 8)
        
        # Name and price should change
        self.assertEqual(membership.name, 'New Bono')
        self.assertEqual(membership.price, Decimal('60.00'))
    
    def test_payment_method_not_changed(self):
        """El método de pago no debe cambiar al actualizar"""
        from clients.models import Client as ClientModel
        from finance.models import PaymentMethod
        
        client = ClientModel.objects.create(gym=self.gym, first_name='Test', last_name='User')
        payment_method = PaymentMethod.objects.create(
            gym=self.gym,
            name='Tarjeta Visa',
            type='CARD',
            is_active=True
        )
        
        membership = ClientMembership.objects.create(
            client=client,
            gym=self.gym,
            plan=self.plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=date.today(),
            payment_method=payment_method
        )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'New Name',
            'base_price': '75.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': True,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        
        # Payment method should NOT change
        self.assertEqual(membership.payment_method, payment_method)
        
        # But name and price should change
        self.assertEqual(membership.name, 'New Name')
        self.assertEqual(membership.price, Decimal('75.00'))
    
    def test_created_metadata_not_changed(self):
        """Los metadatos de creación no deben cambiar"""
        from clients.models import Client as ClientModel
        
        client = ClientModel.objects.create(gym=self.gym, first_name='Test', last_name='User')
        original_creator = self.user
        
        membership = ClientMembership.objects.create(
            client=client,
            gym=self.gym,
            plan=self.plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=date.today(),
            created_by=original_creator
        )
        
        original_created_at = membership.created_at
        
        # Wait a bit to ensure time difference
        import time
        time.sleep(0.1)
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'New Name',
            'base_price': '75.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': True,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        
        # Created metadata should NOT change
        self.assertEqual(membership.created_by, original_creator)
        self.assertEqual(membership.created_at, original_created_at)
    
    def test_start_and_end_dates_not_changed(self):
        """Las fechas de inicio y fin no deben cambiar"""
        from clients.models import Client as ClientModel
        
        client = ClientModel.objects.create(gym=self.gym, first_name='Test', last_name='User')
        
        original_start = date.today() - timedelta(days=15)
        original_end = date.today() + timedelta(days=15)
        
        membership = ClientMembership.objects.create(
            client=client,
            gym=self.gym,
            plan=self.plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='ACTIVE',
            start_date=original_start,
            end_date=original_end
        )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'New Name',
            'base_price': '75.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': True,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        
        # Dates should NOT change
        self.assertEqual(membership.start_date, original_start)
        self.assertEqual(membership.end_date, original_end)


class StatusSpecificTestCase(TestCase):
    """Tests específicos para diferentes estados de membresía"""
    
    def setUp(self):
        """Setup básico"""
        self.franchise = Franchise.objects.create(name='Test Franchise Status')
        self.gym = Gym.objects.create(franchise=self.franchise, name='Gym Status', commercial_name='Gym Status')
        self.user = User.objects.create_user(
            email='test@test.com', 
            password='pass',
            is_superuser=True,
            is_staff=True
        )
        self.franchise.owners.add(self.user)
        
        self.plan = MembershipPlan.objects.create(
            gym=self.gym,
            name='Plan',
            base_price=Decimal('50.00')
        )
        
        self.http_client = Client()
        self.http_client.login(email='test@test.com', password='pass')
        session = self.http_client.session
        session['current_gym_id'] = self.gym.id
        session.save()
    
    def test_paused_status_not_updated(self):
        """Membresías pausadas NO deben actualizarse"""
        from clients.models import Client as ClientModel
        
        client = ClientModel.objects.create(gym=self.gym, first_name='Test', last_name='User')
        
        membership = ClientMembership.objects.create(
            client=client,
            gym=self.gym,
            plan=self.plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='PAUSED',
            start_date=date.today()
        )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'New Name',
            'base_price': '75.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': False,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        
        # PAUSED memberships should NOT be updated
        self.assertEqual(membership.name, 'Old Name')
        self.assertEqual(membership.price, Decimal('50.00'))
    
    def test_pending_payment_status_updated(self):
        """Membresías PENDING_PAYMENT SÍ deben actualizarse"""
        from clients.models import Client as ClientModel
        
        client = ClientModel.objects.create(gym=self.gym, first_name='Test', last_name='User')
        
        membership = ClientMembership.objects.create(
            client=client,
            gym=self.gym,
            plan=self.plan,
            name='Old Name',
            price=Decimal('50.00'),
            status='PENDING_PAYMENT',
            start_date=date.today()
        )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'New Name',
            'base_price': '75.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': False,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        
        # PENDING_PAYMENT memberships SHOULD be updated
        self.assertEqual(membership.name, 'New Name')
        self.assertEqual(membership.price, Decimal('75.00'))
    
    def test_mixed_status_update(self):
        """Test con múltiples membresías en diferentes estados"""
        from clients.models import Client as ClientModel
        
        client1 = ClientModel.objects.create(gym=self.gym, first_name='Client', last_name='One')
        client2 = ClientModel.objects.create(gym=self.gym, first_name='Client', last_name='Two')
        client3 = ClientModel.objects.create(gym=self.gym, first_name='Client', last_name='Three')
        client4 = ClientModel.objects.create(gym=self.gym, first_name='Client', last_name='Four')
        
        # ACTIVE - should update
        m_active = ClientMembership.objects.create(
            client=client1, gym=self.gym, plan=self.plan,
            name='Old', price=Decimal('50.00'), status='ACTIVE', start_date=date.today()
        )
        
        # PENDING - should update
        m_pending = ClientMembership.objects.create(
            client=client2, gym=self.gym, plan=self.plan,
            name='Old', price=Decimal('50.00'), status='PENDING', start_date=date.today()
        )
        
        # EXPIRED - should NOT update
        m_expired = ClientMembership.objects.create(
            client=client3, gym=self.gym, plan=self.plan,
            name='Old', price=Decimal('50.00'), status='EXPIRED', 
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=1)
        )
        
        # PAUSED - should NOT update
        m_paused = ClientMembership.objects.create(
            client=client4, gym=self.gym, plan=self.plan,
            name='Old', price=Decimal('50.00'), status='PAUSED', start_date=date.today()
        )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        response = self.http_client.post(url, {
            'name': 'Updated Plan',
            'base_price': '99.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': False,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        }, follow=True)
        
        # Reload all
        m_active.refresh_from_db()
        m_pending.refresh_from_db()
        m_expired.refresh_from_db()
        m_paused.refresh_from_db()
        
        # ACTIVE and PENDING should be updated
        self.assertEqual(m_active.name, 'Updated Plan')
        self.assertEqual(m_active.price, Decimal('99.00'))
        self.assertEqual(m_pending.name, 'Updated Plan')
        self.assertEqual(m_pending.price, Decimal('99.00'))
        
        # EXPIRED and PAUSED should NOT be updated
        self.assertEqual(m_expired.name, 'Old')
        self.assertEqual(m_expired.price, Decimal('50.00'))
        self.assertEqual(m_paused.name, 'Old')
        self.assertEqual(m_paused.price, Decimal('50.00'))
        
        # Check message shows correct count (2 updated)
        messages = list(response.context['messages'])
        self.assertTrue(any('2 membresías' in str(m) for m in messages))


class PerformanceAndEdgeCasesTestCase(TestCase):
    """Tests de rendimiento y casos extremos"""
    
    def setUp(self):
        """Setup básico"""
        self.franchise = Franchise.objects.create(name='Test Franchise Performance')
        self.gym = Gym.objects.create(franchise=self.franchise, name='Gym Performance', commercial_name='Gym Performance')
        self.user = User.objects.create_user(
            email='test@test.com', 
            password='pass',
            is_superuser=True,
            is_staff=True
        )
        self.franchise.owners.add(self.user)
        
        self.plan = MembershipPlan.objects.create(
            gym=self.gym,
            name='Plan',
            base_price=Decimal('50.00')
        )
        
        self.http_client = Client()
        self.http_client.login(email='test@test.com', password='pass')
        session = self.http_client.session
        session['current_gym_id'] = self.gym.id
        session.save()
    
    def test_large_number_of_memberships(self):
        """Test con gran cantidad de membresías activas (100+)"""
        from clients.models import Client as ClientModel
        
        # Create 100 active memberships
        for i in range(100):
            client = ClientModel.objects.create(
                gym=self.gym, 
                first_name=f'Client{i}', 
                last_name=f'Test{i}'
            )
            ClientMembership.objects.create(
                client=client,
                gym=self.gym,
                plan=self.plan,
                name='Old Name',
                price=Decimal('50.00'),
                status='ACTIVE',
                start_date=date.today()
            )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        response = self.http_client.post(url, {
            'name': 'New Name',
            'base_price': '75.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': False,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        }, follow=True)
        
        # Verify all 100 were updated
        updated_count = ClientMembership.objects.filter(
            plan=self.plan,
            name='New Name',
            price=Decimal('75.00')
        ).count()
        
        self.assertEqual(updated_count, 100)
        
        # Check message
        messages = list(response.context['messages'])
        self.assertTrue(any('100 membresías' in str(m) for m in messages))
    
    def test_no_memberships_to_update(self):
        """Test cuando no hay membresías para actualizar"""
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        response = self.http_client.post(url, {
            'name': 'New Name',
            'base_price': '75.00',
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': False,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        }, follow=True)
        
        # Check message shows 0 updated
        messages = list(response.context['messages'])
        self.assertTrue(any('0 membresías' in str(m) for m in messages))
    
    def test_decimal_precision_preserved(self):
        """Test que la precisión decimal se mantiene correctamente"""
        from clients.models import Client as ClientModel
        
        client = ClientModel.objects.create(gym=self.gym, first_name='Test', last_name='User')
        
        membership = ClientMembership.objects.create(
            client=client,
            gym=self.gym,
            plan=self.plan,
            name='Old',
            price=Decimal('49.99'),
            status='ACTIVE',
            start_date=date.today()
        )
        
        url = reverse('membership_plan_edit', kwargs={'pk': self.plan.pk})
        self.http_client.post(url, {
            'name': 'New',
            'base_price': '99.95',  # Specific decimal value
            'is_recurring': True,
            'frequency_amount': 1,
            'frequency_unit': 'MONTH',
            'is_active': True,
            'is_membership': True,
            'prorate_first_month': False,
            'price_strategy': 'TAX_INCLUDED',
            'access_rules-TOTAL_FORMS': '0',
            'access_rules-INITIAL_FORMS': '0',
            'access_rules-MIN_NUM_FORMS': '0',
            'access_rules-MAX_NUM_FORMS': '1000',
            'update_existing_memberships': 'true',
        })
        
        membership.refresh_from_db()
        
        # Verify exact decimal precision
        self.assertEqual(membership.price, Decimal('99.95'))
        self.assertIsInstance(membership.price, Decimal)

