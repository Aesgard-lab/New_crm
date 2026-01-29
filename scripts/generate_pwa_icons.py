"""
Script para generar íconos PWA para el CRM.
Genera íconos en múltiples tamaños para backoffice y portal del cliente.
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Directorio base
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(BASE_DIR, 'static', 'icons')
PORTAL_ICONS_DIR = os.path.join(ICONS_DIR, 'portal')

# Tamaños requeridos para PWA
SIZES = [72, 96, 128, 144, 152, 192, 384, 512]


def create_gradient_background(size, color1, color2):
    """Crea un fondo con gradiente diagonal."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    for i in range(size):
        # Gradiente diagonal
        ratio = i / size
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        draw.line([(i, 0), (0, i)], fill=(r, g, b, 255))
        draw.line([(i, size-1), (size-1, i)], fill=(r, g, b, 255))
    
    return img


def create_rounded_rectangle(size, radius, color1, color2):
    """Crea un rectángulo redondeado con gradiente."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Fondo con gradiente simple (vertical)
    for y in range(size):
        ratio = y / size
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    
    # Crear máscara redondeada
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (size-1, size-1)], radius=radius, fill=255)
    
    # Aplicar máscara
    img.putalpha(mask)
    
    return img


def draw_text_centered(draw, text, position, font, fill):
    """Dibuja texto centrado en la posición dada."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = position[0] - text_width // 2
    y = position[1] - text_height // 2
    draw.text((x, y), text, font=font, fill=fill)


def create_backoffice_icon(size):
    """Crea el ícono del backoffice (G con check verde)."""
    # Colores del gradiente (indigo a púrpura)
    color1 = (79, 70, 229)   # #4F46E5
    color2 = (124, 58, 237)  # #7C3AED
    
    # Crear fondo redondeado
    radius = int(size * 0.2)
    img = create_rounded_rectangle(size, radius, color1, color2)
    draw = ImageDraw.Draw(img)
    
    # Dibujar la "G"
    try:
        font_size = int(size * 0.55)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Posición de la G (un poco arriba y a la izquierda del centro)
    g_pos = (int(size * 0.45), int(size * 0.45))
    draw_text_centered(draw, "G", g_pos, font, (255, 255, 255, 255))
    
    # Círculo verde (check)
    circle_radius = int(size * 0.16)
    circle_center = (int(size * 0.74), int(size * 0.74))
    
    draw.ellipse([
        circle_center[0] - circle_radius,
        circle_center[1] - circle_radius,
        circle_center[0] + circle_radius,
        circle_center[1] + circle_radius
    ], fill=(16, 185, 129, 255))  # #10B981
    
    # Check mark
    check_width = int(size * 0.04)
    check_points = [
        (circle_center[0] - circle_radius * 0.5, circle_center[1]),
        (circle_center[0] - circle_radius * 0.15, circle_center[1] + circle_radius * 0.35),
        (circle_center[0] + circle_radius * 0.5, circle_center[1] - circle_radius * 0.4)
    ]
    draw.line([check_points[0], check_points[1]], fill=(255, 255, 255, 255), width=check_width)
    draw.line([check_points[1], check_points[2]], fill=(255, 255, 255, 255), width=check_width)
    
    return img


def create_portal_icon(size):
    """Crea el ícono del portal del cliente (más amigable, persona/fitness)."""
    # Colores teal/cyan
    color1 = (20, 184, 166)   # #14B8A6
    color2 = (6, 182, 212)    # #06B6D4
    
    # Crear fondo redondeado
    radius = int(size * 0.2)
    img = create_rounded_rectangle(size, radius, color1, color2)
    draw = ImageDraw.Draw(img)
    
    # Dibujar ícono de persona/fitness simplificado
    center_x = size // 2
    center_y = size // 2
    
    # Cabeza
    head_radius = int(size * 0.12)
    head_y = int(size * 0.3)
    draw.ellipse([
        center_x - head_radius,
        head_y - head_radius,
        center_x + head_radius,
        head_y + head_radius
    ], fill=(255, 255, 255, 255))
    
    # Cuerpo (forma de persona haciendo ejercicio)
    body_width = int(size * 0.06)
    
    # Torso
    draw.line([
        (center_x, head_y + head_radius),
        (center_x, int(size * 0.6))
    ], fill=(255, 255, 255, 255), width=body_width)
    
    # Brazos levantados (pose de fuerza)
    arm_y = int(size * 0.4)
    draw.line([
        (center_x, arm_y),
        (center_x - int(size * 0.2), int(size * 0.28))
    ], fill=(255, 255, 255, 255), width=body_width)
    draw.line([
        (center_x, arm_y),
        (center_x + int(size * 0.2), int(size * 0.28))
    ], fill=(255, 255, 255, 255), width=body_width)
    
    # Manos con pesas
    weight_radius = int(size * 0.06)
    draw.ellipse([
        center_x - int(size * 0.2) - weight_radius,
        int(size * 0.28) - weight_radius,
        center_x - int(size * 0.2) + weight_radius,
        int(size * 0.28) + weight_radius
    ], fill=(255, 255, 255, 255))
    draw.ellipse([
        center_x + int(size * 0.2) - weight_radius,
        int(size * 0.28) - weight_radius,
        center_x + int(size * 0.2) + weight_radius,
        int(size * 0.28) + weight_radius
    ], fill=(255, 255, 255, 255))
    
    # Piernas
    leg_y = int(size * 0.6)
    draw.line([
        (center_x, leg_y),
        (center_x - int(size * 0.12), int(size * 0.8))
    ], fill=(255, 255, 255, 255), width=body_width)
    draw.line([
        (center_x, leg_y),
        (center_x + int(size * 0.12), int(size * 0.8))
    ], fill=(255, 255, 255, 255), width=body_width)
    
    return img


def generate_all_icons():
    """Genera todos los íconos necesarios."""
    # Crear directorios si no existen
    os.makedirs(ICONS_DIR, exist_ok=True)
    os.makedirs(PORTAL_ICONS_DIR, exist_ok=True)
    
    print("Generando íconos PWA...")
    
    # Generar íconos del backoffice
    for size in SIZES:
        icon = create_backoffice_icon(size)
        path = os.path.join(ICONS_DIR, f'icon-{size}x{size}.png')
        icon.save(path, 'PNG')
        print(f"  ✓ Backoffice: {path}")
    
    # Generar íconos del portal
    for size in SIZES:
        icon = create_portal_icon(size)
        path = os.path.join(PORTAL_ICONS_DIR, f'icon-{size}x{size}.png')
        icon.save(path, 'PNG')
        print(f"  ✓ Portal: {path}")
    
    print(f"\n✅ Se generaron {len(SIZES) * 2} íconos exitosamente!")
    print(f"   - Backoffice: {ICONS_DIR}")
    print(f"   - Portal: {PORTAL_ICONS_DIR}")


if __name__ == '__main__':
    generate_all_icons()
