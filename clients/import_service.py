"""
Servicio para importar clientes desde CSV
"""
import pandas as pd
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Client, ClientGroup, ClientTag


class ClientImportService:
    """
    Servicio para importar masivamente clientes desde CSV.
    Maneja validación, deduplicación y actualización de registros existentes.
    """
    
    # Mapeo de columnas esperadas en el CSV
    FIELD_MAPPING = {
        'first_name': ['nombre', 'first_name', 'nombre_cliente'],
        'last_name': ['apellido', 'last_name', 'apellidos', 'apellido_cliente'],
        'email': ['email', 'correo', 'email_cliente'],
        'phone_number': ['teléfono', 'telefono', 'phone', 'celular', 'movil'],
        'dni': ['dni', 'nif', 'id', 'document', 'cedula'],
        'birth_date': ['fecha_nacimiento', 'birth_date', 'nacimiento'],
        'gender': ['género', 'genero', 'gender', 'sexo'],
        'address': ['dirección', 'direccion', 'address', 'domicilio'],
        'status': ['estado', 'status', 'estatus'],
    }
    
    GENDER_MAPPING = {
        'm': 'M', 'male': 'M', 'masculino': 'M', 'hombre': 'M',
        'f': 'F', 'female': 'F', 'femenino': 'F', 'mujer': 'F',
        'o': 'O', 'otro': 'O', 'other': 'O',
        'x': 'X', 'no especificado': 'X', 'not specified': 'X'
    }
    
    STATUS_MAPPING = {
        'lead': 'LEAD', 'prospecto': 'LEAD', 'prospect': 'LEAD',
        'active': 'ACTIVE', 'activo': 'ACTIVE',
        'inactive': 'INACTIVE', 'inactivo': 'INACTIVE',
        'paused': 'PAUSED', 'excedencia': 'PAUSED',
        'blocked': 'BLOCKED', 'bloqueado': 'BLOCKED',
    }
    
    def __init__(self, gym):
        self.gym = gym
        self.results = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
            'warnings': []
        }
    
    def detect_column_names(self, df):
        """
        Detecta automáticamente los nombres de columnas del CSV
        y retorna un mapeo de campos reales.
        """
        detected = {}
        df_columns = [col.lower().strip() for col in df.columns]
        
        for field, aliases in self.FIELD_MAPPING.items():
            for alias in aliases:
                if alias in df_columns:
                    # Encontrar índice real
                    idx = df_columns.index(alias)
                    detected[field] = df.columns[idx]
                    break
        
        return detected
    
    def parse_date(self, date_str):
        """Intenta parsear diferentes formatos de fecha"""
        if pd.isna(date_str) or not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
            '%d/%m/%y', '%d-%m-%y',
            '%d.%m.%Y', '%d.%m.%y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Si no parsea, retornar None
        self.results['warnings'].append(f"No se pudo parsear fecha: {date_str}")
        return None
    
    def normalize_phone(self, phone):
        """Normaliza número de teléfono"""
        if pd.isna(phone) or not phone:
            return ''
        
        phone = str(phone).strip()
        # Remover espacios, guiones, paréntesis
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        return phone
    
    def check_duplicate(self, data):
        """
        Verifica si ya existe un cliente con similar información.
        Retorna el cliente existente si lo encuentra, None si no.
        """
        # Buscar por email (más confiable)
        if data.get('email'):
            client = Client.objects.filter(
                gym=self.gym,
                email__iexact=data['email']
            ).first()
            if client:
                return client
        
        # Buscar por DNI
        if data.get('dni'):
            client = Client.objects.filter(
                gym=self.gym,
                dni__iexact=data['dni']
            ).first()
            if client:
                return client
        
        # Buscar por nombre + teléfono
        if data.get('phone_number') and data.get('first_name'):
            client = Client.objects.filter(
                gym=self.gym,
                first_name__iexact=data['first_name'],
                phone_number=data['phone_number']
            ).first()
            if client:
                return client
        
        return None
    
    def import_from_csv(self, csv_file, update_existing=True, skip_errors=False):
        """
        Importa clientes desde archivo CSV.
        
        Args:
            csv_file: Objeto archivo CSV
            update_existing: Si True, actualiza clientes duplicados
            skip_errors: Si True, continúa con el siguiente cliente en caso de error
        
        Returns:
            dict con resultados de importación
        """
        try:
            # Leer CSV
            df = pd.read_csv(csv_file, encoding='utf-8')
            if df.empty:
                self.results['errors'].append("El archivo CSV está vacío")
                return self.results
            
            # Detectar columnas
            column_mapping = self.detect_column_names(df)
            
            if not column_mapping.get('first_name'):
                self.results['errors'].append(
                    "No se encontró columna de 'nombre'. "
                    "Asegúrate que exista una columna llamada 'nombre', 'first_name' o similar."
                )
                return self.results
            
            # Procesar cada fila
            with transaction.atomic():
                for idx, row in df.iterrows():
                    try:
                        client_data = self._extract_client_data(row, column_mapping)
                        
                        # Validar datos mínimos
                        if not client_data['first_name']:
                            self.results['skipped'] += 1
                            continue
                        
                        # Verificar duplicados
                        existing = self.check_duplicate(client_data)
                        
                        if existing:
                            if update_existing:
                                self._update_client(existing, client_data)
                                self.results['updated'] += 1
                            else:
                                self.results['skipped'] += 1
                        else:
                            self._create_client(client_data)
                            self.results['created'] += 1
                    
                    except Exception as e:
                        error_msg = f"Fila {idx + 2}: {str(e)}"
                        self.results['errors'].append(error_msg)
                        
                        if not skip_errors:
                            raise
        
        except pd.errors.ParserError as e:
            self.results['errors'].append(f"Error al leer el CSV: {str(e)}")
        except Exception as e:
            self.results['errors'].append(f"Error inesperado: {str(e)}")
        
        return self.results
    
    def _extract_client_data(self, row, column_mapping):
        """Extrae y normaliza datos de una fila del CSV"""
        data = {}
        
        # Nombre (obligatorio)
        data['first_name'] = str(row[column_mapping['first_name']]).strip() if column_mapping.get('first_name') else ''
        
        # Apellido
        if column_mapping.get('last_name'):
            data['last_name'] = str(row[column_mapping['last_name']]).strip() if pd.notna(row[column_mapping['last_name']]) else ''
        else:
            data['last_name'] = ''
        
        # Email
        if column_mapping.get('email'):
            email = row[column_mapping['email']]
            data['email'] = str(email).strip() if pd.notna(email) else ''
        else:
            data['email'] = ''
        
        # Teléfono
        if column_mapping.get('phone_number'):
            phone = row[column_mapping['phone_number']]
            data['phone_number'] = self.normalize_phone(phone)
        else:
            data['phone_number'] = ''
        
        # DNI
        if column_mapping.get('dni'):
            dni = row[column_mapping['dni']]
            data['dni'] = str(dni).strip().upper() if pd.notna(dni) else ''
        else:
            data['dni'] = ''
        
        # Fecha de nacimiento
        if column_mapping.get('birth_date'):
            data['birth_date'] = self.parse_date(row[column_mapping['birth_date']])
        else:
            data['birth_date'] = None
        
        # Género
        if column_mapping.get('gender'):
            gender = str(row[column_mapping['gender']]).strip().lower() if pd.notna(row[column_mapping['gender']]) else 'x'
            data['gender'] = self.GENDER_MAPPING.get(gender, 'X')
        else:
            data['gender'] = 'X'
        
        # Dirección
        if column_mapping.get('address'):
            address = row[column_mapping['address']]
            data['address'] = str(address).strip() if pd.notna(address) else ''
        else:
            data['address'] = ''
        
        # Estado
        if column_mapping.get('status'):
            status = str(row[column_mapping['status']]).strip().lower() if pd.notna(row[column_mapping['status']]) else 'lead'
            data['status'] = self.STATUS_MAPPING.get(status, 'LEAD')
        else:
            data['status'] = 'LEAD'
        
        return data
    
    def _create_client(self, data):
        """Crea un nuevo cliente"""
        Client.objects.create(
            gym=self.gym,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'] or None,
            phone_number=data['phone_number'],
            dni=data['dni'],
            birth_date=data['birth_date'],
            gender=data['gender'],
            address=data['address'],
            status=data['status']
        )
    
    def _update_client(self, client, data):
        """Actualiza un cliente existente"""
        client.first_name = data['first_name']
        client.last_name = data['last_name']
        
        if data['email'] and not client.email:
            client.email = data['email']
        
        if data['phone_number'] and not client.phone_number:
            client.phone_number = data['phone_number']
        
        if data['dni'] and not client.dni:
            client.dni = data['dni']
        
        if data['birth_date'] and not client.birth_date:
            client.birth_date = data['birth_date']
        
        if data['gender'] != 'X':
            client.gender = data['gender']
        
        if data['address'] and not client.address:
            client.address = data['address']
        
        # Actualizar estado si el cliente es LEAD
        if client.status == 'LEAD' and data['status'] != 'LEAD':
            client.status = data['status']
        
        client.save()
