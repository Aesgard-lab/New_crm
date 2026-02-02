import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../api/api_service.dart';

/// Pantalla para escanear el QR de una sesión y hacer check-in.
/// El cliente abre la cámara, escanea el QR de la sesión (mostrado en tablet/recepción),
/// y confirma su asistencia automáticamente.
class QrScannerScreen extends StatefulWidget {
  const QrScannerScreen({super.key});

  @override
  State<QrScannerScreen> createState() => _QrScannerScreenState();
}

class _QrScannerScreenState extends State<QrScannerScreen> {
  MobileScannerController? _scannerController;
  bool _isProcessing = false;
  bool _hasScanned = false;
  String? _resultMessage;
  bool _isSuccess = false;
  Map<String, dynamic>? _sessionInfo;
  bool _torchEnabled = false;

  @override
  void initState() {
    super.initState();
    _scannerController = MobileScannerController(
      detectionSpeed: DetectionSpeed.normal,
      facing: CameraFacing.back,
      torchEnabled: false,
    );
  }

  @override
  void dispose() {
    _scannerController?.dispose();
    super.dispose();
  }

  Future<void> _processQRCode(String qrContent) async {
    if (_isProcessing || _hasScanned) return;

    setState(() {
      _isProcessing = true;
      _hasScanned = true;
    });

    // Pausar el escáner
    _scannerController?.stop();

    final api = Provider.of<ApiService>(context, listen: false);
    final result = await api.qrCheckin(qrContent);

    setState(() {
      _isProcessing = false;
      _isSuccess = result['success'] == true;
      _resultMessage = result['message'] ??
          (result['success'] == true
              ? '¡Asistencia registrada!'
              : 'Error al procesar el check-in');
      _sessionInfo = result['success'] == true
          ? {
              'session_name': result['session_name'],
              'session_time': result['session_time'],
              'room': result['room'],
            }
          : null;
    });

    _showResultDialog();
  }

