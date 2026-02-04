"""
API endpoints para escaneo de códigos de barras y generación de etiquetas.
"""
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_GET
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from accounts.decorators import require_gym_permission
from .models import Product, detect_barcode_type, validate_ean13, validate_ean8
import json


@require_GET
@require_gym_permission('products.view_product')
def barcode_scan(request):
    """
    Endpoint de escaneo rápido para POS.
    Busca producto por código de barras o SKU.
    
    GET /products/api/scan/?code=8410076470119
    
    Respuesta exitosa:
    {
        "found": true,
        "product": {
            "id": 123,
            "name": "Agua Bezoya 500ml",
            "barcode": "8410076470119",
            "sku": "GYM01-BEB-0001",
            "price": 1.50,
            "stock": 24,
            "image": "/media/products/agua.jpg"
        }
    }
    
    No encontrado:
    {
        "found": false,
        "code": "8410076470119",
        "code_type": "EAN13",
        "message": "Producto no encontrado"
    }
    """
    code = request.GET.get('code', '').strip()
    gym = request.gym
    
    if not code:
        return JsonResponse({
            'error': 'Código requerido',
            'found': False
        }, status=400)
    
    # Buscar producto
    product = Product.find_by_code(gym, code)
    
    if product:
        return JsonResponse({
            'found': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'barcode': product.barcode or '',
                'barcode_type': product.barcode_type,
                'sku': product.sku or '',
                'price': float(product.final_price),
                'base_price': float(product.base_price),
                'tax_rate': float(product.tax_rate.rate_percent) if product.tax_rate else 0,
                'stock': product.stock_quantity if product.track_stock else None,
                'track_stock': product.track_stock,
                'image': product.image.url if product.image else None,
                'category': product.category.name if product.category else None,
            }
        })
    
    # No encontrado - dar info sobre el código
    code_type = detect_barcode_type(code)
    
    return JsonResponse({
        'found': False,
        'code': code,
        'code_type': code_type,
        'code_valid': code_type not in ('INVALID_EAN13', 'INVALID_EAN8', 'UNKNOWN'),
        'message': 'Producto no encontrado. ¿Desea crearlo?'
    })


@require_GET
@require_gym_permission('products.view_product')
def barcode_validate(request):
    """
    Valida un código de barras sin buscar producto.
    Útil para verificar antes de crear un producto.
    
    GET /products/api/barcode/validate/?code=8410076470119
    """
    code = request.GET.get('code', '').strip()
    gym = request.gym
    
    if not code:
        return JsonResponse({'valid': False, 'error': 'Código requerido'}, status=400)
    
    code_type = detect_barcode_type(code)
    is_valid = code_type not in ('INVALID_EAN13', 'INVALID_EAN8', 'UNKNOWN')
    
    # Verificar si ya existe
    existing = Product.objects.filter(gym=gym, barcode=code).first()
    
    response = {
        'code': code,
        'type': code_type,
        'type_display': dict(Product.BARCODE_TYPE_CHOICES).get(code_type, code_type),
        'valid': is_valid,
        'already_exists': existing is not None,
    }
    
    if existing:
        response['existing_product'] = {
            'id': existing.id,
            'name': existing.name
        }
    
    if not is_valid:
        if code_type == 'INVALID_EAN13':
            response['error'] = 'Dígito de control EAN-13 incorrecto'
        elif code_type == 'INVALID_EAN8':
            response['error'] = 'Dígito de control EAN-8 incorrecto'
        else:
            response['error'] = 'Formato de código no reconocido'
    
    return JsonResponse(response)


