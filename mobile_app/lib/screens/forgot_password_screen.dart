import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';
import 'gym_search_screen.dart'; // For HexColor

class ForgotPasswordScreen extends StatefulWidget {
  final Color? brandColor;
  
  const ForgotPasswordScreen({super.key, this.brandColor});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> with SingleTickerProviderStateMixin {
  final _emailCtrl = TextEditingController();
  final _codeCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmPasswordCtrl = TextEditingController();
  
  bool _isLoading = false;
  String? _message;
  bool _isError = false;
  int _currentStep = 0; // 0 = request code, 1 = enter code and password
  
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    );
    _animationController.forward();
  }

  @override
  void dispose() {
    _emailCtrl.dispose();
    _codeCtrl.dispose();
    _passwordCtrl.dispose();
    _confirmPasswordCtrl.dispose();
    _animationController.dispose();
    super.dispose();
  }

  Color get brandColor => widget.brandColor ?? const Color(0xFF0F172A);

  Future<void> _requestCode() async {
    final email = _emailCtrl.text.trim();
    
    if (email.isEmpty || !email.contains('@')) {
      setState(() {
        _message = 'Por favor ingresa un email válido';
        _isError = true;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _message = null;
    });

    final api = Provider.of<ApiService>(context, listen: false);
    final result = await api.requestPasswordReset(email);

    if (mounted) {
      setState(() {
        _isLoading = false;
        _message = result['message'];
        _isError = !result['success'];
        
        if (result['success']) {
          _currentStep = 1;
          _animationController.reset();
          _animationController.forward();
        }
      });
    }
  }

  Future<void> _confirmReset() async {
    final email = _emailCtrl.text.trim();
    final code = _codeCtrl.text.trim();
    final password = _passwordCtrl.text;
    final confirmPassword = _confirmPasswordCtrl.text;

    if (code.isEmpty || code.length != 6) {
      setState(() {
        _message = 'El código debe tener 6 dígitos';
        _isError = true;
      });
      return;
    }

    if (password.isEmpty || password.length < 6) {
      setState(() {
        _message = 'La contraseña debe tener al menos 6 caracteres';
        _isError = true;
      });
      return;
    }

    if (password != confirmPassword) {
      setState(() {
        _message = 'Las contraseñas no coinciden';
        _isError = true;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _message = null;
    });

    final api = Provider.of<ApiService>(context, listen: false);
    final result = await api.confirmPasswordReset(email, code, password);

    if (mounted) {
      setState(() {
        _isLoading = false;
        _message = result['message'];
        _isError = !result['success'];
      });

      if (result['success']) {
        // Wait a moment to show success message, then navigate back to login
        await Future.delayed(const Duration(seconds: 2));
        if (mounted) {
          Navigator.of(context).pop();
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.black),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: FadeTransition(
            opacity: _fadeAnimation,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Icon
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    color: brandColor.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    _currentStep == 0 ? Icons.lock_reset : Icons.vpn_key,
                    size: 40,
                    color: brandColor,
                  ),
                ),
                const SizedBox(height: 24),

                // Title
                Text(
                  _currentStep == 0 ? 'Recuperar Contraseña' : 'Restablecer Contraseña',
                  style: const TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),

                // Subtitle
                Text(
                  _currentStep == 0
                      ? 'Ingresa tu email y te enviaremos un código de recuperación'
                      : 'Ingresa el código que recibiste y tu nueva contraseña',
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.grey[600],
                  ),
                ),
                const SizedBox(height: 32),

                // Form
                if (_currentStep == 0) ..._buildStep1() else ..._buildStep2(),

                // Message
                if (_message != null) ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: _isError 
                          ? Colors.red.withOpacity(0.1)
                          : Colors.green.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: _isError ? Colors.red : Colors.green,
                        width: 1,
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          _isError ? Icons.error_outline : Icons.check_circle_outline,
                          color: _isError ? Colors.red : Colors.green,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            _message!,
                            style: TextStyle(
                              color: _isError ? Colors.red[900] : Colors.green[900],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 24),

                // Action Button
                ElevatedButton(
                  onPressed: _isLoading ? null : (_currentStep == 0 ? _requestCode : _confirmReset),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: brandColor,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    elevation: 0,
                  ),
                  child: _isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            color: Colors.white,
                            strokeWidth: 2,
                          ),
                        )
                      : Text(
                          _currentStep == 0 ? 'Enviar Código' : 'Restablecer Contraseña',
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                ),

                // Additional actions
                if (_currentStep == 1) ...[
                  const SizedBox(height: 16),
                  TextButton(
                    onPressed: _isLoading ? null : () {
                      setState(() {
                        _currentStep = 0;
                        _codeCtrl.clear();
                        _passwordCtrl.clear();
                        _confirmPasswordCtrl.clear();
                        _message = null;
                        _animationController.reset();
                        _animationController.forward();
                      });
                    },
                    child: Text(
                      '¿No recibiste el código? Solicitar nuevo código',
                      style: TextStyle(
                        color: brandColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _buildStep1() {
    return [
      TextField(
        controller: _emailCtrl,
        keyboardType: TextInputType.emailAddress,
        decoration: InputDecoration(
          labelText: 'Email',
          prefixIcon: const Icon(Icons.email_outlined),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: brandColor, width: 2),
          ),
        ),
      ),
    ];
  }

  List<Widget> _buildStep2() {
    return [
      TextField(
        controller: _codeCtrl,
        keyboardType: TextInputType.number,
        maxLength: 6,
        textAlign: TextAlign.center,
        style: const TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.bold,
          letterSpacing: 8,
        ),
        inputFormatters: [
          FilteringTextInputFormatter.digitsOnly,
        ],
        decoration: InputDecoration(
          labelText: 'Código de 6 dígitos',
          hintText: '000000',
          counterText: '',
          prefixIcon: const Icon(Icons.pin_outlined),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: brandColor, width: 2),
          ),
        ),
      ),
      const SizedBox(height: 16),
      TextField(
        controller: _passwordCtrl,
        obscureText: true,
        decoration: InputDecoration(
          labelText: 'Nueva Contraseña',
          prefixIcon: const Icon(Icons.lock_outlined),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: brandColor, width: 2),
          ),
        ),
      ),
      const SizedBox(height: 16),
      TextField(
        controller: _confirmPasswordCtrl,
        obscureText: true,
        decoration: InputDecoration(
          labelText: 'Confirmar Contraseña',
          prefixIcon: const Icon(Icons.lock_outlined),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: brandColor, width: 2),
          ),
        ),
      ),
    ];
  }
}
