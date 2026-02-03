from django.contrib.auth.models import Permission

# Define the logical structure for the Permission UI
# This maps a "Module Name" to a list of (Codename, Label) tuples
PERMISSION_STRUCTURE = {
    "Clientes": [
        ("view_client", "Ver Clientes"),
        ("add_client", "Crear Clientes"),
        ("change_client", "Editar Clientes"),
        ("delete_client", "Eliminar Clientes"),
        ("view_clientnote", "Ver Notas"),
        ("add_clientnote", "Añadir Notas"),
        ("change_clientnote", "Editar Notas"),
        ("delete_clientnote", "Eliminar Notas"),
    ],
    "Finanzas": [
        ("view_finance", "Ver Dashboard Financiero"),
        ("add_finance", "Crear Registros Financieros"),
        ("change_finance", "Editar Registros Financieros"),
        ("delete_finance", "Eliminar Registros Financieros"),
        ("view_invoice", "Ver Facturas"),
        ("add_invoice", "Crear Facturas"),
        ("change_invoice", "Editar Facturas"),
        ("delete_invoice", "Eliminar Facturas"),
        ("add_cashsession", "Abrir/Cerrar Caja"),
        ("view_paymentmethod", "Ver Métodos Pago"),
        ("add_paymentmethod", "Crear Métodos Pago"),
        ("change_paymentmethod", "Editar Métodos Pago"),
        ("delete_paymentmethod", "Eliminar Métodos Pago"),
    ],
    "Marketing": [
        ("view_marketing", "Ver Dashboard Marketing"),
        ("add_marketing", "Crear Registros Marketing"),
        ("change_marketing", "Editar Registros Marketing"),
        ("delete_marketing", "Eliminar Registros Marketing"),
        ("view_leadcard", "Ver Leads"),
        ("add_leadcard", "Crear Leads"),
        ("change_leadcard", "Editar Leads"),
        ("delete_leadcard", "Eliminar Leads"),
        ("view_campaign", "Ver Campañas Email"),
        ("add_campaign", "Crear Campañas Email"),
        ("change_campaign", "Editar Campañas Email"),
        ("delete_campaign", "Eliminar Campañas Email"),
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
    "Servicios & Productos": [
        ("view_service", "Ver Servicios"),
        ("add_service", "Crear Servicios"),
        ("change_service", "Editar Servicios"),
        ("delete_service", "Eliminar Servicios"),
        ("view_product", "Ver Productos"),
        ("add_product", "Crear Productos"),
        ("change_product", "Editar Productos"),
        ("delete_product", "Eliminar Productos"),
        ("view_membershipplan", "Ver Cuotas"),
        ("add_membershipplan", "Crear Cuotas"),
        ("change_membershipplan", "Editar Cuotas"),
        ("delete_membershipplan", "Eliminar Cuotas"),
    ],
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
    ],
    "Objetivos": [
        ("view_gymgoal", "Ver Objetivos del Gimnasio"),
        ("add_gymgoal", "Crear Objetivos"),
        ("change_gymgoal", "Editar Objetivos"),
        ("delete_gymgoal", "Eliminar Objetivos"),
    ],
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
    "Rutinas y Ejercicios": [
        ("view_workoutroutine", "Ver Rutinas"),
        ("add_workoutroutine", "Crear Rutinas"),
        ("change_workoutroutine", "Editar Rutinas"),
        ("delete_workoutroutine", "Eliminar Rutinas"),
        ("view_exercise", "Ver Ejercicios"),
        ("add_exercise", "Crear Ejercicios"),
        ("change_exercise", "Editar Ejercicios"),
        ("delete_exercise", "Eliminar Ejercicios"),
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
