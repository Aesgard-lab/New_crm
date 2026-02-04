from django.test import TestCase, Client as TestClient
from django.contrib.auth import get_user_model
from products.models import (
    Product, ProductCategory, 
    validate_ean13, validate_ean8, 
    detect_barcode_type, calculate_ean13_check_digit,
    generate_internal_sku
)
from organizations.models import Gym

User = get_user_model()


class BarcodeValidationTests(TestCase):
    """Tests para validación de códigos de barras."""
    
    def test_valid_ean13(self):
        """EAN-13 válido debe retornar True."""
        # Código de barras real de Coca-Cola
        self.assertTrue(validate_ean13('5449000000996'))
        # Otro código válido
        self.assertTrue(validate_ean13('8410076470119'))
    
    def test_invalid_ean13_wrong_check_digit(self):
        """EAN-13 con dígito de control incorrecto debe retornar False."""
        self.assertFalse(validate_ean13('5449000000995'))  # Último dígito incorrecto
        self.assertFalse(validate_ean13('8410076470118'))
    
    def test_invalid_ean13_wrong_length(self):
        """EAN-13 con longitud incorrecta debe retornar False."""
        self.assertFalse(validate_ean13('544900000099'))  # 12 dígitos
        self.assertFalse(validate_ean13('54490000009966'))  # 14 dígitos
    
    def test_invalid_ean13_non_numeric(self):
        """EAN-13 con caracteres no numéricos debe retornar False."""
        self.assertFalse(validate_ean13('544900000099A'))
    
    def test_valid_ean8(self):
        """EAN-8 válido debe retornar True."""
        self.assertTrue(validate_ean8('96385074'))
    
    def test_invalid_ean8(self):
        """EAN-8 inválido debe retornar False."""
        self.assertFalse(validate_ean8('96385075'))  # Check digit incorrecto
        self.assertFalse(validate_ean8('9638507'))   # Muy corto
    
    def test_calculate_ean13_check_digit(self):
        """Cálculo del dígito de control EAN-13."""
        # Dado los primeros 12 dígitos, debe calcular el 13º
        self.assertEqual(calculate_ean13_check_digit('544900000099'), '5449000000996')
        self.assertEqual(calculate_ean13_check_digit('841007647011'), '8410076470119')
    
    def test_detect_barcode_type_ean13(self):
        """Detectar tipo EAN-13."""
        self.assertEqual(detect_barcode_type('5449000000996'), 'EAN13')
    
    def test_detect_barcode_type_ean8(self):
        """Detectar tipo EAN-8."""
        self.assertEqual(detect_barcode_type('96385074'), 'EAN8')
    
    def test_detect_barcode_type_code128(self):
        """Detectar tipo CODE128 (alfanumérico)."""
        self.assertEqual(detect_barcode_type('ABC-123-XYZ'), 'CODE128')
        self.assertEqual(detect_barcode_type('GYM01-BEB-0001'), 'CODE128')
    
    def test_detect_barcode_type_invalid_ean13(self):
        """Detectar EAN-13 inválido."""
        self.assertEqual(detect_barcode_type('5449000000995'), 'INVALID_EAN13')
    
    def test_detect_barcode_type_upca(self):
        """Detectar UPC-A (12 dígitos)."""
        self.assertEqual(detect_barcode_type('012345678905'), 'UPCA')


class ProductBarcodeTests(TestCase):
    """Tests para funcionalidad de código de barras en productos."""
    
    @classmethod
    def setUpTestData(cls):
        # Crear gimnasio
        cls.gym = Gym.objects.create(
            name='Test Gym',
            email='gym@test.com'
        )
        cls.category = ProductCategory.objects.create(
            gym=cls.gym,
            name='Bebidas',
            code='BEB'
        )
    
    def test_product_auto_generates_sku(self):
        """Producto sin SKU debe generar uno automáticamente."""
        product = Product.objects.create(
            gym=self.gym,
            name='Agua Mineral',
            base_price=1.50,
            category=self.category
        )
        self.assertTrue(product.sku)
        self.assertIn('BEB', product.sku)
    
    def test_product_with_valid_barcode(self):
        """Producto con código de barras válido."""
        product = Product.objects.create(
            gym=self.gym,
            name='Coca-Cola',
            base_price=2.00,
            barcode='5449000000996'
        )
        self.assertEqual(product.barcode_type, 'EAN13')
        self.assertTrue(product.has_valid_barcode)
    
    def test_product_find_by_barcode(self):
        """Buscar producto por código de barras."""
        Product.objects.create(
            gym=self.gym,
            name='Fanta',
            base_price=2.00,
            barcode='5449000131805'
        )
        
        found = Product.find_by_code(self.gym, '5449000131805')
        self.assertIsNotNone(found)
        self.assertEqual(found.name, 'Fanta')
    
    def test_product_find_by_sku(self):
        """Buscar producto por SKU."""
        product = Product.objects.create(
            gym=self.gym,
            name='Sprite',
            base_price=2.00,
            category=self.category
        )
        
        found = Product.find_by_code(self.gym, product.sku)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, 'Sprite')
    
    def test_product_not_found_returns_none(self):
        """Búsqueda sin resultado retorna None."""
        found = Product.find_by_code(self.gym, 'CODIGO_INEXISTENTE')
        self.assertIsNone(found)
    
    def test_display_code_property(self):
        """Propiedad display_code retorna el código correcto."""
        # Con barcode
        p1 = Product.objects.create(
            gym=self.gym,
            name='Producto 1',
            base_price=1.00,
            barcode='5449000000996'
        )
        self.assertEqual(p1.display_code, '5449000000996')
        
        # Sin barcode, con SKU
        p2 = Product.objects.create(
            gym=self.gym,
            name='Producto 2',
            base_price=1.00,
            sku='TEST-SKU-001'
        )
        self.assertEqual(p2.display_code, 'TEST-SKU-001')


class ProductCategoryCodeTests(TestCase):
    """Tests para código de categoría."""
    
    @classmethod
    def setUpTestData(cls):
        cls.gym = Gym.objects.create(
            name='Test Gym',
            email='gym@test.com'
        )
    
    def test_category_auto_generates_code(self):
        """Categoría sin código debe generar uno automáticamente."""
        category = ProductCategory.objects.create(
            gym=self.gym,
            name='Suplementos Deportivos'
        )
        self.assertTrue(category.code)
        # Debería ser algo como "SD" o "SUD"
        self.assertTrue(len(category.code) <= 5)
    
    def test_category_preserves_custom_code(self):
        """Categoría con código personalizado lo preserva."""
        category = ProductCategory.objects.create(
            gym=self.gym,
            name='Bebidas',
            code='BEB'
        )
        self.assertEqual(category.code, 'BEB')
