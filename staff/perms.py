from django.contrib.auth.models import Permission

# Define the logical structure for the Permission UI
# This maps a "Module Name" to a list of (Codename, Label) tuples
PERMISSION_STRUCTURE = {
    # ==========================================
    # CLIENTES
    # ==========================================
    "Clientes": [
        ("view_client", "Ver Clientes"),
        ("add_client", "Crear Clientes"),
        ("change_client", "Editar Clientes"),
        ("delete_client", "Eliminar Clientes"),
        ("export_client", "Exportar Clientes"),
        ("import_client", "Importar Clientes"),
        ("view_clientnote", "Ver Notas"),
        ("add_clientnote", "Añadir Notas"),
        ("change_clientnote", "Editar Notas"),
        ("delete_clientnote", "Eliminar Notas"),
        ("view_clientdocument", "Ver Documentos"),
        ("add_clientdocument", "Subir Documentos"),
        ("delete_clientdocument", "Eliminar Documentos"),
        ("view_clientmembership", "Ver Membresías de Clientes"),
        ("change_clientmembership", "Modificar Membresías de Clientes"),
    ],
    
    # ==========================================
    # FINANZAS Y FACTURACIÓN
    # ==========================================
    "Finanzas": [
        # Dashboard
        ("view_finance", "Ver Dashboard Financiero"),
        ("view_finance_reports", "Ver Informes Financieros"),
        ("export_finance_reports", "Exportar Informes Financieros"),
        
        # Caja
        ("view_cashsession", "Ver Sesiones de Caja"),
        ("add_cashsession", "Abrir Caja"),
        ("close_cashsession", "Cerrar Caja"),
        ("view_cashmovement", "Ver Movimientos de Caja"),
        ("add_cashmovement", "Añadir Movimiento Manual"),
        
        # Métodos de Pago
        ("view_paymentmethod", "Ver Métodos de Pago"),
        ("add_paymentmethod", "Crear Métodos de Pago"),
        ("change_paymentmethod", "Editar Métodos de Pago"),
        ("delete_paymentmethod", "Eliminar Métodos de Pago"),
        
        # Pagos de Clientes
        ("view_clientpayment", "Ver Pagos de Clientes"),
        ("add_clientpayment", "Registrar Pagos"),
        ("refund_clientpayment", "Realizar Devoluciones"),
        
        # TPV/POS
        ("view_posdevice", "Ver Dispositivos TPV"),
        ("add_posdevice", "Configurar TPV"),
        ("change_posdevice", "Editar TPV"),
        
        # Configuración Financiera
        ("view_financesettings", "Ver Configuración Financiera"),
        ("change_financesettings", "Editar Configuración Financiera"),
    ],
    
    "Facturación": [
        # Facturas
        ("view_invoice", "Ver Facturas"),
        ("add_invoice", "Crear Facturas"),
        ("change_invoice", "Editar Facturas"),
        ("delete_invoice", "Anular Facturas"),
        ("export_invoice", "Exportar Facturas"),
        ("send_invoice", "Enviar Facturas por Email"),
        
        # Facturas Rectificativas
        ("add_rectificativeinvoice", "Crear Factura Rectificativa"),
        
        # Impuestos
        ("view_taxrate", "Ver Tipos de IVA"),
        ("change_taxrate", "Modificar Tipos de IVA"),
        
        # Verifactu
        ("view_verifactu", "Ver Registros Verifactu"),
        ("sync_verifactu", "Sincronizar con Hacienda"),
    ],
    
    "Gastos": [
        # Categorías
        ("view_expensecategory", "Ver Categorías de Gastos"),
        ("add_expensecategory", "Crear Categorías"),
        ("change_expensecategory", "Editar Categorías"),
        ("delete_expensecategory", "Eliminar Categorías"),
        
        # Gastos
        ("view_expense", "Ver Gastos"),
        ("add_expense", "Registrar Gastos"),
        ("change_expense", "Editar Gastos"),
        ("delete_expense", "Eliminar Gastos"),
        ("approve_expense", "Aprobar Gastos"),
        ("export_expense", "Exportar Gastos"),
    ],
    
    # ==========================================
    # VENTAS (TPV)
    # ==========================================
    "Ventas (TPV)": [
        # Ventas
        ("view_sale", "Ver Ventas/Tickets"),
        ("add_sale", "Crear Ventas"),
        ("change_sale", "Editar Ventas"),
        ("delete_sale", "Eliminar/Cancelar Ventas"),
        ("refund_sale", "Procesar Devoluciones"),
        ("export_sale", "Exportar Ventas"),
        
        # Acceso al TPV
        ("access_pos", "Acceder al TPV/Punto de Venta"),
    ],
    
    # ==========================================
    # PROVEEDORES Y COMPRAS
    # ==========================================
    "Proveedores": [
        # CRUD Proveedores
        ("view_provider", "Ver Proveedores"),
        ("add_provider", "Crear Proveedores"),
        ("change_provider", "Editar Proveedores"),
        ("delete_provider", "Eliminar Proveedores"),
        
        # Contactos
        ("view_providercontact", "Ver Contactos de Proveedor"),
        ("add_providercontact", "Añadir Contactos"),
        ("change_providercontact", "Editar Contactos"),
        ("delete_providercontact", "Eliminar Contactos"),
        
        # Documentos
        ("view_providerdocument", "Ver Documentos de Proveedor"),
        ("add_providerdocument", "Subir Documentos"),
        ("delete_providerdocument", "Eliminar Documentos"),
        
        # Valoraciones
        ("view_providerrating", "Ver Valoraciones"),
        ("add_providerrating", "Añadir Valoración"),
        
        # Catálogo del Proveedor
        ("view_provideritem", "Ver Catálogo del Proveedor"),
        ("add_provideritem", "Añadir Productos del Proveedor"),
        ("change_provideritem", "Editar Productos del Proveedor"),
        ("delete_provideritem", "Eliminar Productos del Proveedor"),
    ],
    
    "Órdenes de Compra": [
        # Órdenes
        ("view_purchaseorder", "Ver Órdenes de Compra"),
        ("add_purchaseorder", "Crear Órdenes de Compra"),
        ("change_purchaseorder", "Editar Órdenes de Compra"),
        ("delete_purchaseorder", "Eliminar Órdenes de Compra"),
        ("approve_purchaseorder", "Aprobar Órdenes de Compra"),
        ("receive_purchaseorder", "Recibir Mercancía"),
        ("cancel_purchaseorder", "Cancelar Órdenes"),
        ("export_purchaseorder", "Exportar Órdenes"),
        
        # Líneas de Pedido
        ("view_purchaseorderline", "Ver Líneas de Pedido"),
        ("change_purchaseorderline", "Modificar Líneas de Pedido"),
    ],
    
    # ==========================================
    # MARKETING
    # ==========================================
    "Marketing": [
        ("view_marketing", "Ver Dashboard Marketing"),
        ("view_leadcard", "Ver Leads"),
        ("add_leadcard", "Crear Leads"),
        ("change_leadcard", "Editar Leads"),
        ("delete_leadcard", "Eliminar Leads"),
        ("convert_leadcard", "Convertir Lead a Cliente"),
        ("view_campaign", "Ver Campañas Email"),
        ("add_campaign", "Crear Campañas Email"),
        ("change_campaign", "Editar Campañas Email"),
        ("delete_campaign", "Eliminar Campañas Email"),
        ("send_campaign", "Enviar Campañas"),
        ("view_popup", "Ver Popups/Notificaciones"),
        ("add_popup", "Crear Popups/Notificaciones"),
        ("change_popup", "Editar Popups/Notificaciones"),
        ("delete_popup", "Eliminar Popups/Notificaciones"),
        ("view_advertisement", "Ver Anuncios en App"),
        ("add_advertisement", "Crear Anuncios en App"),
        ("change_advertisement", "Editar Anuncios en App"),
        ("delete_advertisement", "Eliminar Anuncios en App"),
        ("view_emailworkflow", "Ver Automatizaciones"),
        ("add_emailworkflow", "Crear Automatizaciones"),
        ("change_emailworkflow", "Editar Automatizaciones"),
        ("delete_emailworkflow", "Eliminar Automatizaciones"),
    ],
    
    # ==========================================
    # STAFF (EQUIPO)
    # ==========================================
    "Staff (Equipo)": [
        # CRUD Empleados
        ("view_staffprofile", "Ver Equipo"),
        ("add_staffprofile", "Crear Empleados"),
        ("change_staffprofile", "Editar Empleados"),
        ("delete_staffprofile", "Eliminar Empleados"),
        
        # Turnos y Fichajes
        ("view_workshift", "Ver Turnos/Fichajes"),
        ("add_workshift", "Crear Turnos Manuales"),
        ("change_workshift", "Editar Turnos"),
        ("delete_workshift", "Eliminar Turnos"),
        ("view_shift_report", "Ver Informe de Fichajes"),
        ("export_shift_report", "Exportar Informe de Fichajes"),
        
        # Horarios Esperados
        ("view_expectedschedule", "Ver Horarios Esperados"),
        ("change_expectedschedule", "Configurar Horarios Esperados"),
        
        # Alertas de Fichaje
        ("view_checkinalert", "Ver Alertas de Fichaje"),
        ("resolve_checkinalert", "Resolver Alertas de Fichaje"),
        
        # Kiosco de Fichaje
        ("view_staffkiosk", "Ver Kiosco de Fichaje"),
        ("access_staffkiosk", "Acceder al Kiosco de Fichaje"),
        
        # Roles y Permisos
        ("manage_roles", "Gestionar Roles y Permisos"),
        ("view_auditlog", "Ver Registro de Auditoría"),
        
        # Incentivos y Comisiones
        ("view_incentive", "Ver Incentivos y Comisiones"),
        ("add_incentiverule", "Crear Reglas de Incentivos"),
        ("change_incentiverule", "Editar Reglas de Incentivos"),
        ("delete_incentiverule", "Eliminar Reglas de Incentivos"),
        ("view_all_incentives", "Ver Incentivos de Todo el Staff"),
        ("view_own_incentives", "Ver Solo Incentivos Propios"),
        
        # Rating Incentives
        ("view_ratingincentive", "Ver Incentivos por Rating"),
        ("add_ratingincentive", "Crear Incentivos por Rating"),
        ("change_ratingincentive", "Editar Incentivos por Rating"),
        ("delete_ratingincentive", "Eliminar Incentivos por Rating"),
        
        # Salarios
        ("view_salaryconfig", "Ver Configuración Salarial"),
        ("change_salaryconfig", "Editar Configuración Salarial"),
        
        # Tareas
        ("view_stafftask", "Ver Tareas de Empleados"),
        ("add_stafftask", "Crear Tareas"),
        ("change_stafftask", "Editar Tareas"),
        ("delete_stafftask", "Eliminar Tareas"),
        ("complete_stafftask", "Marcar Tareas Completadas"),
        
        # Vacaciones y Ausencias
        ("view_vacation", "Ver Vacaciones/Ausencias"),
        ("add_vacation", "Solicitar Vacaciones"),
        ("approve_vacation", "Aprobar/Rechazar Vacaciones"),
        ("view_vacation_balance", "Ver Balance de Vacaciones"),
        ("change_vacation_balance", "Ajustar Balance de Vacaciones"),
        ("manage_blocked_periods", "Gestionar Periodos Bloqueados"),
    ],
    
    # ==========================================
    # SERVICIOS, PRODUCTOS Y CUOTAS
    # ==========================================
    "Servicios & Productos": [
        ("view_service", "Ver Servicios"),
        ("add_service", "Crear Servicios"),
        ("change_service", "Editar Servicios"),
        ("delete_service", "Eliminar Servicios"),
        ("view_product", "Ver Productos"),
        ("add_product", "Crear Productos"),
        ("change_product", "Editar Productos"),
        ("delete_product", "Eliminar Productos"),
        ("view_membershipplan", "Ver Cuotas/Planes"),
        ("add_membershipplan", "Crear Cuotas/Planes"),
        ("change_membershipplan", "Editar Cuotas/Planes"),
        ("delete_membershipplan", "Eliminar Cuotas/Planes"),
        ("view_inventory", "Ver Inventario"),
        ("change_inventory", "Ajustar Inventario"),
    ],
    
    # ==========================================
    # DESCUENTOS Y PROMOCIONES
    # ==========================================
    "Descuentos": [
        ("view_discount", "Ver Descuentos"),
        ("add_discount", "Crear Descuentos"),
        ("change_discount", "Editar Descuentos"),
        ("delete_discount", "Eliminar Descuentos"),
        ("view_discountusage", "Ver Uso de Descuentos"),
        ("view_referralprogram", "Ver Programas de Referidos"),
        ("add_referralprogram", "Crear Programas de Referidos"),
        ("change_referralprogram", "Editar Programas de Referidos"),
        ("delete_referralprogram", "Eliminar Programas de Referidos"),
        ("view_coupon", "Ver Cupones"),
        ("add_coupon", "Crear Cupones"),
        ("change_coupon", "Editar Cupones"),
        ("delete_coupon", "Eliminar Cupones"),
        ("view_promotion", "Ver Promociones"),
        ("add_promotion", "Crear Promociones"),
        ("change_promotion", "Editar Promociones"),
        ("delete_promotion", "Eliminar Promociones"),
    ],
    
    # ==========================================
    # CALENDARIO Y ACTIVIDADES
    # ==========================================
    "Calendario y Actividades": [
        ("view_room", "Ver Calendario y Salas"),
        ("add_room", "Crear Salas"),
        ("change_room", "Editar Salas"),
        ("delete_room", "Eliminar Salas"),
        ("view_activity", "Ver Actividades"),
        ("add_activity", "Crear Actividades"),
        ("change_activity", "Editar Actividades"),
        ("delete_activity", "Eliminar Actividades"),
        ("view_activitysession", "Ver Sesiones de Clases"),
        ("add_activitysession", "Crear Sesiones de Clases"),
        ("change_activitysession", "Editar Sesiones de Clases"),
        ("delete_activitysession", "Eliminar Sesiones de Clases"),
        ("view_schedulesettings", "Ver Configuración de Horarios"),
        ("change_schedulesettings", "Modificar Configuración de Horarios"),
        ("view_booking", "Ver Reservas de Clases"),
        ("add_booking", "Crear Reservas de Clases"),
        ("change_booking", "Editar Reservas de Clases"),
        ("delete_booking", "Cancelar Reservas de Clases"),
    ],
    
    # ==========================================
    # RUTINAS Y EJERCICIOS
    # ==========================================
    "Rutinas y Ejercicios": [
        # Ejercicios
        ("view_exercise", "Ver Ejercicios"),
        ("add_exercise", "Crear Ejercicios"),
        ("change_exercise", "Editar Ejercicios"),
        ("delete_exercise", "Eliminar Ejercicios"),
        
        # Etiquetas de Ejercicios
        ("view_exercisetag", "Ver Etiquetas de Ejercicios"),
        ("add_exercisetag", "Crear Etiquetas"),
        ("change_exercisetag", "Editar Etiquetas"),
        ("delete_exercisetag", "Eliminar Etiquetas"),
        
        # Rutinas
        ("view_workoutroutine", "Ver Rutinas"),
        ("add_workoutroutine", "Crear Rutinas"),
        ("change_workoutroutine", "Editar Rutinas"),
        ("delete_workoutroutine", "Eliminar Rutinas"),
        ("duplicate_workoutroutine", "Duplicar Rutinas"),
        
        # Asignación de Rutinas
        ("view_clientroutine", "Ver Rutinas Asignadas"),
        ("add_clientroutine", "Asignar Rutinas a Clientes"),
        ("change_clientroutine", "Modificar Asignaciones"),
        ("delete_clientroutine", "Eliminar Asignaciones"),
        
        # Registros de Entrenamientos
        ("view_workoutlog", "Ver Registros de Entrenamientos"),
        ("view_all_workoutlogs", "Ver Entrenamientos de Todos"),
        ("view_own_workoutlogs", "Ver Solo Mis Entrenamientos"),
    ],
    
    # ==========================================
    # GAMIFICACIÓN
    # ==========================================
    "Gamificación": [
        # Configuración
        ("view_gamificationsettings", "Ver Configuración de Gamificación"),
        ("change_gamificationsettings", "Editar Configuración de Gamificación"),
        
        # Logros
        ("view_achievement", "Ver Logros"),
        ("add_achievement", "Crear Logros"),
        ("change_achievement", "Editar Logros"),
        ("delete_achievement", "Eliminar Logros"),
        
        # Desafíos
        ("view_challenge", "Ver Desafíos"),
        ("add_challenge", "Crear Desafíos"),
        ("change_challenge", "Editar Desafíos"),
        ("delete_challenge", "Eliminar Desafíos"),
        
        # Progreso de Clientes
        ("view_clientprogress", "Ver Progreso de Clientes"),
        ("change_clientprogress", "Ajustar Puntos/XP"),
        ("view_xptransaction", "Ver Historial de XP"),
        
        # Recompensas
        ("view_reward", "Ver Recompensas"),
        ("add_reward", "Crear Recompensas"),
        ("change_reward", "Editar Recompensas"),
        ("delete_reward", "Eliminar Recompensas"),
        ("redeem_reward", "Canjear Recompensas"),
        
        # Rankings
        ("view_leaderboard", "Ver Rankings/Leaderboard"),
    ],
    
    # ==========================================
    # TAQUILLAS (LOCKERS)
    # ==========================================
    "Taquillas": [
        # Zonas
        ("view_lockerzone", "Ver Zonas de Taquillas"),
        ("add_lockerzone", "Crear Zonas"),
        ("change_lockerzone", "Editar Zonas"),
        ("delete_lockerzone", "Eliminar Zonas"),
        
        # Taquillas
        ("view_locker", "Ver Taquillas"),
        ("add_locker", "Crear Taquillas"),
        ("change_locker", "Editar Taquillas"),
        ("delete_locker", "Eliminar Taquillas"),
        ("view_locker_map", "Ver Mapa de Taquillas"),
        
        # Asignaciones
        ("view_lockerassignment", "Ver Asignaciones"),
        ("add_lockerassignment", "Asignar Taquillas"),
        ("change_lockerassignment", "Modificar Asignaciones"),
        ("delete_lockerassignment", "Liberar Taquillas"),
        ("force_release_locker", "Forzar Liberación de Taquilla"),
        
        # Incidencias
        ("view_lockerincident", "Ver Incidencias de Taquillas"),
        ("add_lockerincident", "Reportar Incidencias"),
        ("resolve_lockerincident", "Resolver Incidencias"),
    ],
    
    # ==========================================
    # RECONOCIMIENTO FACIAL
    # ==========================================
    "Reconocimiento Facial": [
        # Configuración
        ("view_facerecognitionsettings", "Ver Configuración Facial"),
        ("change_facerecognitionsettings", "Editar Configuración Facial"),
        
        # Registros Faciales
        ("view_clientfaceencoding", "Ver Registros Faciales"),
        ("add_clientfaceencoding", "Registrar Cara de Cliente"),
        ("delete_clientfaceencoding", "Eliminar Registro Facial"),
        
        # Logs
        ("view_facerecognitionlog", "Ver Logs de Reconocimiento"),
        ("export_facerecognitionlog", "Exportar Logs"),
        
        # Acceso al Terminal
        ("access_facialcheckin", "Acceder al Terminal de Check-in Facial"),
    ],
    
    # ==========================================
    # DASHBOARDS Y ANALYTICS
    # ==========================================
    "Dashboards y Analytics": [
        # Dashboard Principal
        ("view_dashboard", "Ver Dashboard Principal"),
        
        # Analytics de Clientes
        ("view_client_analytics", "Ver Analytics de Clientes"),
        ("view_retention_report", "Ver Informe de Retención"),
        ("view_churn_report", "Ver Informe de Bajas"),
        
        # Analytics de Ventas
        ("view_sales_analytics", "Ver Analytics de Ventas"),
        ("view_revenue_report", "Ver Informe de Ingresos"),
        ("view_product_report", "Ver Informe de Productos"),
        
        # Analytics de Actividades
        ("view_activity_analytics", "Ver Analytics de Actividades"),
        ("view_occupancy_report", "Ver Informe de Ocupación"),
        ("view_attendance_report", "Ver Informe de Asistencia"),
        
        # Analytics de Staff
        ("view_staff_analytics", "Ver Analytics de Staff"),
        ("view_performance_report", "Ver Informe de Rendimiento"),
        
        # Exportación
        ("export_analytics", "Exportar Informes de Analytics"),
        
        # Configuración
        ("view_analytics_settings", "Ver Configuración de Analytics"),
        ("change_analytics_settings", "Editar Configuración de Analytics"),
    ],
    
    # ==========================================
    # CONTROL DE ACCESO
    # ==========================================
    "Control de Acceso": [
        # Registro de Accesos
        ("view_accesslog", "Ver Registro de Accesos"),
        ("export_accesslog", "Exportar Registro de Accesos"),
        
        # Reglas de Acceso
        ("view_accessrule", "Ver Reglas de Acceso"),
        ("add_accessrule", "Crear Reglas de Acceso"),
        ("change_accessrule", "Editar Reglas de Acceso"),
        ("delete_accessrule", "Eliminar Reglas de Acceso"),
        
        # Check-in Manual
        ("manual_checkin", "Check-in Manual de Clientes"),
        ("manual_checkout", "Check-out Manual de Clientes"),
        
        # Configuración
        ("view_accesssettings", "Ver Configuración de Acceso"),
        ("change_accesssettings", "Editar Configuración de Acceso"),
    ],
    
    # ==========================================
    # OBJETIVOS
    # ==========================================
    "Objetivos": [
        ("view_gymgoal", "Ver Objetivos del Gimnasio"),
        ("add_gymgoal", "Crear Objetivos"),
        ("change_gymgoal", "Editar Objetivos"),
        ("delete_gymgoal", "Eliminar Objetivos"),
        ("view_goaltracking", "Ver Seguimiento de Objetivos"),
    ],
    
    # ==========================================
    # CONFIGURACIÓN GENERAL
    # ==========================================
    "Configuración": [
        # Gimnasio
        ("view_gym_settings", "Ver Configuración del Gimnasio"),
        ("change_gym_settings", "Editar Configuración del Gimnasio"),
        
        # Notificaciones
        ("view_notification_settings", "Ver Configuración de Notificaciones"),
        ("change_notification_settings", "Editar Configuración de Notificaciones"),
        
        # Integraciones
        ("view_integrations", "Ver Integraciones"),
        ("change_integrations", "Configurar Integraciones"),
        
        # Plantillas de Email
        ("view_emailtemplate", "Ver Plantillas de Email"),
        ("change_emailtemplate", "Editar Plantillas de Email"),
        
        # Backup/Restore
        ("view_backup", "Ver Copias de Seguridad"),
        ("create_backup", "Crear Copia de Seguridad"),
        ("restore_backup", "Restaurar Copia de Seguridad"),
    ],
}


def get_all_managed_permissions():
    """
    Returns a flat list of all permission codenames managed by this system.
    """
    perms = []
    for module, actions in PERMISSION_STRUCTURE.items():
        for codename, label in actions:
            perms.append(codename)
    return perms
