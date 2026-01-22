import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/models.dart';

import 'package:flutter/foundation.dart'; // for kIsWeb

class ApiService {
  // Use localhost for Web, 10.0.2.2 for Android Emulator
  static String get baseUrl {
    if (kIsWeb) return 'http://127.0.0.1:8000/api';
    return 'http://10.0.2.2:8000/api';
  }
  
  String? _token;
  Client? _currentClient;

  Client? get currentClient => _currentClient;

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

  Future<bool> login(String email, String password, {int? gymId}) async {
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
        
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('auth_token', _token!);
        return true;
      }
      return false;
    } catch (e) {
      print('Login error: $e');
      return false;
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
        return {'success': false, 'message': data['error'] ?? 'Error desconocido'};
      }
    } catch (e) {
      print('Password reset request error: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }

  Future<Map<String, dynamic>> confirmPasswordReset(String email, String code, String newPassword) async {
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
        return {'success': false, 'message': data['error'] ?? 'Error desconocido'};
      }
    } catch (e) {
      print('Password reset confirm error: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  // ===========================
  // SCHEDULE & BOOKINGS
  // ===========================
  
  Future<List<dynamic>> getSchedule({String? startDate, String? endDate, int? activityId}) async {
    if (_token == null) return [];
    
    try {
      var url = '$baseUrl/schedule/';
      final params = <String, String>{};
      
      if (startDate != null) params['start_date'] = startDate;
      if (endDate != null) params['end_date'] = endDate;
      if (activityId != null) params['activity_id'] = activityId.toString();
      
      if (params.isNotEmpty) {
        url += '?' + params.entries.map((e) => '${e.key}=${e.value}').join('&');
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
        return {'success': true, 'message': data['message'], 'booking': data['booking']};
      } else {
        return {'success': false, 'message': data['error'] ?? 'Error al reservar'};
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
        return {'success': false, 'message': data['error'] ?? 'Error al cancelar'};
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
  // ROUTINES
  // ===========================
  
  /// Get list of routines assigned to the client
  Future<Map<String, dynamic>> getRoutines() async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado', 'routines': []};
    }
    
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
        return {
          'success': true,
          'count': data['count'],
          'routines': data['routines'],
        };
      }
      return {'success': false, 'message': 'Error obteniendo rutinas', 'routines': []};
    } catch (e) {
      print('Error getting routines: $e');
      return {'success': false, 'message': 'Error de conexión', 'routines': []};
    }
  }
  
  /// Get detailed routine with all days and exercises
  Future<Map<String, dynamic>> getRoutineDetail(int routineId) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
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
      } else if (response.statusCode == 404) {
        return {'success': false, 'message': 'Rutina no encontrada'};
      }
      return {'success': false, 'message': 'Error obteniendo rutina'};
    } catch (e) {
      print('Error getting routine detail: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  /// Get detailed info for a single exercise
  Future<Map<String, dynamic>> getExerciseDetail(int exerciseId) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/exercises/$exerciseId/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, 'exercise': data};
      } else if (response.statusCode == 404) {
        return {'success': false, 'message': 'Ejercicio no encontrado'};
      }
      return {'success': false, 'message': 'Error obteniendo ejercicio'};
    } catch (e) {
      print('Error getting exercise detail: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  // ===========================
  // CHECK-IN QR
  // ===========================
  
  /// Generate QR token for check-in
  Future<Map<String, dynamic>> generateCheckinQR() async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/checkin/generate/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error generando QR'};
    } catch (e) {
      print('Error generating QR token: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  /// Refresh QR token
  Future<Map<String, dynamic>> refreshCheckinQR() async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
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
      return {'success': false, 'message': 'Error refrescando QR'};
    } catch (e) {
      print('Error refreshing QR token: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  /// Get check-in history
  Future<Map<String, dynamic>> getCheckinHistory({int limit = 10}) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado', 'visits': []};
    }
    
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
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error obteniendo historial', 'visits': []};
    } catch (e) {
      print('Error getting checkin history: $e');
      return {'success': false, 'message': 'Error de conexión', 'visits': []};
    }
  }
  
  // ===========================
  // PROFILE
  // ===========================
  
  /// Get client profile
  Future<Map<String, dynamic>> getProfile() async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/profile/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, 'profile': data};
      }
      return {'success': false, 'message': 'Error obteniendo perfil'};
    } catch (e) {
      print('Error getting profile: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  /// Update client profile
  Future<Map<String, dynamic>> updateProfile({
    String? firstName,
    String? lastName,
    String? email,
    String? phone,
  }) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final Map<String, dynamic> body = {};
      if (firstName != null) body['first_name'] = firstName;
      if (lastName != null) body['last_name'] = lastName;
      if (email != null) body['email'] = email;
      if (phone != null) body['phone'] = phone;
      
      final response = await http.put(
        Uri.parse('$baseUrl/profile/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode(body),
      );

      final data = json.decode(response.body);
      
      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message'], 'client': data['client']};
      }
      return {'success': false, 'message': data['error'] ?? 'Error actualizando perfil'};
    } catch (e) {
      print('Error updating profile: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  /// Change password
  Future<Map<String, dynamic>> changePassword(String currentPassword, String newPassword) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/profile/change-password/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({
          'current_password': currentPassword,
          'new_password': newPassword,
        }),
      );

      final data = json.decode(response.body);
      
      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }
      return {'success': false, 'message': data['error'] ?? 'Error cambiando contraseña'};
    } catch (e) {
      print('Error changing password: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  /// Toggle email notifications
  Future<Map<String, dynamic>> toggleNotifications(bool enabled) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/profile/notifications/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'enabled': enabled}),
      );

      final data = json.decode(response.body);
      
      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }
      return {'success': false, 'message': data['error'] ?? 'Error actualizando notificaciones'};
    } catch (e) {
      print('Error toggling notifications: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  /// Get membership details
  Future<Map<String, dynamic>> getMembershipDetails() async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/profile/membership/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error obteniendo membresía'};
    } catch (e) {
      print('Error getting membership: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  // ===========================
  // SHOP
  // ===========================
  
  /// Get shop items (products, services, plans)
  Future<Map<String, dynamic>> getShop() async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
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
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error cargando tienda'};
    } catch (e) {
      print('Error getting shop: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  /// Request info about an item
  Future<Map<String, dynamic>> requestInfo(String itemType, int itemId, {String message = ''}) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/shop/request-info/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({
          'item_type': itemType, // 'product', 'service', 'plan'
          'item_id': itemId,
          'message': message,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error enviando solicitud'};
    } catch (e) {
      print('Error requesting info: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  // ===========================
  // DOCUMENTS
  // ===========================
  
  /// Get documents
  Future<Map<String, dynamic>> getDocuments({String? status}) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      String url = '$baseUrl/documents/';
      if (status != null) {
        url += '?status=$status';
      }
      
      final response = await http.get(
        Uri.parse(url),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error obteniendo documentos'};
    } catch (e) {
      print('Error getting documents: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  /// Get document details
  Future<Map<String, dynamic>> getDocumentDetail(int documentId) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/documents/$documentId/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error obteniendo documento'};
    } catch (e) {
      print('Error getting document detail: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  /// Sign document (base64 image)
  Future<Map<String, dynamic>> signDocument(int documentId, String signatureImageBase64) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/documents/$documentId/sign/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({
          'signature_image': signatureImageBase64,
        }),
      );

      final data = json.decode(response.body);
      
      if (response.statusCode == 200) {
        return {'success': true, ...data};
      }
      return {'success': false, 'message': data['error'] ?? 'Error firmando documento'};
    } catch (e) {
      print('Error signing document: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  // ===========================
  // CHAT
  // ===========================
  
  /// Get chat messages
  Future<Map<String, dynamic>> getChatMessages({int limit = 50, int offset = 0}) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado', 'messages': []};
    }
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/chat/messages/?limit=$limit&offset=$offset'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {'success': true, ...data};
      }
      return {'success': false, 'message': 'Error obteniendo chat', 'messages': []};
    } catch (e) {
      print('Error getting chat: $e');
      return {'success': false, 'message': 'Error de conexión', 'messages': []};
    }
  }
  
  /// Send chat message
  Future<Map<String, dynamic>> sendChatMessage(String message) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/chat/messages/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({'message': message}),
      );

      final data = json.decode(response.body);
      
      if (response.statusCode == 201) {
        return {'success': true, ...data};
      }
      return {'success': false, 'message': data['error'] ?? 'Error enviando mensaje'};
    } catch (e) {
      print('Error sending message: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
  
  /// Mark messages as read
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
      print('Error marking read: $e');
    }
  }
  
  // ===========================
  // NOTIFICATIONS (Popups)
  // ===========================
  
  /// Get active popup notifications
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
        final data = json.decode(response.body);
        return data['popups'] ?? [];
      }
      return [];
    } catch (e) {
      print('Error getting popups: $e');
      return [];
    }
  }
  
  /// Dismiss a popup
  Future<void> dismissPopup(int noteId) async {
    if (_token == null) return;
    
    try {
      await http.post(
        Uri.parse('$baseUrl/notifications/popup/$noteId/dismiss/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );
    } catch (e) {
      print('Error dismissing popup: $e');
    }
  }
  
  // ===========================
  // BILLING
  // ===========================
  
  /// Get billing history (invoices)
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
        return data['invoices'] ?? [];
      }
      return [];
    } catch (e) {
      print('Error getting billing history: $e');
      return [];
    }
  }
  
  // ===========================
  // HISTORY & REVIEWS
  // ===========================
  
  /// Get past classes
  Future<List<dynamic>> getClassHistory({int limit = 20, int offset = 0}) async {
    if (_token == null) return [];
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/history/classes/?limit=$limit&offset=$offset'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['classes'] ?? [];
      }
      return [];
    } catch (e) {
      print('Error getting class history: $e');
      return [];
    }
  }
  
  /// Submit class review
  Future<Map<String, dynamic>> submitClassReview({
    required int sessionId,
    required int instructorRating,
    required int classRating,
    String comment = '',
  }) async {
    if (_token == null) {
      return {'success': false, 'message': 'No autenticado'};
    }
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/history/reviews/'),
        headers: {
          'Authorization': 'Token $_token',
          'Content-Type': 'application/json'
        },
        body: json.encode({
          'session_id': sessionId,
          'instructor_rating': instructorRating,
          'class_rating': classRating,
          'comment': comment,
        }),
      );

      final data = json.decode(response.body);
      
      if (response.statusCode == 200) {
        return {'success': true, ...data};
      }
      return {'success': false, 'message': data['error'] ?? 'Error enviando valoración'};
    } catch (e) {
      print('Error submitting review: $e');
      return {'success': false, 'message': 'Error de conexión'};
    }
  }
}






