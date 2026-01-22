def translations(request):
    """
    Context processor que provee traducciones básicas basadas en el idioma actual
    """
    translations_dict = {
        'es': {
            'brand_image': 'Imagen de Marca',
            'logo': 'Logotipo',
            'no_logo': 'Sin Logo',
            'recommended_png': 'Recomendado: PNG fondo transparente (200x200px)',
            'brand_color': 'Color Corporativo',
            'brand_color_usage': 'Se usará en botones, bordes y elementos destacados.',
            'commercial_name': 'Nombre Comercial (Público)',
            'company_data': 'Datos de Empresa',
            'legal_name': 'Razón Social',
            'tax_id': 'CIF / NIF',
            'primary_language': 'Idioma Principal',
            'language_description': 'Idioma por defecto para la interfaz y comunicaciones',
            'contact_location': 'Contacto y Ubicación',
            'address': 'Dirección',
            'city': 'Ciudad',
            'province': 'Provincia',
            'postal_code': 'Código Postal',
            'country': 'País',
            'phone': 'Teléfono',
            'public_email': 'Email Público',
            'website': 'Sitio Web',
            'social_networks': 'Redes Sociales',
            'instagram': 'Instagram',
            'facebook': 'Facebook',
            'tiktok': 'TikTok',
            'youtube': 'YouTube',
            'save_changes': 'Guardar Cambios',
            'cancel': 'Cancelar',
        },
        'en': {
            'brand_image': 'Brand Image',
            'logo': 'Logo',
            'no_logo': 'No Logo',
            'recommended_png': 'Recommended: Transparent PNG (200x200px)',
            'brand_color': 'Brand Color',
            'brand_color_usage': 'Will be used in buttons, borders and highlighted elements.',
            'commercial_name': 'Commercial Name (Public)',
            'company_data': 'Company Data',
            'legal_name': 'Legal Name',
            'tax_id': 'Tax ID / VAT',
            'primary_language': 'Primary Language',
            'language_description': 'Default language for interface and communications',
            'contact_location': 'Contact & Location',
            'address': 'Address',
            'city': 'City',
            'province': 'Province / State',
            'postal_code': 'Postal Code',
            'country': 'Country',
            'phone': 'Phone',
            'public_email': 'Public Email',
            'website': 'Website',
            'social_networks': 'Social Networks',
            'instagram': 'Instagram',
            'facebook': 'Facebook',
            'tiktok': 'TikTok',
            'youtube': 'YouTube',
            'save_changes': 'Save Changes',
            'cancel': 'Cancel',
        }
    }
    
    # Obtener el idioma actual de la sesión o del gimnasio
    current_language = 'es'  # Default
    
    if hasattr(request, 'gym') and request.gym:
        current_language = getattr(request.gym, 'language', 'es')
    
    return {
        't': translations_dict.get(current_language, translations_dict['es'])
    }
