import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';
import '../models/schedule_models.dart';
import 'package:intl/intl.dart';

class MyBookingsScreen extends StatefulWidget {
  const MyBookingsScreen({super.key});

  @override
  State<MyBookingsScreen> createState() => _MyBookingsScreenState();
}

class _MyBookingsScreenState extends State<MyBookingsScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<Booking> _upcomingBookings = [];
  List<Booking> _pastBookings = [];
  bool _isLoadingUpcoming = true;
  bool _isLoadingPast = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadUpcomingBookings();
    _loadPastBookings();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadUpcomingBookings() async {
    setState(() => _isLoadingUpcoming = true);
    
    final api = Provider.of<ApiService>(context, listen: false);
    final data = await api.getMyBookings(status: 'upcoming');
    final bookings = data.map((json) => Booking.fromJson(json)).toList();
    
    if (mounted) {
      setState(() {
        _upcomingBookings = bookings;
        _isLoadingUpcoming = false;
      });
    }
  }

  Future<void> _loadPastBookings() async {
    setState(() => _isLoadingPast = true);
    
    final api = Provider.of<ApiService>(context, listen: false);
    final data = await api.getMyBookings(status: 'past');
    final bookings = data.map((json) => Booking.fromJson(json)).toList();
    
    if (mounted) {
      setState(() {
        _pastBookings = bookings;
        _isLoadingPast = false;
      });
    }
  }

  Future<void> _cancelBooking(Booking booking) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancelar Reserva'),
        content: Text('¿Estás seguro de que quieres cancelar tu reserva para ${booking.activityName}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('No'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sí, cancelar', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    // Show loading
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );

    final api = Provider.of<ApiService>(context, listen: false);
    final result = await api.cancelBooking(booking.id);

    if (mounted) {
      Navigator.pop(context); // Close loading

      if (result['success']) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: Colors.green,
          ),
        );
        _loadUpcomingBookings(); // Refresh
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Mis Clases'),
        backgroundColor: const Color(0xFF0F172A),
        foregroundColor: Colors.white,
        elevation: 0,
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white70,
          tabs: const [
            Tab(text: 'Próximas'),
            Tab(text: 'Pasadas'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildUpcomingTab(),
          _buildPastTab(),
        ],
      ),
    );
  }

  Widget _buildUpcomingTab() {
    if (_isLoadingUpcoming) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_upcomingBookings.isEmpty) {
      return _buildEmptyState(
        icon: Icons.bookmark_outline,
        title: 'No tienes clases reservadas',
        subtitle: 'Ve al horario y reserva tu próxima clase',
      );
    }

    return RefreshIndicator(
      onRefresh: _loadUpcomingBookings,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _upcomingBookings.length,
        itemBuilder: (context, index) {
          final booking = _upcomingBookings[index];
          return _buildBookingCard(booking, isUpcoming: true);
        },
      ),
    );
  }

  Widget _buildPastTab() {
    if (_isLoadingPast) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_pastBookings.isEmpty) {
      return _buildEmptyState(
        icon: Icons.history,
        title: 'Sin historial',
        subtitle: 'Tus clases pasadas aparecerán aquí',
      );
    }

    return RefreshIndicator(
      onRefresh: _loadPastBookings,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _pastBookings.length,
        itemBuilder: (context, index) {
          final booking = _pastBookings[index];
          return _buildBookingCard(booking, isUpcoming: false);
        },
      ),
    );
  }

  Widget _buildBookingCard(Booking booking, {required bool isUpcoming}) {
    final session = booking.session;
    final color = session.activity.color.isNotEmpty
        ? Color(int.parse(session.activity.color.replaceFirst('#', '0xFF')))
        : const Color(0xFF0F172A);

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey[200]!),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                // Date badge
                Container(
                  width: 60,
                  height: 60,
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        DateFormat('d').format(session.startDatetime),
                        style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          color: color,
                        ),
                      ),
                      Text(
                        DateFormat('MMM').format(session.startDatetime).toUpperCase(),
                        style: TextStyle(
                          fontSize: 12,
                          color: color,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),

                // Info
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        session.activity.name,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        session.timeRange,
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey[600],
                        ),
                      ),
                      if (session.instructor != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          'Con ${session.instructor!.fullName}',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[500],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),

                // Status badge
                if (!isUpcoming)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: booking.attended ? Colors.green[50] : Colors.grey[100],
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          booking.attended ? Icons.check_circle : Icons.cancel,
                          size: 16,
                          color: booking.attended ? Colors.green : Colors.grey,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          booking.attended ? 'Asistida' : 'No asistida',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: booking.attended ? Colors.green : Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),

          // Cancel button for upcoming
          if (isUpcoming && booking.isConfirmed)
            Container(
              decoration: BoxDecoration(
                border: Border(top: BorderSide(color: Colors.grey[200]!)),
              ),
              child: TextButton(
                onPressed: () => _cancelBooking(booking),
                style: TextButton.styleFrom(
                  foregroundColor: Colors.red,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: const RoundedRectangleBorder(
                    borderRadius: BorderRadius.only(
                      bottomLeft: Radius.circular(16),
                      bottomRight: Radius.circular(16),
                    ),
                  ),
                ),
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.cancel_outlined, size: 18),
                    SizedBox(width: 8),
                    Text(
                      'Cancelar Reserva',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildEmptyState({
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            icon,
            size: 80,
            color: Colors.grey[300],
          ),
          const SizedBox(height: 16),
          Text(
            title,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[500],
            ),
          ),
        ],
      ),
    );
  }
}