  void _showResultDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      isDismissible: false,
      builder: (context) => Container(
        padding: const EdgeInsets.all(24),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Icono de resultado
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  colors: _isSuccess
                      ? [const Color(0xFF10B981), const Color(0xFF059669)]
                      : [const Color(0xFFEF4444), const Color(0xFFDC2626)],
                ),
              ),
              child: Icon(
                _isSuccess ? Icons.check : Icons.close,
                color: Colors.white,
                size: 40,
              ),
            ),
            const SizedBox(height: 20),

            // Título
            Text(
              _isSuccess ? '¡Check-in realizado!' : 'Error',
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: Color(0xFF1E293B),
              ),
            ),
            const SizedBox(height: 12),

            // Mensaje
            Text(
              _resultMessage ?? '',
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 16,
                color: Color(0xFF64748B),
              ),
            ),

            // Info de la sesión
            if (_sessionInfo != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.fitness_center,
                      color: Color(0xFF64748B),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _sessionInfo!['session_name'] ?? '',
                            style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF1E293B),
                            ),
                          ),
                          Text(
                            '${_sessionInfo!['session_time'] ?? ''} - ${_sessionInfo!['room'] ?? 'Por asignar'}',
                            style: const TextStyle(
                              fontSize: 13,
                              color: Color(0xFF64748B),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 24),

            // Botón
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.pop(context);
                  if (_isSuccess) {
                    Navigator.pop(context); // Volver a pantalla anterior
                  } else {
                    // Reiniciar el escáner
                    setState(() {
                      _hasScanned = false;
                      _resultMessage = null;
                    });
                    _scannerController?.start();
                  }
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0F172A),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                child: Text(
                  _isSuccess ? 'Entendido' : 'Intentar de nuevo',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.white,
        elevation: 0,
        title: const Text('Check-in con QR'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          // Botón de flash
          IconButton(
            icon: Icon(
              _torchEnabled ? Icons.flash_on : Icons.flash_off,
              color: _torchEnabled ? Colors.yellow : Colors.white,
            ),
            onPressed: () async {
              await _scannerController?.toggleTorch();
              setState(() {
                _torchEnabled = !_torchEnabled;
              });
            },
          ),
          // Botón de cambiar cámara
          IconButton(
            icon: const Icon(Icons.flip_camera_ios),
            onPressed: () => _scannerController?.switchCamera(),
          ),
        ],
      ),
      body: Stack(
        children: [
          // Scanner
          MobileScanner(
            controller: _scannerController,
            onDetect: (capture) {
              final List<Barcode> barcodes = capture.barcodes;
              for (final barcode in barcodes) {
                if (barcode.rawValue != null) {
                  _processQRCode(barcode.rawValue!);
                  break;
                }
              }
            },
          ),

          // Overlay con marco de escaneo
          CustomPaint(
            size: Size.infinite,
            painter: ScannerOverlayPainter(
              borderColor: Theme.of(context).primaryColor,
            ),
          ),

          // Instrucciones en la parte inferior
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Container(
              padding: const EdgeInsets.all(24),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Colors.transparent, Colors.black87],
                ),
              ),
              child: Column(
                children: [
                  const Icon(
                    Icons.qr_code_scanner,
                    color: Colors.white,
                    size: 32,
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Escanea el código QR',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Apunta la cámara al QR de la sesión\nque se muestra en la pantalla de recepción',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.7),
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),

          // Indicador de procesamiento
          if (_isProcessing)
            Container(
              color: Colors.black54,
              child: const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(
                      color: Colors.white,
                    ),
                    SizedBox(height: 16),
                    Text(
                      'Verificando...',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Painter para dibujar el overlay del escáner con el marco central
class ScannerOverlayPainter extends CustomPainter {
  final Color borderColor;
  final double borderRadius;
  final double borderLength;
  final double borderWidth;
  final double cutOutSize;

  ScannerOverlayPainter({
    this.borderColor = Colors.white,
    this.borderRadius = 16,
    this.borderLength = 40,
    this.borderWidth = 4,
    this.cutOutSize = 280,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final double left = (size.width - cutOutSize) / 2;
    final double top = (size.height - cutOutSize) / 2;
    final double right = left + cutOutSize;
    final double bottom = top + cutOutSize;

    // Fondo oscuro con hueco central
    final backgroundPath = Path()
      ..addRect(Rect.fromLTWH(0, 0, size.width, size.height));

    final cutoutPath = Path()
      ..addRRect(RRect.fromRectAndRadius(
        Rect.fromLTRB(left, top, right, bottom),
        Radius.circular(borderRadius),
      ));

    final paint = Paint()
      ..color = Colors.black.withOpacity(0.5)
      ..style = PaintingStyle.fill;

    canvas.drawPath(
      Path.combine(PathOperation.difference, backgroundPath, cutoutPath),
      paint,
    );

    // Esquinas del marco
    final borderPaint = Paint()
      ..color = borderColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = borderWidth
      ..strokeCap = StrokeCap.round;

    // Esquina superior izquierda
    canvas.drawLine(
      Offset(left, top + borderRadius),
      Offset(left, top + borderLength),
      borderPaint,
    );
    canvas.drawLine(
      Offset(left + borderRadius, top),
      Offset(left + borderLength, top),
      borderPaint,
    );

    // Esquina superior derecha
    canvas.drawLine(
      Offset(right, top + borderRadius),
      Offset(right, top + borderLength),
      borderPaint,
    );
    canvas.drawLine(
      Offset(right - borderRadius, top),
      Offset(right - borderLength, top),
      borderPaint,
    );

    // Esquina inferior izquierda
    canvas.drawLine(
      Offset(left, bottom - borderRadius),
      Offset(left, bottom - borderLength),
      borderPaint,
    );
    canvas.drawLine(
      Offset(left + borderRadius, bottom),
      Offset(left + borderLength, bottom),
      borderPaint,
    );

    // Esquina inferior derecha
    canvas.drawLine(
      Offset(right, bottom - borderRadius),
      Offset(right, bottom - borderLength),
      borderPaint,
    );
    canvas.drawLine(
      Offset(right - borderRadius, bottom),
      Offset(right - borderLength, bottom),
      borderPaint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
