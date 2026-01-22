"""
API Views for Client Documents (Mobile App).
List contracts, terms, and handle digital signatures.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.files.base import ContentFile
import base64
import uuid

from clients.models import Client, ClientDocument


class DocumentListView(views.APIView):
    """
    List client documents.
    
    GET /api/documents/
    Query params:
    - status: 'PENDING' | 'SIGNED' (optional)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        status_filter = request.query_params.get('status')
        documents = ClientDocument.objects.filter(client=client)
        
        if status_filter:
            documents = documents.filter(status=status_filter)
            
        documents = documents.order_by('-created_at')
        
        data = [{
            'id': doc.id,
            'name': doc.name,
            'document_type': doc.document_type,
            'status': doc.status,
            'requires_signature': doc.requires_signature,
            'created_at': doc.created_at.isoformat(),
            'signed_at': doc.signed_at.isoformat() if doc.signed_at else None,
            'file_url': doc.file.url if doc.file else None,
            'has_content': bool(doc.content),
        } for doc in documents]
        
        return Response({
            'count': len(data),
            'documents': data
        })


class DocumentDetailView(views.APIView):
    """
    Get document details and content.
    
    GET /api/documents/<id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, document_id):
        try:
            client = Client.objects.get(user=request.user)
            document = ClientDocument.objects.get(id=document_id, client=client)
        except (Client.DoesNotExist, ClientDocument.DoesNotExist):
            return Response(
                {'error': 'Documento no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            'id': document.id,
            'name': document.name,
            'document_type': document.document_type,
            'status': document.status,
            'requires_signature': document.requires_signature,
            'content': document.content, # HTML content
            'file_url': document.file.url if document.file else None,
            'created_at': document.created_at.isoformat(),
            'signed_at': document.signed_at.isoformat() if document.signed_at else None,
        })


class SignDocumentView(views.APIView):
    """
    Sign a document.
    Expects a base64 encoded PNG image of the signature.
    
    POST /api/documents/<id>/sign/
    Body: { signature_image: "base64_string..." }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, document_id):
        try:
            client = Client.objects.get(user=request.user)
            document = ClientDocument.objects.get(id=document_id, client=client)
        except (Client.DoesNotExist, ClientDocument.DoesNotExist):
            return Response(
                {'error': 'Documento no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        if document.status == 'SIGNED' or document.is_signed:
            return Response(
                {'error': 'El documento ya está firmado'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        signature_data = request.data.get('signature_image')
        if not signature_data:
            return Response(
                {'error': 'Se requiere la imagen de la firma'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Decode base64 image
            format, imgstr = signature_data.split(';base64,') 
            ext = format.split('/')[-1] 
            data = ContentFile(base64.b64decode(imgstr), name=f'{uuid.uuid4()}.{ext}')
            
            # Save signature
            document.signature_image = data
            document.status = 'SIGNED'
            document.is_signed = True
            
            from django.utils import timezone
            document.signed_at = timezone.now()
            
            # Get IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            document.signed_ip = ip
            
            document.save()
            
            return Response({
                'success': True,
                'message': 'Documento firmado correctamente',
                'signed_at': document.signed_at.isoformat()
            })
            
        except Exception as e:
            print(f"Error signing document: {e}")
            return Response(
                {'error': 'Error procesando la firma'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
