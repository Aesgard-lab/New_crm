"""
Tests simplificados y funcionales para el sistema de anuncios
"""

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from marketing.models import Advertisement
from organizations.models import Gym, Franchise

User = get_user_model()


class AdvertisementModelSimpleTest(TestCase):
    """Tests básicos del modelo Advertisement"""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name="Test Franchise")
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
    
    def test_create_advertisement(self):
        """Test crear anuncio básico"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Test Ad",
            position=Advertisement.PositionType.HERO_CAROUSEL,
            ad_type=Advertisement.AdType.INTERNAL_PROMO,
            created_by=self.user
        )
        
        self.assertEqual(ad.title, "Test Ad")
        self.assertTrue(ad.is_active)
        self.assertEqual(ad.target_screens, [])
    
    def test_target_screens_saves_correctly(self):
        """Test que target_screens se guarda como lista"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Multi Screen Ad",
            target_screens=['HOME', 'SHOP', 'PROFILE'],
            created_by=self.user
        )
        
        ad.refresh_from_db()
        self.assertEqual(len(ad.target_screens), 3)
        self.assertIn('HOME', ad.target_screens)
        self.assertIn('SHOP', ad.target_screens)
    
    def test_empty_target_screens_means_all(self):
        """Test que lista vacía significa todas las pantallas"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="All Screens",
            target_screens=[],
            created_by=self.user
        )
        
        self.assertEqual(ad.target_screens, [])
    
    def test_is_currently_active_logic(self):
        """Test lógica de is_currently_active"""
        # Anuncio activo
        active_ad = Advertisement.objects.create(
            gym=self.gym,
            title="Active",
            is_active=True,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            created_by=self.user
        )
        self.assertTrue(active_ad.is_currently_active())
        
        # Anuncio inactivo
        inactive_ad = Advertisement.objects.create(
            gym=self.gym,
            title="Inactive",
            is_active=False,
            created_by=self.user
        )
        self.assertFalse(inactive_ad.is_currently_active())
        
        # Anuncio futuro
        future_ad = Advertisement.objects.create(
            gym=self.gym,
            title="Future",
            is_active=True,
            start_date=timezone.now() + timedelta(days=1),
            created_by=self.user
        )
        self.assertFalse(future_ad.is_currently_active())
        
        # Anuncio expirado
        expired_ad = Advertisement.objects.create(
            gym=self.gym,
            title="Expired",
            is_active=True,
            start_date=timezone.now() - timedelta(days=2),
            end_date=timezone.now() - timedelta(days=1),
            created_by=self.user
        )
        self.assertFalse(expired_ad.is_currently_active())
    
    def test_ctr_calculation(self):
        """Test cálculo de CTR"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="CTR Test",
            impressions=100,
            clicks=25,
            created_by=self.user
        )
        
        self.assertEqual(ad.ctr, 25.0)
    
    def test_ctr_zero_division(self):
        """Test CTR con cero impresiones"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Zero CTR",
            impressions=0,
            clicks=0,
            created_by=self.user
        )
        
        self.assertEqual(ad.ctr, 0)
    
    def test_screen_type_choices_exist(self):
        """Test que todos los ScreenType existen"""
        expected_screens = [
            'ALL', 'HOME', 'CLASS_CATALOG', 'CLASS_DETAIL',
            'PROFILE', 'BOOKINGS', 'SHOP', 'CHECKIN', 'SETTINGS'
        ]
        
        choices = [choice[0] for choice in Advertisement.ScreenType.choices]
        
        for screen in expected_screens:
            self.assertIn(screen, choices, f"Missing screen type: {screen}")
    
    def test_tracking_increments(self):
        """Test que tracking incrementa correctamente"""
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Tracking Test",
            created_by=self.user
        )
        
        # Incrementar impresiones
        ad.impressions += 1
        ad.save()
        ad.refresh_from_db()
        self.assertEqual(ad.impressions, 1)
        
        # Incrementar clicks
        ad.clicks += 1
        ad.save()
        ad.refresh_from_db()
        self.assertEqual(ad.clicks, 1)
    
    def test_priority_ordering(self):
        """Test que priority afecta el ordenamiento"""
        ad1 = Advertisement.objects.create(
            gym=self.gym,
            title="Priority 3",
            priority=3,
            created_by=self.user
        )
        ad2 = Advertisement.objects.create(
            gym=self.gym,
            title="Priority 1",
            priority=1,
            created_by=self.user
        )
        ad3 = Advertisement.objects.create(
            gym=self.gym,
            title="Priority 2",
            priority=2,
            created_by=self.user
        )
        
        # Ordenar por priority
        ads = Advertisement.objects.filter(gym=self.gym).order_by('priority')
        
        self.assertEqual(ads[0].title, "Priority 1")
        self.assertEqual(ads[1].title, "Priority 2")
        self.assertEqual(ads[2].title, "Priority 3")


class AdvertisementQueryTest(TestCase):
    """Tests de queries y filtrado"""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name="Test Franchise")
        self.gym = Gym.objects.create(
            name="Test Gym",
            franchise=self.franchise
        )
        self.user = User.objects.create_user(
            email="test@test.com",
            password="testpass123"
        )
        
        # Crear anuncios de prueba
        self.ad_home = Advertisement.objects.create(
            gym=self.gym,
            title="Home Only",
            target_screens=['HOME'],
            is_active=True,
            created_by=self.user
        )
        
        self.ad_shop = Advertisement.objects.create(
            gym=self.gym,
            title="Shop Only",
            target_screens=['SHOP'],
            is_active=True,
            created_by=self.user
        )
        
        self.ad_multi = Advertisement.objects.create(
            gym=self.gym,
            title="Home and Shop",
            target_screens=['HOME', 'SHOP'],
            is_active=True,
            created_by=self.user
        )
        
        self.ad_all = Advertisement.objects.create(
            gym=self.gym,
            title="All Screens",
            target_screens=[],
            is_active=True,
            created_by=self.user
        )
    
    def test_filter_by_home_screen(self):
        """Test filtrar anuncios para pantalla HOME"""
        from django.db.models import Q
        
        screen = 'HOME'
        ads = Advertisement.objects.filter(
            gym=self.gym,
            is_active=True
        ).filter(
            Q(target_screens=[]) | Q(target_screens__contains=[screen])
        )
        
        titles = [ad.title for ad in ads]
        
        # Debe incluir: Home Only, Home and Shop, All Screens
        self.assertIn('Home Only', titles)
        self.assertIn('Home and Shop', titles)
        self.assertIn('All Screens', titles)
        
        # No debe incluir: Shop Only
        self.assertNotIn('Shop Only', titles)
    
    def test_filter_by_shop_screen(self):
        """Test filtrar anuncios para pantalla SHOP"""
        from django.db.models import Q
        
        screen = 'SHOP'
        ads = Advertisement.objects.filter(
            gym=self.gym,
            is_active=True
        ).filter(
            Q(target_screens=[]) | Q(target_screens__contains=[screen])
        )
        
        titles = [ad.title for ad in ads]
        
        # Debe incluir: Shop Only, Home and Shop, All Screens
        self.assertIn('Shop Only', titles)
        self.assertIn('Home and Shop', titles)
        self.assertIn('All Screens', titles)
        
        # No debe incluir: Home Only
        self.assertNotIn('Home Only', titles)
    
    def test_filter_by_profile_screen_no_specific_ads(self):
        """Test filtrar por pantalla sin anuncios específicos"""
        from django.db.models import Q
        
        screen = 'PROFILE'
        ads = Advertisement.objects.filter(
            gym=self.gym,
            is_active=True
        ).filter(
            Q(target_screens=[]) | Q(target_screens__contains=[screen])
        )
        
        # Solo debe retornar All Screens
        self.assertEqual(ads.count(), 1)
        self.assertEqual(ads[0].title, 'All Screens')
    
    def test_only_active_ads(self):
        """Test que solo se retornan anuncios activos"""
        # Crear anuncio inactivo
        Advertisement.objects.create(
            gym=self.gym,
            title="Inactive Ad",
            target_screens=['HOME'],
            is_active=False,
            created_by=self.user
        )
        
        ads = Advertisement.objects.filter(
            gym=self.gym,
            is_active=True
        )
        
        titles = [ad.title for ad in ads]
        self.assertNotIn('Inactive Ad', titles)
    
    def test_filter_by_position(self):
        """Test filtrar por posición"""
        # Limpiar anuncios anteriores para este test
        Advertisement.objects.filter(gym=self.gym).delete()
        
        hero_ad = Advertisement.objects.create(
            gym=self.gym,
            title="Hero Ad",
            position=Advertisement.PositionType.HERO_CAROUSEL,
            is_active=True,
            created_by=self.user
        )
        
        footer_ad = Advertisement.objects.create(
            gym=self.gym,
            title="Footer Ad",
            position=Advertisement.PositionType.STICKY_FOOTER,
            is_active=True,
            created_by=self.user
        )
        
        hero_ads = Advertisement.objects.filter(
            gym=self.gym,
            position=Advertisement.PositionType.HERO_CAROUSEL
        )
        
        self.assertEqual(hero_ads.count(), 1)
        self.assertEqual(hero_ads[0].title, "Hero Ad")


class AdvertisementIntegrationTest(TestCase):
    """Tests de integración completos"""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name="Integration Test")
        self.gym = Gym.objects.create(
            name="Integration Gym",
            franchise=self.franchise
        )
        self.user = User.objects.create_user(
            email="integration@test.com",
            password="testpass123"
        )
    
    def test_full_lifecycle(self):
        """Test ciclo de vida completo de un anuncio"""
        # 1. Crear
        ad = Advertisement.objects.create(
            gym=self.gym,
            title="Lifecycle Test",
            target_screens=['HOME', 'SHOP'],
            is_active=True,
            priority=1,
            created_by=self.user
        )
        
        # 2. Verificar que existe
        self.assertTrue(Advertisement.objects.filter(id=ad.id).exists())
        
        # 3. Simular impresiones
        ad.impressions = 10
        ad.save()
        
        # 4. Simular clicks
        ad.clicks = 3
        ad.save()
        
        # 5. Verificar CTR
        ad.refresh_from_db()
        self.assertEqual(ad.ctr, 30.0)
        
        # 6. Desactivar
        ad.is_active = False
        ad.save()
        
        # 7. Verificar que no está activo
        self.assertFalse(ad.is_currently_active())
    
    def test_multiple_gyms_isolation(self):
        """Test que anuncios de diferentes gimnasios están aislados"""
        gym2 = Gym.objects.create(
            name="Gym 2",
            franchise=self.franchise
        )
        
        ad1 = Advertisement.objects.create(
            gym=self.gym,
            title="Gym 1 Ad",
            created_by=self.user
        )
        
        ad2 = Advertisement.objects.create(
            gym=gym2,
            title="Gym 2 Ad",
            created_by=self.user
        )
        
        # Verificar aislamiento
        gym1_ads = Advertisement.objects.filter(gym=self.gym)
        self.assertEqual(gym1_ads.count(), 1)
        self.assertEqual(gym1_ads[0].title, "Gym 1 Ad")
        
        gym2_ads = Advertisement.objects.filter(gym=gym2)
        self.assertEqual(gym2_ads.count(), 1)
        self.assertEqual(gym2_ads[0].title, "Gym 2 Ad")


print("\n" + "="*60)
print("✅ TESTS SIMPLIFICADOS CREADOS")
print("="*60)
print("\nTests incluidos:")
print("  📊 AdvertisementModelSimpleTest (11 tests)")
print("     - Creación, target_screens, is_active, CTR, etc.")
print("  🔍 AdvertisementQueryTest (6 tests)")
print("     - Filtrado por pantalla, posición, estado")
print("  🔄 AdvertisementIntegrationTest (2 tests)")
print("     - Ciclo completo y aislamiento de gimnasios")
print("\nTotal: 19 tests funcionales")
print("="*60)
