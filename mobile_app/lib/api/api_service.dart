import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/models.dart';
import '../models/advertisement.dart';

import 'package:flutter/foundation.dart'; // for kIsWeb

class ApiService extends ChangeNotifier {
  // Use localhost for Web, 10.0.2.2 for Android Emulator
  static String get baseUrl {
    if (kIsWeb) return 'http://127.0.0.1:8000/api';
    return 'http://10.0.2.2:8000/api';
  }

  String? _token;
  Client? _currentClient;
  Gym? _currentGym;

  Client? get currentClient => _currentClient;
  Gym? get currentGym => _currentGym;
  
  // Colores del branding del gimnasio
  Color get brandColor {
    if (_currentGym?.brandColor != null) {
      return _hexToColor(_currentGym!.brandColor);
    }
    return const Color(0xFF6366F1); // Color por defecto (indigo)
  }
  
  Color get brandColorDark {
    final base = brandColor;
    // Oscurecer el color un 20%
    return Color.fromARGB(
      base.alpha,
      (base.red * 0.8).round(),
      (base.green * 0.8).round(),
      (base.blue * 0.8).round(),
    );
  }
  
  Color _hexToColor(String hex) {
    hex = hex.replaceFirst('#', '');
    if (hex.length == 6) {
      hex = 'FF$hex';
    }
    return Color(int.parse(hex, radix: 16));
  }
  
  void setCurrentGym(Gym gym) {
    _currentGym = gym;
    notifyListeners();
  }