@require_GET
@require_gym_permission('products.view_product')
def barcode_labels_pdf(request):
    """
    Genera PDF con etiquetas de códigos de barras para imprimir.
    
    GET /products/api/labels/pdf/?ids=1,2,3&copies=2&format=30x20
    
    Parámetros:
    - ids: IDs de productos separados por coma
    - copies: Número de copias por producto (default: 1)
    - format: Formato de etiqueta (30x20, 40x25, 50x30)
    """
    from io import BytesIO
    
    ids = request.GET.get('ids', '')
    copies = int(request.GET.get('copies', 1))
    label_format = request.GET.get('format', '40x25')
    gym = request.gym
    
    if not ids:
        return JsonResponse({'error': 'Se requieren IDs de productos'}, status=400)
    
    try:
        product_ids = [int(x.strip()) for x in ids.split(',') if x.strip()]
    except ValueError:
        return JsonResponse({'error': 'IDs inválidos'}, status=400)
    
    products = Product.objects.filter(gym=gym, id__in=product_ids)
    
    if not products.exists():
        return JsonResponse({'error': 'No se encontraron productos'}, status=404)
    
    # Generar PDF con códigos de barras
    try:
        pdf_buffer = generate_barcode_labels_pdf(products, copies, label_format)
        
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="etiquetas_productos.pdf"'
        return response
    except ImportError as e:
        return JsonResponse({
            'error': 'Módulo python-barcode no instalado',
            'install': 'pip install python-barcode[images] reportlab'
        }, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def generate_barcode_labels_pdf(products, copies=1, label_format='40x25'):
    """
    Genera un PDF con etiquetas de códigos de barras.
    Requiere: pip install python-barcode[images] reportlab
    """
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    
    try:
        import barcode
        from barcode.writer import ImageWriter
    except ImportError:
        raise ImportError("Instalar: pip install python-barcode[images]")
    
    # Configuración por formato
    formats = {
        '30x20': {'width': 30*mm, 'height': 20*mm, 'cols': 6, 'rows': 13},
        '40x25': {'width': 40*mm, 'height': 25*mm, 'cols': 5, 'rows': 10},
        '50x30': {'width': 50*mm, 'height': 30*mm, 'cols': 4, 'rows': 9},
        '70x35': {'width': 70*mm, 'height': 35*mm, 'cols': 2, 'rows': 7},
    }
    
    config = formats.get(label_format, formats['40x25'])
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4
    
    # Calcular márgenes para centrar
    total_width = config['cols'] * config['width']
    total_height = config['rows'] * config['height']
    margin_x = (page_width - total_width) / 2
    margin_y = (page_height - total_height) / 2
    
    labels = []
    for product in products:
        for _ in range(copies):
            labels.append(product)
    
    labels_per_page = config['cols'] * config['rows']
    
    for page_num, start_idx in enumerate(range(0, len(labels), labels_per_page)):
        if page_num > 0:
            c.showPage()
        
        page_labels = labels[start_idx:start_idx + labels_per_page]
        
        for idx, product in enumerate(page_labels):
            row = idx // config['cols']
            col = idx % config['cols']
            
            x = margin_x + col * config['width']
            y = page_height - margin_y - (row + 1) * config['height']
            
            # Dibujar etiqueta
            draw_label(c, product, x, y, config['width'], config['height'])
    
    c.save()
    buffer.seek(0)
    return buffer


def draw_label(canvas, product, x, y, width, height):
    """Dibuja una etiqueta individual."""
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from io import BytesIO
    
    padding = 2*mm
    
    # Código a usar
    code = product.barcode or product.sku or f"P{product.pk:05d}"
    
    # Nombre del producto (truncado)
    name = product.name[:25] + '...' if len(product.name) > 25 else product.name
    
    # Precio
    price = f"{product.final_price:.2f}€"
    
    # Dibujar borde (opcional, para corte)
    canvas.setStrokeColor(colors.lightgrey)
    canvas.setLineWidth(0.5)
    canvas.rect(x, y, width, height)
    
    # Nombre del producto
    canvas.setFillColor(colors.black)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(x + padding, y + height - 4*mm, name)
    
    # Código de barras como imagen
    try:
        import barcode
        from barcode.writer import ImageWriter
        from PIL import Image
        
        # Determinar tipo de código de barras
        if product.barcode and len(product.barcode) == 13:
            barcode_class = barcode.get_barcode_class('ean13')
        elif product.barcode and len(product.barcode) == 8:
            barcode_class = barcode.get_barcode_class('ean8')
        else:
            barcode_class = barcode.get_barcode_class('code128')
        
        # Generar imagen del código de barras
        bc = barcode_class(code, writer=ImageWriter())
        
        bc_buffer = BytesIO()
        bc.write(bc_buffer, options={
            'write_text': False,
            'module_height': 8,
            'module_width': 0.3,
            'quiet_zone': 1
        })
        bc_buffer.seek(0)
        
        # Insertar imagen
        from reportlab.lib.utils import ImageReader
        img = ImageReader(bc_buffer)
        
        bc_width = width - 2*padding
        bc_height = height * 0.45
        bc_x = x + padding
        bc_y = y + 5*mm
        
        canvas.drawImage(img, bc_x, bc_y, width=bc_width, height=bc_height, preserveAspectRatio=True)
        
    except Exception as e:
        # Si falla el código de barras, mostrar el código como texto
        canvas.setFont("Courier", 8)
        canvas.drawCentredString(x + width/2, y + height/2, code)
    
    # Código en texto
    canvas.setFont("Courier", 6)
    canvas.drawCentredString(x + width/2, y + 3*mm, code)
    
    # Precio
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawRightString(x + width - padding, y + height - 4*mm, price)


@require_http_methods(["POST"])
@require_gym_permission('products.add_product')
def quick_create_from_scan(request):
    """
    Crea rápidamente un producto desde un código de barras escaneado.
    Útil para agregar productos sobre la marcha en el POS.
    
    POST /products/api/quick-create/
    {
        "barcode": "8410076470119",
        "name": "Agua Bezoya 500ml",
        "price": 1.50,
        "category_id": 5  // Opcional
    }
    """
    gym = request.gym
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    barcode = data.get('barcode', '').strip()
    name = data.get('name', '').strip()
    price = data.get('price')
    category_id = data.get('category_id')
    
    if not name:
        return JsonResponse({'error': 'El nombre es requerido'}, status=400)
    
    if price is None:
        return JsonResponse({'error': 'El precio es requerido'}, status=400)
    
    # Verificar que el barcode no exista
    if barcode:
        existing = Product.objects.filter(gym=gym, barcode=barcode).first()
        if existing:
            return JsonResponse({
                'error': 'Ya existe un producto con este código de barras',
                'existing_product': {
                    'id': existing.id,
                    'name': existing.name
                }
            }, status=400)
    
    # Crear producto
    from .models import ProductCategory
    
    category = None
    if category_id:
        category = ProductCategory.objects.filter(gym=gym, id=category_id).first()
    
    product = Product.objects.create(
        gym=gym,
        name=name,
        barcode=barcode,
        base_price=price,
        category=category,
        is_active=True
    )
    
    return JsonResponse({
        'success': True,
        'product': {
            'id': product.id,
            'name': product.name,
            'barcode': product.barcode,
            'sku': product.sku,
            'price': float(product.final_price)
        }
    }, status=201)


@require_GET
@require_gym_permission('products.view_product')
def products_without_barcode(request):
    """
    Lista productos sin código de barras asignado.
    Útil para identificar qué productos necesitan etiquetado.
    
    GET /products/api/without-barcode/
    """
    gym = request.gym
    
    products = Product.objects.filter(
        gym=gym,
        is_active=True
    ).filter(
        barcode__isnull=True
    ) | Product.objects.filter(
        gym=gym,
        is_active=True,
        barcode=''
    )
    
    products = products.select_related('category').order_by('name')
    
    return JsonResponse({
        'count': products.count(),
        'products': [{
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'category': p.category.name if p.category else None,
            'price': float(p.final_price)
        } for p in products[:100]]
    })
