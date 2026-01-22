import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:signature/signature.dart'; // Add to pubspec.yaml: signature: ^5.0.0
import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';
import '../api/api_service.dart';

class DocumentDetailScreen extends StatefulWidget {
  final int documentId;
  final String documentName;

  const DocumentDetailScreen({
    super.key,
    required this.documentId,
    required this.documentName,
  });

  @override
  State<DocumentDetailScreen> createState() => _DocumentDetailScreenState();
}

class _DocumentDetailScreenState extends State<DocumentDetailScreen> {
  Map<String, dynamic>? _document;
  bool _isLoading = true;
  String? _errorMessage;
  bool _isSigning = false;
  
  // Signature Controller
  late SignatureController _signatureController;

  @override
  void initState() {
    super.initState();
    _signatureController = SignatureController(
      penStrokeWidth: 3,
      penColor: Colors.black,
      exportBackgroundColor: Colors.white,
    );
    _loadDocumentDetail();
  }

  @override
  void dispose() {
    _signatureController.dispose();
    super.dispose();
  }

  Future<void> _loadDocumentDetail() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final api = Provider.of<ApiService>(context, listen: false);
    final result = await api.getDocumentDetail(widget.documentId);

    if (result['success'] == true) {
      setState(() {
        _document = result;
        _isLoading = false;
      });
    } else {
      setState(() {
        _errorMessage = result['message'] ?? 'Error cargando documento';
        _isLoading = false;
      });
    }
  }

  Future<void> _submitSignature() async {
    if (_signatureController.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, firma el documento antes de enviar.')),
      );
      return;
    }

    // Confirm dialog
    final bool? confirm = await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirmar Firma'),
        content: const Text('¿Estás seguro de que quieres firmar y enviar este documento? Esta acción es legalmente vinculante.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF0F172A),
              foregroundColor: Colors.white,
            ),
            child: const Text('Confirmar y Enviar'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    setState(() {
      _isSigning = true;
    });

    try {
      // Export signature to PNG bytes
      final Uint8List? data = await _signatureController.toPngBytes();
      
      if (data == null) {
        throw Exception('Error exportando firma');
      }
      
      // Convert to base64
      final String base64Signature = 'data:image/png;base64,${base64Encode(data)}';
      
      // Send to API
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.signDocument(widget.documentId, base64Signature);
      
      if (result['success'] == true) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Documento firmado correctamente'),
            backgroundColor: Color(0xFF10B981),
          ),
        );
        Navigator.of(context).pop(true); // Return to list and refresh
      } else {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message'] ?? 'Error enviando firma'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSigning = false;
        });
      }
    }
  }
  
  void _clearSignature() {
    _signatureController.clear();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: Text(
          widget.documentName,
          style: const TextStyle(color: Colors.white, fontSize: 16),
        ),
        backgroundColor: const Color(0xFF0F172A),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage != null
              ? Center(child: Text(_errorMessage!))
              : _buildContent(),
    );
  }

  Widget _buildContent() {
    final bool isSigned = _document?['status'] == 'SIGNED';
    final String? content = _document?['content'];
    
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Document Header
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey[200]!),
            ),
            child: Row(
              children: [
                Icon(
                  isSigned ? Icons.check_circle : Icons.pending_actions,
                  color: isSigned ? Colors.green : Colors.orange,
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Estado: ${_document?['status'] ?? 'Desconocido'}',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    if (isSigned && _document?['signed_at'] != null)
                      Text(
                        'Firmado el: ${_document?['signed_at'].toString().split('T')[0]}',
                        style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                      ),
                  ],
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 24),
          
          // Document Content (HTML)
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey[300]!),
            ),
            child: content != null && content.isNotEmpty
                ? HtmlWidget(
                    content,
                    textStyle: const TextStyle(fontSize: 14, height: 1.5),
                  )
                : const Center(
                    child: Text('Sin contenido visualizable. Descarga el archivo si está disponible.'),
                  ),
          ),
          
          const SizedBox(height: 32),
          
          // Signature Area
          if (!isSigned) ...[
            const Text(
              'Firma aquí',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF0F172A),
              ),
            ),
            const SizedBox(height: 8),
            Container(
              height: 200,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey),
                borderRadius: BorderRadius.circular(12),
                color: Colors.white,
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Signature(
                  controller: _signatureController,
                  backgroundColor: Colors.white,
                ),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                TextButton(
                  onPressed: _clearSignature,
                  child: const Text('Borrar Firma', style: TextStyle(color: Colors.red)),
                ),
                const Text(
                  'Firma digital legalmente vinculante',
                  style: TextStyle(fontSize: 10, color: Colors.grey),
                ),
              ],
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _isSigning ? null : _submitSignature,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0F172A),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: _isSigning
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                      )
                    : const Text(
                        'FIRMAR DOCUMENTO',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
              ),
            ),
          ] else ...[
             const Center(
               child: Text(
                 'Este documento ya ha sido firmado.',
                 style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold),
               ),
             ),
          ],
          
          const SizedBox(height: 40),
        ],
      ),
    );
  }
}