  // Get system config (branding)
  Future<Map<String, dynamic>> getSystemConfig() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/system/config/'));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return {'system_name': 'Gym Portal', 'system_logo': null};
    } catch (e) {
      print('Error getting system config: $e');
      return {'system_name': 'Gym Portal', 'system_logo': null};
    }
  }

  Future<List<Gym>> searchGyms(String query) async {
    if (query.length < 2) return [];

    try {
      final url = '$baseUrl/gyms/search/?q=$query';
      print('🔍 Searching gyms with URL: $url');

      final response = await http.get(Uri.parse(url));
      print('📡 Response status: ${response.statusCode}');
      print('📦 Response body: ${response.body}');

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        print('✅ Found ${data.length} gyms');
        return data.map((json) => Gym.fromJson(json)).toList();
      }
      print('❌ Non-200 status code');
      return [];
    } catch (e) {
      print('💥 Error searching gyms: $e');
      return [];
    }
  }

  Future<bool> login(String email, String password, {int? gymId, Gym? gym}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/login/'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'email': email,
          'password': password,
          if (gymId != null) 'gym_id': gymId,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _token = data['token'];
        _currentClient = Client.fromJson(data['client']);
        
        // Guardar el gym si se proporcionó
        if (gym != null) {
          _currentGym = gym;
        }

        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('auth_token', _token!);
        // Guardar el color del gym
        if (_currentGym != null) {
          await prefs.setString('gym_brand_color', _currentGym!.brandColor);
          await prefs.setString('gym_name', _currentGym!.name);
          await prefs.setInt('gym_id', _currentGym!.id);
        }
        
        notifyListeners();
        return true;
      }
      return false;
    } catch (e) {
      print('Login error: $e');
      return false;
    }
  }

  /// Register a new client account
  Future<Map<String, dynamic>> registerClient({
    required int gymId,
    required String firstName,
    required String lastName,
    required String email,
    required String password,
    String? phoneNumber,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/registration/register/'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'gym_id': gymId,
          'first_name': firstName,
          'last_name': lastName,
          'email': email,
          'password': password,
          if (phoneNumber != null && phoneNumber.isNotEmpty) 'phone_number': phoneNumber,
        }),
      );

      final data = json.decode(response.body);
      
      if (response.statusCode == 201 || response.statusCode == 200) {
        return {
          'success': true,
          'message': data['message'] ?? 'Registro completado correctamente',
          'requires_verification': data['requires_verification'] ?? false,
          'requires_approval': data['requires_approval'] ?? false,
        };
      } else {
        return {
          'success': false,
          'error': data['error'] ?? 'Error al registrar',
        };
      }
    } catch (e) {
      print('Registration error: $e');
      return {
        'success': false,
        'error': 'Error de conexión',
      };
    }
  }

  Future<bool> checkAuth() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');

    if (token == null) return false;

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/auth/check/'),
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _currentClient = Client.fromJson(data['client']);
        _token = token;
        
        // Restaurar el gym desde SharedPreferences
        final gymId = prefs.getInt('gym_id');
        final gymName = prefs.getString('gym_name');
        final brandColor = prefs.getString('gym_brand_color');
        if (gymId != null && gymName != null) {
          _currentGym = Gym(
            id: gymId,
            name: gymName,
            city: '',
            address: '',
            brandColor: brandColor ?? '#6366F1',
          );
        }
        
        notifyListeners();
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  Future<Map<String, dynamic>> requestPasswordReset(String email) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/password-reset/request/'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'email': email}),
      );

      final data = json.decode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      } else {
        return {
          'success': false,
          'message': data['error'] ?? 'Error desconocido'
        };
      }
    } catch (e) {
      print('Password reset request error: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  Future<Map<String, dynamic>> confirmPasswordReset(
      String email, String code, String newPassword) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/password-reset/confirm/'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'email': email,
          'code': code,
          'new_password': newPassword,
        }),
      );

      final data = json.decode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      } else {
        return {
          'success': false,
          'message': data['error'] ?? 'Error desconocido'
        };
      }
    } catch (e) {
      print('Password reset confirm error: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // ===========================
  // SCHEDULE & BOOKINGS
  // ===========================

  Future<List<dynamic>> getSchedule(
      {String? startDate, String? endDate, int? activityId}) async {
    if (_token == null) return [];

    try {
      var url = '$baseUrl/schedule/';
      final params = <String, String>{};

      if (startDate != null) params['start_date'] = startDate;
      if (endDate != null) params['end_date'] = endDate;
      if (activityId != null) params['activity_id'] = activityId.toString();

      if (params.isNotEmpty) {
        url += '?${params.entries.map((e) => '${e.key}=${e.value}').join('&')}';
      }

      final response = await http.get(
        Uri.parse(url),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
      }
      return [];
    } catch (e) {
      print('Error getting schedule: $e');
      return [];
    }
  }

  Future<List<dynamic>> getActivities() async {
    if (_token == null) return [];

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/activities/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
      }
      return [];
    } catch (e) {
      print('Error getting activities: $e');
      return [];
    }
  }

  Future<Map<String, dynamic>> bookSession(int sessionId) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/bookings/book/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'session_id': sessionId}),
      );

      final data = json.decode(response.body);

      if (response.statusCode == 201) {
        return {
          'success': true,
          'message': data['message'],
          'booking': data['booking']
        };
      } else {
        return {
          'success': false,
          'message': data['error'] ?? 'Error al reservar'
        };
      }
    } catch (e) {
      print('Error booking session: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  Future<Map<String, dynamic>> cancelBooking(int bookingId) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }

    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/bookings/$bookingId/cancel/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      final data = json.decode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      } else {
        return {
          'success': false,
          'message': data['error'] ?? 'Error al cancelar'
        };
      }
    } catch (e) {
      print('Error canceling booking: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  Future<List<dynamic>> getMyBookings({String status = 'upcoming'}) async {
    if (_token == null) return [];

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/bookings/my-bookings/?status=$status'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
      }
      return [];
    } catch (e) {
      print('Error getting bookings: $e');
      return [];
    }
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    _token = null;
    _currentClient = null;
  }

  // ===========================
  // PROFILE
  // ===========================

  Future<Map<String, dynamic>> getProfile() async {
    if (_token == null) return {};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/profile/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return {};
    } catch (e) {
      print('Error getting profile: $e');
      return {};
    }
  }

  Future<Map<String, dynamic>> updateProfile(Map<String, dynamic> data) async {
    if (_token == null) return {'success': false};

    try {
      final response = await http.put(
        Uri.parse('$baseUrl/profile/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode(data),
      );

      if (response.statusCode == 200) {
        return {'success': true, 'profile': json.decode(response.body)};
      }
      return {'success': false};
    } catch (e) {
      print('Error updating profile: $e');
      return {'success': false};
    }
  }

  Future<Map<String, dynamic>> changePassword(
      String oldPassword, String newPassword) async {
    if (_token == null) return {'success': false};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/profile/change-password/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json
            .encode({'old_password': oldPassword, 'new_password': newPassword}),
      );

      final data = json.decode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }
      return {'success': false, 'message': data['error']};
    } catch (e) {
      print('Error changing password: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Payment Methods
  Future<List<Map<String, dynamic>>> getPaymentMethods() async {
    if (_token == null) return [];

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/profile/payment-methods/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.cast<Map<String, dynamic>>();
      }
      return [];
    } catch (e) {
      print('Error getting payment methods: $e');
      return [];
    }
  }

  Future<Map<String, dynamic>> addPaymentMethod({
    required String cardNumber,
    required int expiryMonth,
    required int expiryYear,
    required String cvv,
    required String cardholderName,
  }) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/profile/payment-methods/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({
          'card_number': cardNumber,
          'expiry_month': expiryMonth,
          'expiry_year': expiryYear,
          'cvv': cvv,
          'cardholder_name': cardholderName,
        }),
      );

      final data = json.decode(response.body);

      if (response.statusCode == 201 || response.statusCode == 200) {
        return {'success': true, 'data': data};
      }
      return {'success': false, 'message': data['error'] ?? 'Error al añadir tarjeta'};
    } catch (e) {
      print('Error adding payment method: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  Future<Map<String, dynamic>> setDefaultPaymentMethod(int methodId) async {
    if (_token == null) return {'success': false};

    try {
      final response = await http.patch(
        Uri.parse('$baseUrl/profile/payment-methods/$methodId/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'is_default': true}),
      );

      if (response.statusCode == 200) {
        return {'success': true};
      }
      return {'success': false};
    } catch (e) {
      print('Error setting default payment method: $e');
      return {'success': false};
    }
  }

  Future<Map<String, dynamic>> deletePaymentMethod(int methodId) async {
    if (_token == null) return {'success': false};

    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/profile/payment-methods/$methodId/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 204 || response.statusCode == 200) {
        return {'success': true};
      }
      return {'success': false};
    } catch (e) {
      print('Error deleting payment method: $e');
      return {'success': false};
    }
  }

  Future<Map<String, dynamic>> toggleNotifications(bool enabled) async {
    if (_token == null) return {'success': false};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/profile/notifications/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'notifications_enabled': enabled}),
      );

      if (response.statusCode == 200) {
        return {'success': true};
      }
      return {'success': false};
    } catch (e) {
      print('Error toggling notifications: $e');
      return {'success': false};
    }
  }

  Future<Map<String, dynamic>> getMembership() async {
    if (_token == null) return {};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/profile/membership/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return {};
    } catch (e) {
      print('Error getting membership: $e');
      return {};
    }
  }

  // ===========================
  // NOTIFICATIONS
  // ===========================

  Future<List<dynamic>> getPopupNotifications() async {
    if (_token == null) return [];

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/notifications/popup/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
      }
      return [];
    } catch (e) {
      print('Error getting popup notifications: $e');
      return [];
    }
  }

  Future<Map<String, dynamic>> dismissPopup(int noteId) async {
    if (_token == null) return {'success': false};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/notifications/popup/$noteId/dismiss/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        return {'success': true};
      }
      return {'success': false};
    } catch (e) {
      print('Error dismissing popup: $e');
      return {'success': false};
    }
  }

  // ===========================
  // EXERCISE DETAIL
  // ===========================

  Future<Map<String, dynamic>> getExerciseDetail(int exerciseId) async {
    if (_token == null) return {};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/exercises/$exerciseId/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return {};
    } catch (e) {
      print('Error getting exercise detail: $e');
      return {};
    }
  }

  // ===========================
  // BILLING
  // ===========================

  // Billing History
  Future<List<dynamic>> getBillingHistory() async {
    if (_token == null) return [];

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/billing/history/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // API returns {'count': X, 'invoices': [...]}
        if (data is Map && data.containsKey('invoices')) {
          return data['invoices'] as List<dynamic>;
        }
        return [];
      }
      return [];
    } catch (e) {
      print('Error getting billing history: $e');
      return [];
    }
  }

  // Chat Messages
  Future<Map<String, dynamic>> getChatMessages({int page = 1}) async {
    if (_token == null) return {'messages': [], 'has_next': false};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/chat/messages/?page=$page'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return {'messages': [], 'has_next': false};
    } catch (e) {
      print('Error getting chat messages: $e');
      return {'messages': [], 'has_next': false};
    }
  }

  // Mark Chat as Read
  Future<void> markChatRead() async {
    if (_token == null) return;

    try {
      await http.post(
        Uri.parse('$baseUrl/chat/read/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );
    } catch (e) {
      print('Error marking chat as read: $e');
    }
  }

  // Send Chat Message
  Future<Map<String, dynamic>> sendChatMessage(String text) async {
    if (_token == null) return {'success': false};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/chat/messages/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'message': text}),
      );

      if (response.statusCode == 201) {
        return {'success': true, 'message': json.decode(response.body)};
      }
      return {'success': false};
    } catch (e) {
      print('Error sending chat message: $e');
      return {'success': false};
    }
  }

  // Generate Check-in QR
  Future<Map<String, dynamic>> generateCheckinQR() async {
    if (_token == null) return {'success': false, 'error': 'No autenticado'};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/checkin/generate/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'error': 'Error al generar QR'};
    } catch (e) {
      print('Error generating QR: $e');
      return {'success': false, 'error': 'Error de conexión'};
    }
  }

  // Get Check-in History
  Future<Map<String, dynamic>> getCheckinHistory({int limit = 20}) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/checkin/history/?limit=$limit'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, 'visits': data['history'] ?? []};
      }
      return {'success': false, 'message': 'Error al cargar historial'};
    } catch (e) {
      print('Error getting checkin history: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Refresh Check-in QR
  Future<Map<String, dynamic>> refreshCheckinQR() async {
    if (_token == null) return {'success': false};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/checkin/refresh/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false};
    } catch (e) {
      print('Error refreshing QR: $e');
      return {'success': false};
    }
  }

  /// QR Check-in: Escanea el QR de una sesión para registrar asistencia
  Future<Map<String, dynamic>> qrCheckin(String qrContent) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/checkin/qr/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'qr_content': qrContent}),
      );

      final data = json.decode(response.body);
      
      if (response.statusCode == 200) {
        return {
          'success': true,
          'message': data['message'] ?? '¡Check-in realizado!',
          'session_name': data['session_name'],
          'session_time': data['session_time'],
          'room': data['room'],
        };
      }
      return {
        'success': false,
        'message': data['error'] ?? 'Error al procesar el check-in',
      };
    } catch (e) {
      print('Error QR checkin: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Get Document Detail
  Future<Map<String, dynamic>> getDocumentDetail(int documentId) async {
    if (_token == null) return {};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/documents/$documentId/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return {};
    } catch (e) {
      print('Error getting document detail: $e');
      return {};
    }
  }

  // Sign Document
  Future<Map<String, dynamic>> signDocument(
      int documentId, String base64signature) async {
    if (_token == null) return {'success': false};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/documents/$documentId/sign/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'signature': base64signature}),
      );

      if (response.statusCode == 200) {
        return {'success': true, 'document': json.decode(response.body)};
      }
      return {'success': false};
    } catch (e) {
      print('Error signing document: $e');
      return {'success': false};
    }
  }

  // Get Documents List
  Future<Map<String, dynamic>> getDocuments() async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/documents/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, 'documents': data is List ? data : []};
      }
      return {'success': false, 'message': 'Error al cargar documentos'};
    } catch (e) {
      print('Error getting documents: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Get Class History
  Future<List<dynamic>> getClassHistory() async {
    if (_token == null) return [];

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/history/classes/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // API returns {'classes': [...]}
        if (data is Map && data.containsKey('classes')) {
          return data['classes'] as List<dynamic>;
        }
        return [];
      }
      return [];
    } catch (e) {
      print('Error getting class history: $e');
      return [];
    }
  }

  // Submit Class Review
  Future<Map<String, dynamic>> submitClassReview(
      {required int sessionId,
      required int instructorRating,
      required int classRating,
      required String comment}) async {
    if (_token == null) return {'success': false};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/history/review/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({
          'session_id': sessionId,
          'instructor_rating': instructorRating,
          'class_rating': classRating,
          'comment': comment
        }),
      );

      if (response.statusCode == 201) {
        return {'success': true};
      }
      return {'success': false};
    } catch (e) {
      print('Error submitting review: $e');
      return {'success': false};
    }
  }

  // Get Routine Detail
  Future<Map<String, dynamic>> getRoutineDetail(int routineId) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/routines/$routineId/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, 'routine': data};
      }
      return {'success': false, 'message': 'Error al cargar rutina'};
    } catch (e) {
      print('Error getting routine detail: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Get Routines List
  Future<Map<String, dynamic>> getRoutines() async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/routines/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // Backend returns {'count': X, 'routines': [...]}
        final routines = data is Map ? (data['routines'] ?? []) : (data is List ? data : []);
        return {'success': true, 'routines': routines};
      }
      return {'success': false, 'message': 'Error al cargar rutinas'};
    } catch (e) {
      print('Error getting routines: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // ===========================
  // WORKOUT TRACKING
  // ===========================

  // Start a new workout from a routine day
  Future<Map<String, dynamic>> startWorkout(int dayId) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/workout/start/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'day_id': dayId}),
      );

      final data = json.decode(response.body);
      if (response.statusCode == 200 || response.statusCode == 201) {
        return {'success': true, ...data};
      }
      return {'success': false, 'message': data['error'] ?? 'Error al iniciar entrenamiento'};
    } catch (e) {
      print('Error starting workout: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Check if there's an active workout
  Future<Map<String, dynamic>> getActiveWorkout() async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/workout/active/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error al verificar entrenamiento activo'};
    } catch (e) {
      print('Error checking active workout: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Get workout status and exercises
  Future<Map<String, dynamic>> getWorkoutStatus(int workoutId) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/workout/$workoutId/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error al cargar entrenamiento'};
    } catch (e) {
      print('Error getting workout status: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Log a set for an exercise
  Future<Map<String, dynamic>> logSet(int workoutId, int exerciseLogId, int reps, double weight) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/workout/$workoutId/log/$exerciseLogId/set/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'reps': reps, 'weight': weight}),
      );

      final data = json.decode(response.body);
      if (response.statusCode == 200 || response.statusCode == 201) {
        return {'success': true, ...data};
      }
      return {'success': false, 'message': data['error'] ?? 'Error al registrar serie'};
    } catch (e) {
      print('Error logging set: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Mark exercise as completed
  Future<Map<String, dynamic>> completeExercise(int workoutId, int exerciseLogId) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/workout/$workoutId/log/$exerciseLogId/complete/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      final data = json.decode(response.body);
      if (response.statusCode == 200) {
        return {'success': true, ...data};
      }
      return {'success': false, 'message': data['error'] ?? 'Error al completar ejercicio'};
    } catch (e) {
      print('Error completing exercise: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Finish workout
  Future<Map<String, dynamic>> finishWorkout(int workoutId, {int? difficultyRating, String? notes}) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final body = <String, dynamic>{};
      if (difficultyRating != null) body['difficulty_rating'] = difficultyRating;
      if (notes != null) body['notes'] = notes;

      final response = await http.post(
        Uri.parse('$baseUrl/workout/$workoutId/finish/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode(body),
      );

      final data = json.decode(response.body);
      if (response.statusCode == 200) {
        return {'success': true, ...data};
      }
      return {'success': false, 'message': data['error'] ?? 'Error al finalizar entrenamiento'};
    } catch (e) {
      print('Error finishing workout: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Get workout history
  Future<Map<String, dynamic>> getWorkoutHistory({int limit = 20, int offset = 0}) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/workout/history/?limit=$limit&offset=$offset'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error al cargar historial'};
    } catch (e) {
      print('Error getting workout history: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // ===========================
  // QUICK CHECK-IN
  // ===========================

  // Get today's booked sessions for quick check-in
  Future<Map<String, dynamic>> getTodaysSessions() async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/checkin/todays-sessions/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error al cargar clases'};
    } catch (e) {
      print('Error getting today sessions: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Quick check-in to a booked session
  Future<Map<String, dynamic>> quickCheckin(int sessionId) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/checkin/quick/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'session_id': sessionId}),
      );

      final data = json.decode(response.body);
      if (response.statusCode == 200) {
        return {'success': true, ...data};
      }
      return {'success': false, 'message': data['error'] ?? 'Error en check-in'};
    } catch (e) {
      print('Error quick checkin: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Get Shop Items
  Future<Map<String, dynamic>> getShop() async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/shop/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': true,
          'products': data['products'] ?? [],
          'services': data['services'] ?? [],
          'membership_plans': data['membership_plans'] ?? []
        };
      }
      return {'success': false, 'message': 'Error al cargar tienda'};
    } catch (e) {
      print('Error getting shop items: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Request Shop Item Info
  Future<Map<String, dynamic>> requestInfo(String itemType, int itemId) async {
    if (_token == null) return {'success': false};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/shop/request-info/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'item_type': itemType, 'item_id': itemId}),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        return {'success': true};
      }
      return {'success': false};
    } catch (e) {
      print('Error requesting info: $e');
      return {'success': false};
    }
  }

  // ===== GAMIFICATION =====
  
  // Get Gamification Status (progress, level, XP, rank)
  Future<Map<String, dynamic>> getGamificationStatus() async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/gamification/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error al cargar gamificación'};
    } catch (e) {
      print('Error getting gamification status: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Get Leaderboard
  Future<Map<String, dynamic>> getLeaderboard({String period = 'weekly'}) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/gamification/leaderboard/?period=$period'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, 'leaderboard': data is List ? data : []};
      }
      return {'success': false, 'message': 'Error al cargar ranking'};
    } catch (e) {
      print('Error getting leaderboard: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Get Achievements
  Future<Map<String, dynamic>> getAchievements() async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/gamification/achievements/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': true,
          'unlocked': data['unlocked'] ?? [],
          'locked': data['locked'] ?? []
        };
      }
      return {'success': false, 'message': 'Error al cargar logros'};
    } catch (e) {
      print('Error getting achievements: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Get Challenges
  Future<Map<String, dynamic>> getChallenges() async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/gamification/challenges/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': true,
          'challenges': data is List ? data : []
        };
      }
      return {'success': false, 'message': 'Error al cargar retos'};
    } catch (e) {
      print('Error getting challenges: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Join Challenge
  Future<Map<String, dynamic>> joinChallenge(int challengeId) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/gamification/challenges/$challengeId/join/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = json.decode(response.body);
        return {'success': true, 'message': data['message'] ?? 'Te has unido al reto'};
      }
      final data = json.decode(response.body);
      return {'success': false, 'message': data['error'] ?? 'Error al unirse al reto'};
    } catch (e) {
      print('Error joining challenge: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // Get XP History
  Future<Map<String, dynamic>> getXPHistory({int limit = 20}) async {
    if (_token == null) return {'success': false, 'message': 'No autenticado'};

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/gamification/xp-history/?limit=$limit'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': true,
          'transactions': data is List ? data : []
        };
      }
      return {'success': false, 'message': 'Error al cargar historial XP'};
    } catch (e) {
      print('Error getting XP history: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  // ===========================
  // ADVERTISEMENTS
  // ===========================

  Future<List<Advertisement>> getAdvertisements({
    String screen = 'ALL',
    String? position,
  }) async {
    try {
      var url = '${baseUrl.replaceAll('/api', '')}/marketing/api/advertisements/active/';
      final params = <String, String>{};

      params['screen'] = screen;
      if (position != null) params['position'] = position;

      if (params.isNotEmpty) {
        url += '?${params.entries.map((e) => '${e.key}=${e.value}').join('&')}';
      }

      print('📢 Fetching advertisements: $url');

      final response = await http.get(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        print('✅ Found ${data.length} advertisements for screen: $screen');
        return data.map((json) => Advertisement.fromJson(json)).toList();
      }
      print('❌ Failed to load advertisements: ${response.statusCode}');
      return [];
    } catch (e) {
      print('💥 Error loading advertisements: $e');
      return [];
    }
  }

  Future<void> trackAdvertisementImpression(int adId) async {
    try {
      final url = '${baseUrl.replaceAll('/api', '')}/marketing/api/advertisements/$adId/impression/';
      await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );
    } catch (e) {
      print('Error tracking impression: $e');
    }
  }

  Future<void> trackAdvertisementClick(int adId) async {
    try {
      final url = '${baseUrl.replaceAll('/api', '')}/marketing/api/advertisements/$adId/click/';
      await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );
    } catch (e) {
      print('Error tracking click: $e');
    }
  }
}
