import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';
import '../models/models.dart';
import 'gym_search_screen.dart'; // For HexColor
import 'forgot_password_screen.dart';
import 'register_screen.dart';

class LoginScreen extends StatefulWidget {
  final Gym? selectedGym;

  const LoginScreen({super.key, this.selectedGym});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _isLoading = false;
  bool _isPasswordVisible = false;
  String? _error;

  Future<void> _login() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final api = Provider.of<ApiService>(context, listen: false);
    final success = await api.login(
      _emailCtrl.text,
      _passwordCtrl.text,
      gymId: widget.selectedGym?.id,
      gym: widget
          .selectedGym, // Pasar el gym completo para guardar el brand color
    );

    if (mounted) {
      setState(() => _isLoading = false);
      if (success) {
        Navigator.of(context)
            .pushNamedAndRemoveUntil('/home', (route) => false);
      } else {
        setState(() =>
            _error = 'Credenciales inválidas o no perteneces a este centro.');
      }
    }
  }

  void _goToRegister() {
    if (widget.selectedGym != null) {
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => RegisterScreen(gym: widget.selectedGym!),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final gym = widget.selectedGym; // If null, generic login (optional)
    final brandColor =
        gym != null ? HexColor(gym.brandColor) : const Color(0xFF0F172A);
    final canRegister = gym?.allowSelfRegistration ?? false;

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
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Logo / Brand
              if (gym != null) ...[
                Center(
                  child: Container(
                    width: 120,
                    height: 120,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [
                        if (gym.logoUrl.isEmpty)
                          BoxShadow(
                            color: brandColor.withOpacity(0.2),
                            blurRadius: 20,
                            offset: const Offset(0, 10),
                          )
                      ],
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(20),
                      child: gym.logoUrl.isNotEmpty
                          ? Image.network(
                              gym.logoUrl.startsWith('http')
                                  ? gym.logoUrl
                                  : 'http://localhost:8000${gym.logoUrl}', // Fix for relative paths in local dev
                              fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => Icon(
                                  Icons.fitness_center,
                                  size: 50,
                                  color: brandColor),
                            )
                          : Icon(Icons.fitness_center,
                              size: 50, color: brandColor),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                Text(
                  gym.name,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(
                  gym.city,
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey[600]),
                ),
              ] else ...[
                const Text(
                  'Iniciar Sesión',
                  style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                ),
              ],

              const SizedBox(height: 48),

              // Form
              TextField(
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: 'Email',
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.all(Radius.circular(12))),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _passwordCtrl,
                obscureText: !_isPasswordVisible,
                decoration: InputDecoration(
                  labelText: 'Contraseña',
                  border: const OutlineInputBorder(
                      borderRadius: BorderRadius.all(Radius.circular(12))),
                  suffixIcon: IconButton(
                    icon: Icon(
                      _isPasswordVisible
                          ? Icons.visibility
                          : Icons.visibility_off,
                      color: Colors.grey,
                    ),
                    onPressed: () {
                      setState(() {
                        _isPasswordVisible = !_isPasswordVisible;
                      });
                    },
                  ),
                ),
              ),

              // Forgot Password
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) =>
                            ForgotPasswordScreen(brandColor: brandColor),
                      ),
                    );
                  },
                  child: Text(
                    '¿Olvidaste tu contraseña?',
                    style: TextStyle(
                        color: brandColor, fontWeight: FontWeight.w600),
                  ),
                ),
              ),

              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(
                  _error!,
                  style: const TextStyle(color: Colors.red),
                  textAlign: TextAlign.center,
                ),
              ],

              const SizedBox(height: 24),

              ElevatedButton(
                onPressed: _isLoading ? null : _login,
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
                            color: Colors.white, strokeWidth: 2))
                    : const Text('Entrar',
                        style: TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold)),
              ),

              // Register button - only shown if gym allows self registration
              if (canRegister) ...[
                const SizedBox(height: 16),
                TextButton(
                  onPressed: _goToRegister,
                  child: Text.rich(
                    TextSpan(
                      text: '¿No tienes cuenta? ',
                      style: TextStyle(color: Colors.grey[600]),
                      children: [
                        TextSpan(
                          text: 'Regístrate',
                          style: TextStyle(
                            color: brandColor,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
