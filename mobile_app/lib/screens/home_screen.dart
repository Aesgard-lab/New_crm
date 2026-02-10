import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';
import 'shop_screen.dart';
import 'documents_screen.dart';
import 'workout_tracking_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Map<String, dynamic>? _activeWorkout;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkPopups();
      _checkActiveWorkout();
    });
  }

  Future<void> _checkActiveWorkout() async {
    final api = Provider.of<ApiService>(context, listen: false);
    try {
      final workout = await api.getActiveWorkout();
      if (mounted) {
        setState(() {
          _activeWorkout = workout;
        });
      }
    } catch (e) {
      // Error silencioso - el widget manejará el estado null
    }
  }

  Future<void> _checkPopups() async {
    final api = Provider.of<ApiService>(context, listen: false);
    final popups = await api.getPopupNotifications();
    
    if (popups.isNotEmpty && mounted) {
      for (final note in popups) {
        await _showPopupDialog(note);
      }
    }
  }

  Future<void> _showPopupDialog(Map<String, dynamic> note) async {
    final noteId = note['id'];
    final type = note['type'];
    final text = note['text'];
    final author = note['author'];
    final api = Provider.of<ApiService>(context, listen: false);
    
    Color headerColor = api.brandColor;
    IconData icon = Icons.info_outline;
    
    if (type == 'WARNING') {
      headerColor = Colors.orange;
      icon = Icons.warning_amber_rounded;
    } else if (type == 'DANGER') {
      headerColor = Colors.red;
      icon = Icons.error_outline;
    } else if (type == 'VIP') {
      headerColor = Colors.amber;
      icon = Icons.star;
    }

    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Icon(icon, color: headerColor),
            const SizedBox(width: 8),
            Text('Notificación', style: TextStyle(color: headerColor)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(text ?? '', style: const TextStyle(fontSize: 16)),
            if (author != null) ...[
              const SizedBox(height: 12),
              Text('De: $author', style: TextStyle(fontSize: 12, color: Colors.grey[600], fontStyle: FontStyle.italic)),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              final api = Provider.of<ApiService>(context, listen: false);
              api.dismissPopup(noteId);
              Navigator.of(ctx).pop();
            },
            child: const Text('Entendido'),
          ),
        ],
      ),
    );
  }

  Widget _buildActiveWorkoutCard() {
    final routineName = _activeWorkout?['routine_name'] ?? 'Entrenamiento';
    final dayName = _activeWorkout?['day_name'] ?? '';
    final workoutId = _activeWorkout?['workout_id'];
    
    return GestureDetector(
      onTap: () {
        if (workoutId != null) {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => WorkoutTrackingScreen(
                workoutId: workoutId,
                routineName: routineName,
                dayName: dayName,
              ),
            ),
          ).then((_) => _checkActiveWorkout());
        }
      },
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF10B981), Color(0xFF059669)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF10B981).withOpacity(0.3),
              blurRadius: 12,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(
                Icons.play_arrow_rounded,
                color: Colors.white,
                size: 32,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Entrenamiento en curso',
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    dayName.isNotEmpty ? '$routineName - $dayName' : routineName,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.chevron_right,
              color: Colors.white,
              size: 28,
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final api = Provider.of<ApiService>(context);
    final client = api.currentClient;
    final stats = client?.stats;
    final bookings = client?.nextBookings;

    return Scaffold(

      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            children: [
              // Header
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [api.brandColor, api.brandColorDark],
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    CircleAvatar(
                      radius: 36,
                      backgroundColor: Colors.white24,
                      backgroundImage: (client?.photo != null && client!.photo.isNotEmpty)
                          ? NetworkImage(client.photo)
                          : null,
                      child: (client?.photo == null || client!.photo.isEmpty)
                          ? Text(
                              client?.firstName.substring(0, 1) ?? 'C',
                              style: const TextStyle(fontSize: 28, color: Colors.white),
                            )
                          : null,
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Hola, ${client?.firstName}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 24,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(
                            client?.gymName ?? '',
                            style: const TextStyle(color: Colors.white70),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              // Content
              Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // QR Access Code
                    if (client?.accessCode != null && client!.accessCode.isNotEmpty)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(24),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.05),
                              blurRadius: 20,
                              offset: const Offset(0, 10),
                            ),
                          ],
                        ),
                        child: Column(
                          children: [
                            const Text(
                              'Tu Código de Acceso',
                              style: TextStyle(
                                color: Colors.grey,
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              client.accessCode,
                              style: const TextStyle(
                                fontSize: 32,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 4,
                                color: Color(0xFF0F172A),
                              ),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'Usa este código en la entrada',
                              style: TextStyle(fontSize: 12, color: Colors.grey),
                            ),
                          ],
                        ),
                      ),
                    
                    const SizedBox(height: 24),

                    // Stats Grid
                    Row(
                      children: [
                        Expanded(
                          child: _StatCard(
                            icon: Icons.calendar_month,
                            label: 'Visitas Mes',
                            value: stats?['monthly_visits']?.toString() ?? '0',
                            color: Colors.blue,
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: _StatCard(
                            icon: Icons.local_fire_department,
                            label: 'Racha',
                            value: '${stats?['current_streak']?.toString() ?? '0'} días',
                            color: Colors.orange,
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 24),
                    
                    // Quick Actions
                    Row(
                      children: [
                        Expanded(
                          child: _QuickActionCard(
                            icon: Icons.shopping_bag_outlined,
                            label: 'Tienda',
                            color: api.brandColor,
                            onTap: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (context) => const ShopScreen(),
                                ),
                              );
                            },
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _QuickActionCard(
                            icon: Icons.description_outlined,
                            label: 'Documentos',
                            color: const Color(0xFF10B981),
                            onTap: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (context) => const DocumentsScreen(),
                                ),
                              );
                            },
                          ),
                        ),
                      ],
                    ),

                    // Active Workout Card
                    if (_activeWorkout != null && _activeWorkout!['has_active_workout'] == true) ...[
                      const SizedBox(height: 24),
                      _buildActiveWorkoutCard(),
                    ],


                    const SizedBox(height: 32),

                    // Next Bookings
                    const Text(
                      'Próximas Clases',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                    const SizedBox(height: 16),

                    if (bookings == null || bookings.isEmpty)
                      Container(
                        padding: const EdgeInsets.all(24),
                        alignment: Alignment.center,
                        child: Text(
                          'No tienes clases reservadas',
                          style: TextStyle(color: Colors.grey[500]),
                        ),
                      )
                    else
                      ...bookings.map((booking) => _BookingCard(booking: booking)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final MaterialColor color;

  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.grey[100]!),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 32),
          const SizedBox(height: 12),
          Text(
            value,
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }
}

class _BookingCard extends StatelessWidget {
  final Map<String, dynamic> booking;

  const _BookingCard({required this.booking});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey[200]!),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A).withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.fitness_center,
              color: Color(0xFF0F172A),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  booking['activity_name'] ?? 'Clase',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    color: Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${booking['date']} - ${booking['time']}',
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: Colors.grey),
        ],
      ),
    );
  }
}

class _QuickActionCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _QuickActionCard({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.03),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color, size: 24),
            ),
            const SizedBox(width: 12),
            Text(
              label,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: Color(0xFF1E293B),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

