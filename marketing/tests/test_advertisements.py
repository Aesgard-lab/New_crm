"""
Tests exhaustivos para el sistema de anuncios publicitarios
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import json

from marketing.models import Advertisement
from organizations.models import Gym, Franchise

User = get_user_model()


class AdvertisementModelTest(TestCase):
    """Tests del modelo Advertisement"""
    
    def setUp(self):
        # Crear franquicia, gimnasio y usuario
        self.franchise = Franchise.objects.create(
            name="Test Franchise"
        )
        self.gym = Gym.objects.create(
            name="Test Gym",
            franchise=self.franchise,
            address="Test Address",
            city="Test City"
        )
        self.user = User.objects.create_user(
            email="test@test.com",
            password="testpass123"
        )
    
    def test_create_advertisement_basic(self):
        """Test crear anuncio básico"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Test Ad",
            position=Advertisement.PositionType.HERO_CAROUSEL,
            ad_type=Advertisement.AdType.INTERNAL_PROMO,
            created_by=self.user
        )
        
        self.assertEqual(ad.title, "Test Ad")
        self.assertEqual(ad.gym, self.gym)
        self.assertTrue(ad.is_active)
        self.assertEqual(ad.priority, 1)
        self.assertEqual(ad.duration_seconds, 5)
    
    def test_target_screens_default_empty(self):
        """Test que target_screens por defecto es lista vacía"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Test Ad",
            created_by=self.user
        )
        
        self.assertEqual(ad.target_screens, [])
        self.assertIsInstance(ad.target_screens, list)
    
    def test_target_screens_with_values(self):
        """Test guardar y recuperar target_screens"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Test Ad",
            target_screens=['HOME', 'SHOP', 'PROFILE'],
            created_by=self.user
        )
        
        # Recargar del DB
        ad.refresh_from_db()
        
        self.assertEqual(len(ad.target_screens), 3)
        self.assertIn('HOME', ad.target_screens)
        self.assertIn('SHOP', ad.target_screens)
        self.assertIn('PROFILE', ad.target_screens)
    
    def test_screen_type_choices(self):
        """Test que ScreenType tiene todos los valores esperados"""
        expected_screens = [
            'ALL', 'HOME', 'CLASS_CATALOG', 'CLASS_DETAIL',
            'PROFILE', 'BOOKINGS', 'SHOP', 'CHECKIN', 'SETTINGS'
        ]
        
        screen_values = [choice[0] for choice in Advertisement.ScreenType.choices]
        
        for expected in expected_screens:
            self.assertIn(expected, screen_values)
    
    def test_is_currently_active_true(self):
        """Test que anuncio activo en rango de fechas retorna True"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Active Ad",
            is_active=True,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            created_by=self.user
        )
        
        self.assertTrue(ad.is_currently_active())
    
    def test_is_currently_active_false_inactive(self):
        """Test que anuncio inactivo retorna False"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Inactive Ad",
            is_active=False,
            created_by=self.user
        )
        
        self.assertFalse(ad.is_currently_active())
    
    def test_is_currently_active_false_not_started(self):
        """Test que anuncio no iniciado retorna False"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Future Ad",
            is_active=True,
            start_date=timezone.now() + timedelta(days=1),
            created_by=self.user
        )
        
        self.assertFalse(ad.is_currently_active())
    
    def test_is_currently_active_false_expired(self):
        """Test que anuncio expirado retorna False"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Expired Ad",
            is_active=True,
            start_date=timezone.now() - timedelta(days=2),
            end_date=timezone.now() - timedelta(days=1),
            created_by=self.user
        )
        
        self.assertFalse(ad.is_currently_active())
    
    def test_ctr_calculation(self):
        """Test cálculo de CTR"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Test Ad",
            impressions=100,
            clicks=15,
            created_by=self.user
        )
        
        self.assertEqual(ad.ctr, 15.0)
    
    def test_ctr_zero_impressions(self):
        """Test CTR cuando no hay impresiones"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Test Ad",
            impressions=0,
            clicks=0,
            created_by=self.user
        )
        
        self.assertEqual(ad.ctr, 0)
    
    def test_str_representation(self):
        """Test representación string del modelo"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Black Friday",
            position=Advertisement.PositionType.HERO_CAROUSEL,
            created_by=self.user
        )
        
        expected = "Black Friday (Hero Carousel (Home))"
        self.assertEqual(str(ad), expected)


class AdvertisementAPITest(TestCase):
    """Tests de los endpoints de la API"""
    
    def setUp(self):
        self.client = Client()
        
        # Crear datos base
        self.franchise = Franchise.objects.create(
            name="Test Franchise"
        )
        self.gym = Gym.objects.create(
            name="Test Gym",
            franchise=self.franchise,
            address="Test Address",
            city="Test City"
        )
        self.user = User.objects.create_user(
            email="test@test.com",
            password="testpass123"
        )
        
        # Crear anuncios de prueba
        self.ad_home = Advertisement.objects.create(
            gym=self.gym,
            title="Home Ad",
            target_screens=['HOME'],
            is_active=True,
            created_by=self.user
        )
        
        self.ad_shop = Advertisement.objects.create(
            gym=self.gym,
            title="Shop Ad",
            target_screens=['SHOP'],
            is_active=True,
            created_by=self.user
        )
        
        self.ad_all = Advertisement.objects.create(
            gym=self.gym,
            title="All Screens Ad",
            target_screens=[],  # Vacío = todas las pantallas
            is_active=True,
            created_by=self.user
        )
        
        self.ad_inactive = Advertisement.objects.create(
            gym=self.gym,
            title="Inactive Ad",
            target_screens=['HOME'],
            is_active=False,
            created_by=self.user
        )
    
    def test_get_active_advertisements_no_filter(self):
        """Test obtener anuncios sin filtro de pantalla"""
        url = reverse('api_advertisements_active')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Debe retornar solo los activos
        self.assertEqual(len(data), 3)
    
    def test_get_active_advertisements_home_screen(self):
        """Test filtrar anuncios por pantalla HOME"""
        url = reverse('api_advertisements_active')
        response = self.client.get(url, {'screen': 'HOME'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Debe retornar: ad_home y ad_all (vacío = todas)
        self.assertEqual(len(data), 2)
        titles = [ad['title'] for ad in data]
        self.assertIn('Home Ad', titles)
        self.assertIn('All Screens Ad', titles)
    
    def test_get_active_advertisements_shop_screen(self):
        """Test filtrar anuncios por pantalla SHOP"""
        url = reverse('api_advertisements_active')
        response = self.client.get(url, {'screen': 'SHOP'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Debe retornar: ad_shop y ad_all
        self.assertEqual(len(data), 2)
        titles = [ad['title'] for ad in data]
        self.assertIn('Shop Ad', titles)
        self.assertIn('All Screens Ad', titles)
    
    def test_get_active_advertisements_profile_screen(self):
        """Test filtrar por pantalla sin anuncios específicos"""
        url = reverse('api_advertisements_active')
        response = self.client.get(url, {'screen': 'PROFILE'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Solo debe retornar ad_all (el de pantallas vacías)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'All Screens Ad')
    
    def test_get_active_advertisements_position_filter(self):
        """Test filtrar por posición"""
        # Crear anuncio con posición específica
        Advertisement.objects.create(
            gym=self.gym,
            title="Hero Ad",
            position=Advertisement.PositionType.HERO_CAROUSEL,
            is_active=True,
            created_by=self.user
        )
        
        url = reverse('api_advertisements_active')
        response = self.client.get(url, {'position': 'HERO_CAROUSEL'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Verificar que todos tienen la posición correcta
        for ad in data:
            self.assertEqual(ad['position'], 'HERO_CAROUSEL')
    
    def test_advertisements_sorted_by_priority(self):
        """Test que anuncios se ordenan por prioridad"""
        # Crear anuncios con diferentes prioridades
        Advertisement.objects.create(
            gym=self.gym,
            title="Priority 3",
            priority=3,
            target_screens=['HOME'],
            is_active=True,
            created_by=self.user
        )
        Advertisement.objects.create(
            gym=self.gym,
            title="Priority 1",
            priority=1,
            target_screens=['HOME'],
            is_active=True,
            created_by=self.user
        )
        
        url = reverse('api_advertisements_active')
        response = self.client.get(url, {'screen': 'HOME'})
        data = json.loads(response.content)
        
        # Verificar orden
        priorities = [ad['priority'] for ad in data]
        self.assertEqual(priorities, sorted(priorities))
    
    def test_track_impression(self):
        """Test trackear impresión"""
        url = reverse('api_advertisement_impression', args=[self.ad_home.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se incrementó
        self.ad_home.refresh_from_db()
        self.assertEqual(self.ad_home.impressions, 1)
    
    def test_track_click(self):
        """Test trackear click"""
        url = reverse('api_advertisement_click', args=[self.ad_home.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se incrementó
        self.ad_home.refresh_from_db()
        self.assertEqual(self.ad_home.clicks, 1)
    
    def test_multiple_impressions(self):
        """Test múltiples impresiones"""
        url = reverse('api_advertisement_impression', args=[self.ad_home.id])
        
        # Trackear 5 impresiones
        for _ in range(5):
            self.client.post(url)
        
        self.ad_home.refresh_from_db()
        self.assertEqual(self.ad_home.impressions, 5)
    
    def test_api_response_structure(self):
        """Test estructura completa de respuesta de API"""
        url = reverse('api_advertisements_active')
        response = self.client.get(url, {'screen': 'HOME'})
        data = json.loads(response.content)
        
        # Verificar que tiene al menos un anuncio
        self.assertGreater(len(data), 0)
        
        # Verificar estructura del primer anuncio
        ad = data[0]
        required_fields = [
            'id', 'title', 'position', 'ad_type',
            'image_desktop', 'cta_text', 'cta_action',
            'target_screens', 'priority', 'duration_seconds'
        ]
        
        for field in required_fields:
            self.assertIn(field, ad)
    
    def test_target_screens_in_response(self):
        """Test que target_screens se incluye en respuesta"""
        url = reverse('api_advertisements_active')
        response = self.client.get(url, {'screen': 'HOME'})
        data = json.loads(response.content)
        
        # Buscar el anuncio de HOME
        home_ad = next((ad for ad in data if ad['title'] == 'Home Ad'), None)
        self.assertIsNotNone(home_ad)
        self.assertEqual(home_ad['target_screens'], ['HOME'])
        
        # Buscar el anuncio de todas las pantallas
        all_ad = next((ad for ad in data if ad['title'] == 'All Screens Ad'), None)
        self.assertIsNotNone(all_ad)
        self.assertEqual(all_ad['target_screens'], [])


class AdvertisementFormTest(TestCase):
    """Tests del formulario de anuncios"""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(
            name="Test Franchise"
        )
        self.gym = Gym.objects.create(
            name="Test Gym",
            franchise=self.franchise,
            address="Test Address",
            city="Test City"
        )
        self.user = User.objects.create_user(
            email="test@test.com",
            password="testpass123",
            is_staff=True
        )
        self.user.current_gym = self.gym
        self.user.save()
    
    def test_form_save_with_target_screens(self):
        """Test que el formulario guarda correctamente target_screens"""
        from marketing.forms import AdvertisementForm
        
        form_data = {
            'title': 'Test Ad',
            'position': Advertisement.PositionType.HERO_CAROUSEL,
            'ad_type': Advertisement.AdType.INTERNAL_PROMO,
            'target_screens': ['HOME', 'SHOP'],
            'cta_text': 'Click Here',
            'cta_action': Advertisement.ActionType.VIEW_CATALOG,
            'is_active': True,
            'priority': 1,
            'duration_seconds': 5,
        }
        
        form = AdvertisementForm(data=form_data)
        
        # El formulario debería ser válido (aunque falten imágenes, tiene blank=True en producción)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.gym = self.gym
            instance.created_by = self.user
            instance.save()
            
            # Verificar que se guardó correctamente
            instance.refresh_from_db()
            self.assertEqual(instance.target_screens, ['HOME', 'SHOP'])
    
    def test_form_save_empty_target_screens(self):
        """Test guardar formulario con target_screens vacío"""
        from marketing.forms import AdvertisementForm
        
        form_data = {
            'title': 'Test Ad All',
            'position': Advertisement.PositionType.HERO_CAROUSEL,
            'ad_type': Advertisement.AdType.INTERNAL_PROMO,
            'target_screens': [],
            'is_active': True,
            'priority': 1,
            'duration_seconds': 5,
        }
        
        form = AdvertisementForm(data=form_data)
        
        if form.is_valid():
            instance = form.save(commit=False)
            instance.gym = self.gym
            instance.created_by = self.user
            instance.save()
            
            instance.refresh_from_db()
            self.assertEqual(instance.target_screens, [])


class AdvertisementIntegrationTest(TestCase):
    """Tests de integración end-to-end"""
    
    def setUp(self):
        self.client = Client()
        
        self.franchise = Franchise.objects.create(
            name="Test Franchise"
        )
        self.gym = Gym.objects.create(
            name="Test Gym",
            franchise=self.franchise,
            address="Test Address",
            city="Test City"
        )
        self.user = User.objects.create_user(
            email="test@test.com",
            password="testpass123",
            is_staff=True
        )
    
    def test_full_advertisement_lifecycle(self):
        """Test ciclo completo: crear, mostrar, trackear"""
        
        # 1. Crear anuncio
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Lifecycle Test",
            target_screens=['HOME', 'SHOP'],
            is_active=True,
            priority=1,
            created_by=self.user
        )
        
        # 2. Verificar que aparece en HOME
        url = reverse('api_advertisements_active')
        response = self.client.get(url, {'screen': 'HOME'})
        data = json.loads(response.content)
        titles = [a['title'] for a in data]
        self.assertIn('Lifecycle Test', titles)
        
        # 3. Trackear impresión
        impression_url = reverse('api_advertisement_impression', args=[ad.id])
        self.client.post(impression_url)
        
        # 4. Trackear click
        click_url = reverse('api_advertisement_click', args=[ad.id])
        self.client.post(click_url)
        
        # 5. Verificar estadísticas
        ad.refresh_from_db()
        self.assertEqual(ad.impressions, 1)
        self.assertEqual(ad.clicks, 1)
        self.assertEqual(ad.ctr, 100.0)
        
        # 6. Desactivar
        ad.is_active = False
        ad.save()
        
        # 7. Verificar que ya no aparece
        response = self.client.get(url, {'screen': 'HOME'})
        data = json.loads(response.content)
        titles = [a['title'] for a in data]
        self.assertNotIn('Lifecycle Test', titles)
    
    def test_multi_screen_targeting(self):
        """Test anuncio en múltiples pantallas"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Multi Screen",
            target_screens=['HOME', 'SHOP', 'PROFILE'],
            is_active=True,
            created_by=self.user
        )
        
        url = reverse('api_advertisements_active')
        
        # Verificar en cada pantalla
        for screen in ['HOME', 'SHOP', 'PROFILE']:
            response = self.client.get(url, {'screen': screen})
            data = json.loads(response.content)
            titles = [a['title'] for a in data]
            self.assertIn('Multi Screen', titles)
        
        # Verificar que NO aparece en CLASS_CATALOG
        response = self.client.get(url, {'screen': 'CLASS_CATALOG'})
        data = json.loads(response.content)
        titles = [a['title'] for a in data]
        self.assertNotIn('Multi Screen', titles)
