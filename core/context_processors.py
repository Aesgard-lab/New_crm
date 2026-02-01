def translations(request):
    """
    Context processor que provee traducciones básicas basadas en el idioma actual
    """
    translations_dict = {
        'es': {
            # Gym Settings - Brand
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
            
            # Gym Settings - SMTP
            'smtp_configuration': 'Configuración SMTP',
            'smtp_description': 'Configura el servidor SMTP para enviar emails desde tu gimnasio (campañas, automatizaciones, etc.)',
            'smtp_server': 'Servidor SMTP',
            'smtp_example': 'Ejemplo: smtp.gmail.com',
            'port': 'Puerto',
            'port_description': '587 para TLS, 465 para SSL',
            'smtp_username': 'Usuario SMTP',
            'smtp_password': 'Contraseña SMTP',
            'encrypted_on_save': 'Se encripta al guardar',
            'sender_email': 'Email Remitente',
            'sender_email_description': 'Email que aparecerá como remitente',
            'use_tls': 'Usar TLS (Recomendado)',
            'use_ssl': 'Usar SSL',
            
            # Gym Settings - Email Signature
            'email_signature_policies': 'Firma y Políticas de Email',
            'email_signature_description': 'Configura la firma y el texto legal que se añadirá automáticamente a todos los emails enviados.',
            'signature_logo': 'Logo para Firma',
            'signature_logo_description': 'Sube un logo o imagen que aparecerá en la firma. Recomendado: PNG transparente, máx 200px de alto.',
            'signature_text': 'Texto de la Firma',
            'signature_text_description': 'Se añade después del contenido del email. Puedes usar HTML básico.',
            'email_footer': 'Pie de Email / Políticas de Privacidad',
            'email_footer_description': 'Texto legal, política de privacidad, enlace de baja, etc.',
            
            # Gym Settings - PWA
            'client_app_pwa': 'App para Clientes (PWA)',
            'pwa_description': 'Tus clientes pueden instalar tu portal como una app en su móvil. Comparte este enlace para que accedan directamente con tu logo y colores corporativos.',
            'scan_to_access': 'Escanear para acceder',
            'portal_link': 'Enlace del Portal',
            'copy': 'Copiar',
            'open_portal': 'Abrir Portal',
            'download_qr': 'Descargar QR',
            'share': 'Compartir',
            'pwa_tip': 'Tip: Comparte este enlace en tu web, redes sociales o por WhatsApp. Los clientes podrán "Instalar" la app desde el navegador de su móvil.',
            'embed_code': 'Código para incrustar en tu web',
            'html_code': 'Código HTML (copia y pega en tu web)',
            'link_copied': '¡Enlace copiado!',
            'code_copied': '¡Código copiado!',
            'qr_downloaded': 'QR descargado',
            'copied_to_clipboard': 'Enlace copiado al portapapeles',
            'access_client_portal': 'Acceder al Portal de Clientes',
            
            # Header
            'select_gym': 'Selecciona Sede',
            'my_gyms': 'Mis Sedes',
            'charge': 'Cobrar',
            'logout': 'Cerrar Sesión',
            'no_gym_assigned': 'Sin gimnasio asignado',
            
            # Sidebar - Main sections
            'superadmin_panel': 'Superadmin Panel',
            'franchise_panel': 'Panel Franquicia',
            'goals': 'Objetivos',
            'dashboard': 'Dashboard',
            'calendar': 'Calendario',
            'clients': 'Clientes',
            'pricing': 'Precios',
            'memberships': 'Cuotas',
            'services': 'Servicios',
            'products': 'Productos',
            'activities': 'Actividades',
            'activities_and_rooms': 'Actividades y Salas',
            'analytics_dashboard': 'Dashboard Analytics',
            'attendance_report': 'Informe de Asistencia',
            'activity_report': 'Informe de Actividades',
            'staff_report': 'Informe de Personal',
            'advanced_analytics': 'Analytics Avanzados',
            
            # Sidebar - Finance
            'finances': 'Finanzas',
            'billing_report': 'Informe de Facturación',
            'expenses': 'Gastos',
            'suppliers': 'Proveedores',
            'financial_settings': 'Configuración',
            
            # Sidebar - POS
            'pos': 'TPV / POS',
            
            # Sidebar - Reporting/Audiences
            'audiences': 'Audiencias',
            'groups_tags': 'Grupos & Etiquetas',
            'client_duplicates': 'Duplicados de Clientes',
            'filter_export': 'Filtrar & Exportar',
            
            # Sidebar - Gamification
            'gamification': 'Gamificación',
            'ranking': 'Ranking',
            'achievements': 'Logros',
            'challenges': 'Retos',
            'settings': 'Ajustes',
            
            # Sidebar - Marketing
            'marketing': 'Marketing',
            'email_campaigns': 'Campañas Email',
            'email_templates': 'Plantillas Email',
            'popups_notifications': 'Popups / Notificaciones',
            'app_ads': 'Anuncios en App',
            'automations': 'Automatizaciones',
            'leads_board': 'Tablero Leads',
            'chat': 'Chat',
            'configuration': 'Configuración',
            
            # Sidebar - Team/Staff
            'team': 'Equipo',
            'employee_list': 'Lista de Empleados',
            'time_clock_kiosk': 'Kiosco de Fichaje',
            'my_commissions': 'Mis Comisiones',
            'vacations': 'Vacaciones',
            'roles_permissions': 'Roles y Permisos',
            'incentives': 'Incentivos',
            'performance': 'Rendimiento',
            'activity_log': 'Registro de Actividad',
            
            # Sidebar - Other
            'providers': 'Proveedores',
            'purchase_orders': 'Órdenes de compra',
            'access_control': 'Control de Acceso',
            'facial_recognition': 'Reconocimiento Facial',
            'lockers': 'Taquillas',
            'routines': 'Rutinas',
            'discounts': 'Descuentos',
            'gym_hours': 'Horario del Gimnasio',
            'holidays': 'Festivos',
            'schedule_settings': 'Configuración de Horarios',
            'documents': 'Documentos',
            'document_templates': 'Plantillas Docs',
            'integrations': 'Integraciones',
            'gym_billing': 'Facturación Gimnasio',
            'close_menu': 'Cerrar Menú',
            'billing_report_title': 'Informe de Facturación',
            'analytics_dashboard_title': 'Dashboard Analytics',
            
            # Dashboard - KPIs
            'change': 'Cambiar',
            'performance_summary_of': 'Resumen de rendimiento de',
            'monthly_billing': 'Facturación (Mes)',
            'vs_previous_month': 'vs mes anterior',
            'without_taxes': 'Sin impuestos:',
            'estimated_taxes': 'Impuestos Estimados',
            'vat_collected': 'IVA Recaudado',
            'active_members': 'Socios Activos',
            'new_this_month': 'nuevos este mes',
            'next_month_prediction': 'Próx. Mes (Predicción)',
            'growth': 'Crecimiento',
            'decline': 'Decrecimiento',
            'stable': 'Estable',
            'breakeven_point': 'Punto de Equilibrio',
            'accumulated_balance': 'Balance Acumulado',
            'month_revenue': 'Ingresos mes:',
            'month_expenses': 'Gastos mes:',
            'month_balance': 'Balance mes:',
            'estimated_breakeven': 'Equilibrio estimado en:',
            'months': 'meses',
            'positive_balance': '¡Ya estás en equilibrio positivo!',
            'review_costs': 'Revisar costos y crecimiento',
            'need_more_data': 'Necesitas al menos 3 meses de datos',
            'view_finances': 'Ver finanzas →',
            
            # Dashboard - Memberships
            'active_memberships': 'Membresías Activas',
            'expiring_soon': 'expiran pronto',
            'view_all': 'Ver todas →',
            
            # Dashboard - Goals
            'month_goals': 'Objetivos del Mes',
            'members_goal': 'Socios',
            'revenue_goal': 'Facturación',
            'goal': 'Meta:',
            'view_all_goals': 'Ver todos los objetivos →',
            'current_goals': 'Objetivos Actuales',
            'period_performance': 'Seguimiento de rendimiento del período',
            
            # Dashboard - Quick Actions
            'quick_access': 'Accesos Rápidos',
            'go_to_pos': 'Ir al TPV',
            'new_member': 'Nuevo Socio',
            
            # Dashboard - Staff Kiosk
            'time_clock': 'Kiosco de Fichaje',
            'staff_control': 'Control de Personal',
            'online_now': 'Online ahora:',
            'open_kiosk': 'Abrir Kiosco',
            'view_all_employees': 'Ver todos los empleados',
            
            # Dashboard - Risk Clients
            'risk_clients': 'Clientes en Riesgo (Scoring)',
            'detected': 'Detectados',
            'action_in_days': 'Acción en',
            'days': 'días',
            'no_risk_clients': 'No hay clientes en riesgo detectados.',
            
            # Dashboard - Top Clients
            'top_clients': 'Top Clientes (LTV)',
            'no_data_yet': 'No hay datos aún.',
            
            # Dashboard - Charts
            'revenue_evolution': 'Evolución de Ingresos (30 días)',
            'updated_today': 'Actualizado hoy',
            'revenue': 'Ingresos (€)',
            
            # Dashboard - Forecast
            'quarterly_forecast': 'Previsión Trimestral',
            'based_on_months': 'Basado en',
            'total_projected': 'Total Proyectado (3 meses)',
            'average': 'Promedio:',
            'per_month': '€/mes',
            'trend': 'TENDENCIA',
            'historical': 'HISTÓRICO',
            'monthly_breakdown': 'Desglose Mensual',
            'confidence': 'Confianza:',
            
            # Common
            'search': 'Buscar...',
            'all': 'Todos',
            'add': 'Añadir',
            'edit': 'Editar',
            'delete': 'Eliminar',
            'duplicate': 'Duplicar',
            'save': 'Guardar',
            'close': 'Cerrar',
            'confirm': 'Confirmar',
            'back': 'Volver',
            'next': 'Siguiente',
            'previous': 'Anterior',
            'loading': 'Cargando...',
            'no_results': 'Sin resultados',
            'error': 'Error',
            'success': 'Éxito',
            'warning': 'Advertencia',
            'info': 'Información',
        },
        'en': {
            # Gym Settings - Brand
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
            
            # Gym Settings - SMTP
            'smtp_configuration': 'SMTP Configuration',
            'smtp_description': 'Configure the SMTP server to send emails from your gym (campaigns, automations, etc.)',
            'smtp_server': 'SMTP Server',
            'smtp_example': 'Example: smtp.gmail.com',
            'port': 'Port',
            'port_description': '587 for TLS, 465 for SSL',
            'smtp_username': 'SMTP Username',
            'smtp_password': 'SMTP Password',
            'encrypted_on_save': 'Encrypted when saved',
            'sender_email': 'Sender Email',
            'sender_email_description': 'Email that will appear as sender',
            'use_tls': 'Use TLS (Recommended)',
            'use_ssl': 'Use SSL',
            
            # Gym Settings - Email Signature
            'email_signature_policies': 'Email Signature & Policies',
            'email_signature_description': 'Configure the signature and legal text that will be automatically added to all emails sent.',
            'signature_logo': 'Signature Logo',
            'signature_logo_description': 'Upload a logo or image that will appear in the signature. Recommended: Transparent PNG, max 200px height.',
            'signature_text': 'Signature Text',
            'signature_text_description': 'Added after the email content. You can use basic HTML.',
            'email_footer': 'Email Footer / Privacy Policy',
            'email_footer_description': 'Legal text, privacy policy, unsubscribe link, etc.',
            
            # Gym Settings - PWA
            'client_app_pwa': 'Client App (PWA)',
            'pwa_description': 'Your clients can install your portal as an app on their mobile. Share this link for direct access with your logo and brand colors.',
            'scan_to_access': 'Scan to access',
            'portal_link': 'Portal Link',
            'copy': 'Copy',
            'open_portal': 'Open Portal',
            'download_qr': 'Download QR',
            'share': 'Share',
            'pwa_tip': 'Tip: Share this link on your website, social media or via WhatsApp. Clients can "Install" the app from their mobile browser.',
            'embed_code': 'Embed code for your website',
            'html_code': 'HTML Code (copy and paste in your website)',
            'link_copied': 'Link copied!',
            'code_copied': 'Code copied!',
            'qr_downloaded': 'QR downloaded',
            'copied_to_clipboard': 'Link copied to clipboard',
            'access_client_portal': 'Access Client Portal',
            
            # Header
            'select_gym': 'Select Location',
            'my_gyms': 'My Locations',
            'charge': 'Charge',
            'logout': 'Logout',
            'no_gym_assigned': 'No gym assigned',
            
            # Sidebar - Main sections
            'superadmin_panel': 'Superadmin Panel',
            'franchise_panel': 'Franchise Panel',
            'goals': 'Goals',
            'dashboard': 'Dashboard',
            'calendar': 'Calendar',
            'clients': 'Clients',
            'pricing': 'Pricing',
            'memberships': 'Memberships',
            'services': 'Services',
            'products': 'Products',
            'activities': 'Activities',
            'activities_and_rooms': 'Activities & Rooms',
            'analytics_dashboard': 'Analytics Dashboard',
            'attendance_report': 'Attendance Report',
            'activity_report': 'Activity Report',
            'staff_report': 'Staff Report',
            'advanced_analytics': 'Advanced Analytics',
            
            # Sidebar - Finance
            'finances': 'Finances',
            'billing_report': 'Billing Report',
            'expenses': 'Expenses',
            'suppliers': 'Suppliers',
            'financial_settings': 'Settings',
            
            # Sidebar - POS
            'pos': 'POS',
            
            # Sidebar - Reporting/Audiences
            'audiences': 'Audiences',
            'groups_tags': 'Groups & Tags',
            'client_duplicates': 'Client Duplicates',
            'filter_export': 'Filter & Export',
            
            # Sidebar - Gamification
            'gamification': 'Gamification',
            'ranking': 'Ranking',
            'achievements': 'Achievements',
            'challenges': 'Challenges',
            'settings': 'Settings',
            
            # Sidebar - Marketing
            'marketing': 'Marketing',
            'email_campaigns': 'Email Campaigns',
            'email_templates': 'Email Templates',
            'popups_notifications': 'Popups / Notifications',
            'app_ads': 'In-App Ads',
            'automations': 'Automations',
            'leads_board': 'Leads Board',
            'chat': 'Chat',
            'configuration': 'Configuration',
            
            # Sidebar - Team/Staff
            'team': 'Team',
            'employee_list': 'Employee List',
            'time_clock_kiosk': 'Time Clock Kiosk',
            'my_commissions': 'My Commissions',
            'vacations': 'Vacations',
            'roles_permissions': 'Roles & Permissions',
            'incentives': 'Incentives',
            'performance': 'Performance',
            'activity_log': 'Activity Log',
            
            # Sidebar - Other
            'providers': 'Providers',
            'purchase_orders': 'Purchase Orders',
            'access_control': 'Access Control',
            'facial_recognition': 'Facial Recognition',
            'lockers': 'Lockers',
            'routines': 'Routines',
            'discounts': 'Discounts',
            'gym_hours': 'Gym Hours',
            'holidays': 'Holidays',
            'schedule_settings': 'Schedule Settings',
            'documents': 'Documents',
            'document_templates': 'Doc Templates',
            'integrations': 'Integrations',
            'gym_billing': 'Gym Billing',
            'close_menu': 'Close Menu',
            'billing_report_title': 'Billing Report',
            'analytics_dashboard_title': 'Analytics Dashboard',
            
            # Dashboard - KPIs
            'change': 'Change',
            'performance_summary_of': 'Performance summary of',
            'monthly_billing': 'Monthly Billing',
            'vs_previous_month': 'vs previous month',
            'without_taxes': 'Without taxes:',
            'estimated_taxes': 'Estimated Taxes',
            'vat_collected': 'VAT Collected',
            'active_members': 'Active Members',
            'new_this_month': 'new this month',
            'next_month_prediction': 'Next Month (Prediction)',
            'growth': 'Growth',
            'decline': 'Decline',
            'stable': 'Stable',
            'breakeven_point': 'Break-Even Point',
            'accumulated_balance': 'Accumulated Balance',
            'month_revenue': 'Month revenue:',
            'month_expenses': 'Month expenses:',
            'month_balance': 'Month balance:',
            'estimated_breakeven': 'Estimated break-even in:',
            'months': 'months',
            'positive_balance': 'You are already in positive balance!',
            'review_costs': 'Review costs and growth',
            'need_more_data': 'You need at least 3 months of data',
            'view_finances': 'View finances →',
            
            # Dashboard - Memberships
            'active_memberships': 'Active Memberships',
            'expiring_soon': 'expiring soon',
            'view_all': 'View all →',
            
            # Dashboard - Goals
            'month_goals': 'Month Goals',
            'members_goal': 'Members',
            'revenue_goal': 'Revenue',
            'goal': 'Goal:',
            'view_all_goals': 'View all goals →',
            'current_goals': 'Current Goals',
            'period_performance': 'Period performance tracking',
            
            # Dashboard - Quick Actions
            'quick_access': 'Quick Access',
            'go_to_pos': 'Go to POS',
            'new_member': 'New Member',
            
            # Dashboard - Staff Kiosk
            'time_clock': 'Time Clock Kiosk',
            'staff_control': 'Staff Control',
            'online_now': 'Online now:',
            'open_kiosk': 'Open Kiosk',
            'view_all_employees': 'View all employees',
            
            # Dashboard - Risk Clients
            'risk_clients': 'At-Risk Clients (Scoring)',
            'detected': 'Detected',
            'action_in_days': 'Action in',
            'days': 'days',
            'no_risk_clients': 'No at-risk clients detected.',
            
            # Dashboard - Top Clients
            'top_clients': 'Top Clients (LTV)',
            'no_data_yet': 'No data yet.',
            
            # Dashboard - Charts
            'revenue_evolution': 'Revenue Evolution (30 days)',
            'updated_today': 'Updated today',
            'revenue': 'Revenue (€)',
            
            # Dashboard - Forecast
            'quarterly_forecast': 'Quarterly Forecast',
            'based_on_months': 'Based on',
            'total_projected': 'Total Projected (3 months)',
            'average': 'Average:',
            'per_month': '€/month',
            'trend': 'TREND',
            'historical': 'HISTORICAL',
            'monthly_breakdown': 'Monthly Breakdown',
            'confidence': 'Confidence:',
            
            # Common
            'search': 'Search...',
            'all': 'All',
            'add': 'Add',
            'edit': 'Edit',
            'delete': 'Delete',
            'duplicate': 'Duplicate',
            'save': 'Save',
            'close': 'Close',
            'confirm': 'Confirm',
            'back': 'Back',
            'next': 'Next',
            'previous': 'Previous',
            'loading': 'Loading...',
            'no_results': 'No results',
            'error': 'Error',
            'success': 'Success',
            'warning': 'Warning',
            'info': 'Information',
        }
    }
    
    # Obtener el idioma actual de la sesión o del gimnasio
    current_language = 'es'  # Default
    
    # Primero intentar obtener del gimnasio
    if hasattr(request, 'gym') and request.gym:
        current_language = getattr(request.gym, 'language', 'es')
    # Si no, intentar de la sesión
    elif hasattr(request, 'session') and 'django_language' in request.session:
        current_language = request.session.get('django_language', 'es')
    # Si no, usar el LANGUAGE_CODE del request
    elif hasattr(request, 'LANGUAGE_CODE'):
        current_language = request.LANGUAGE_CODE
    
    # Asegurar que solo usamos 'es' o 'en'
    if current_language not in translations_dict:
        current_language = 'es'
    
    return {
        't': translations_dict.get(current_language, translations_dict['es'])
    }
