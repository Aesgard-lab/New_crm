import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';
import '../models/schedule_models.dart';
import '../widgets/promo_section.dart';
import '../widgets/spot_selector.dart';
import 'package:intl/intl.dart';

class ScheduleScreen extends StatefulWidget {
  const ScheduleScreen({super.key});

  @override
  State<ScheduleScreen> createState() => _ScheduleScreenState();
}

class _ScheduleScreenState extends State<ScheduleScreen> {
  List<ActivitySession> _sessions = [];
  List<Activity> _activities = [];
  bool _isLoading = true;
  int? _selectedActivityId;
  final DateTime _selectedDate = DateTime.now();

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    
    final api = Provider.of<ApiService>(context, listen: false);
    
    // Load activities for filter
    final activitiesData = await api.getActivities();
    final activities = activitiesData.map((json) => Activity.fromJson(json)).toList();
    
    // Load schedule
    final startDate = DateFormat('yyyy-MM-dd').format(_selectedDate);
    final endDate = DateFormat('yyyy-MM-dd').format(_selectedDate.add(const Duration(days: 7)));
    
    final scheduleData = await api.getSchedule(
      startDate: startDate,
      endDate: endDate,
      activityId: _selectedActivityId,
    );
    
    final sessions = scheduleData.map((json) => ActivitySession.fromJson(json)).toList();
    
    if (mounted) {
      setState(() {
        _activities = activities;
        _sessions = sessions;
        _isLoading = false;
      });
    }
  }

  Future<void> _bookSession(ActivitySession session) async {
    final api = Provider.of<ApiService>(context, listen: false);
    int? selectedSpot;
    
    // Check if activity allows spot booking
    if (session.allowSpotBooking) {
      // Show loading while fetching spots
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => const Center(child: CircularProgressIndicator()),
      );
      
      final spotsData = await api.getSessionSpots(session.id);
      
      if (mounted) {
        Navigator.pop(context); // Close loading
        
        // Show spot selector if there are spots available
        if (spotsData['allow_spot_booking'] == true && 
            spotsData['has_layout'] == true &&
            (spotsData['spots'] as List?)?.isNotEmpty == true) {
          
          final result = await showDialog<int>(
            context: context,
            builder: (context) => SpotSelectionDialog(
              spotsData: spotsData,
              brandColor: api.brandColor,
            ),
          );
          
          if (result == null) {
            // User cancelled
            return;
          }
          selectedSpot = result;
        }
      } else {
        return;
      }
    }
    
    // Show loading for booking
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );
    
    final result = await api.bookSession(session.id, spotNumber: selectedSpot);
    
    if (mounted) {
      Navigator.pop(context); // Close loading
      
      if (result['success']) {
        String message = result['message'];
        if (selectedSpot != null) {
          message = '$message (Puesto #$selectedSpot)';
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: Colors.green,
          ),
        );
        _loadData(); // Refresh
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

  Future<void> _joinWaitlist(ActivitySession session) async {
    final api = Provider.of<ApiService>(context, listen: false);
    
    // Show loading
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );
    
    final result = await api.joinWaitlist(session.id);
    
    if (mounted) {
      Navigator.pop(context); // Close loading
      
      if (result['success']) {
        String message = result['message'];
        if (result['is_vip'] == true) {
          message = '¡VIP! $message';
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: Colors.orange,
          ),
        );
        _loadData(); // Refresh
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

  Future<void> _leaveWaitlist(int entryId) async {
    final api = Provider.of<ApiService>(context, listen: false);
    
    // Show loading
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );
    
    final result = await api.leaveWaitlist(entryId);
    
    if (mounted) {
      Navigator.pop(context); // Close loading
      
      if (result['success']) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: Colors.blue,
          ),
        );
        _loadData(); // Refresh
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

  Future<void> _claimWaitlistSpot(int entryId) async {
    final api = Provider.of<ApiService>(context, listen: false);
    
    // Show loading
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );
    
    final result = await api.claimWaitlistSpot(entryId);
    
    if (mounted) {
      Navigator.pop(context); // Close loading
      
      if (result['success']) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: Colors.green,
          ),
        );
        _loadData(); // Refresh
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
    // Group sessions by date
    final sessionsByDate = <String, List<ActivitySession>>{};
    for (var session in _sessions) {
      final dateKey = DateFormat('yyyy-MM-dd').format(session.startDatetime);
      sessionsByDate.putIfAbsent(dateKey, () => []).add(session);
    }

    final api = Provider.of<ApiService>(context);
    final brandColor = api.brandColor;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Horario de Clases'),
        backgroundColor: brandColor,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: Column(
        children: [
          // Filter
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.white,
            child: Row(
              children: [
                Icon(Icons.filter_list, color: brandColor),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<int?>(
                    value: _selectedActivityId,
                    decoration: const InputDecoration(
                      labelText: 'Filtrar por actividad',
                      border: OutlineInputBorder(),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    items: [
                      const DropdownMenuItem(value: null, child: Text('Todas las actividades')),
                      ..._activities.map((activity) => DropdownMenuItem(
                        value: activity.id,
                        child: Text(activity.name),
                      )),
                    ],
                    onChanged: (value) {
                      setState(() => _selectedActivityId = value);
                      _loadData();
                    },
                  ),
                ),
              ],
            ),
          ),

          // Content
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _sessions.isEmpty
                    ? _buildEmptyState()
                    : RefreshIndicator(
                        onRefresh: _loadData,
                        child: ListView(
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          children: [
                            // Promotional Advertisements
                            const PromoSection(
                              screen: 'CLASS_CATALOG',
                              title: 'Ofertas Especiales',
                            ),
                            
                            const SizedBox(height: 16),
                            
                            // Sessions by date
                            ...sessionsByDate.entries.map((entry) {
                              final dateKey = entry.key;
                              final date = DateTime.parse(dateKey);
                              final sessions = entry.value;

                              return Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 16),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    // Date header
                                    Padding(
                                      padding: const EdgeInsets.only(bottom: 12, top: 16),
                                      child: Text(
                                        DateFormat('EEEE d MMMM').format(date),
                                        style: const TextStyle(
                                          fontSize: 18,
                                          fontWeight: FontWeight.bold,
                                          color: Color(0xFF0F172A),
                                        ),
                                      ),
                                    ),
                                    // Sessions for this date
                                    ...sessions.map((session) => _buildSessionCard(session)),
                                  ],
                                ),
                              );
                            }),
                          ],
                        ),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildSessionCard(ActivitySession session) {
    final color = session.activity.color.isNotEmpty
        ? Color(int.parse(session.activity.color.replaceFirst('#', '0xFF')))
        : const Color(0xFF0F172A);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: session.isBooked ? Colors.green : Colors.grey[200]!,
          width: session.isBooked ? 2 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            // Time
            Container(
              width: 60,
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  Text(
                    DateFormat('HH:mm').format(session.startDatetime),
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: color,
                      fontSize: 16,
                    ),
                  ),
                  Text(
                    DateFormat('HH:mm').format(session.endDatetime),
                    style: TextStyle(
                      fontSize: 12,
                      color: color.withOpacity(0.7),
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
                  if (session.instructor != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      'Con ${session.instructor!.fullName}',
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(
                        Icons.people,
                        size: 16,
                        color: session.isFull ? Colors.red : Colors.green,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        '${session.availableSpots} plazas',
                        style: TextStyle(
                          fontSize: 12,
                          color: session.isFull ? Colors.red : Colors.green,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Action button
            _buildActionButton(session, color),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton(ActivitySession session, Color color) {
    // Already booked
    if (session.isBooked) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.green[50],
          borderRadius: BorderRadius.circular(20),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.check_circle, color: Colors.green, size: 16),
            SizedBox(width: 4),
            Text(
              'Reservado',
              style: TextStyle(
                color: Colors.green,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      );
    }
    
    // Can book directly
    if (!session.isFull) {
      return ElevatedButton(
        onPressed: () => _bookSession(session),
        style: ElevatedButton.styleFrom(
          backgroundColor: color,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          elevation: 0,
        ),
        child: const Text(
          'Reservar',
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
        ),
      );
    }
    
    // Session is full - check waitlist options
    final waitlist = session.waitlistInfo;
    
    // Can claim a spot (notified status)
    if (waitlist.canClaim && waitlist.waitlistEntryId != null) {
      return ElevatedButton(
        onPressed: () => _claimWaitlistSpot(waitlist.waitlistEntryId!),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.green,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          elevation: 0,
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.flash_on, size: 14),
            SizedBox(width: 4),
            Text(
              '¡Reclamar!',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      );
    }
    
    // Already in waitlist (but can't claim yet)
    if (waitlist.isInWaitlist && waitlist.waitlistEntryId != null) {
      return GestureDetector(
        onTap: () => _showWaitlistOptions(session, waitlist),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: Colors.orange[50],
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Colors.orange, width: 1),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.hourglass_top, color: Colors.orange, size: 14),
              const SizedBox(width: 4),
              Text(
                '#${waitlist.waitlistPosition ?? '-'}',
                style: const TextStyle(
                  color: Colors.orange,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      );
    }
    
    // Can join waitlist
    if (waitlist.enabled) {
      return ElevatedButton(
        onPressed: () => _joinWaitlist(session),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.orange,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          elevation: 0,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.playlist_add, size: 14),
            const SizedBox(width: 4),
            Text(
              waitlist.waitlistCount > 0 ? 'Espera (${waitlist.waitlistCount})' : 'Lista espera',
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      );
    }
    
    // Just full, no waitlist
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.red[50],
        borderRadius: BorderRadius.circular(20),
      ),
      child: const Text(
        'Lleno',
        style: TextStyle(
          color: Colors.red,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  void _showWaitlistOptions(ActivitySession session, WaitlistInfo waitlist) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey[300],
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 20),
            const Icon(Icons.hourglass_top, size: 48, color: Colors.orange),
            const SizedBox(height: 16),
            Text(
              'En lista de espera',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Colors.grey[800],
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Posición: #${waitlist.waitlistPosition ?? '-'}',
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 8),
            Text(
              session.activity.name,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[500],
              ),
            ),
            Text(
              '${session.dateString} · ${session.timeRange}',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[500],
              ),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () {
                      Navigator.pop(context);
                      _leaveWaitlist(waitlist.waitlistEntryId!);
                    },
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red,
                      side: const BorderSide(color: Colors.red),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: const Text('Salir de la lista'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () => Navigator.pop(context),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.grey[200],
                      foregroundColor: Colors.grey[800],
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                      elevation: 0,
                    ),
                    child: const Text('Cerrar'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.calendar_today_outlined,
            size: 80,
            color: Colors.grey[300],
          ),
          const SizedBox(height: 16),
          Text(
            'No hay clases programadas',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Intenta cambiar el filtro o la fecha',
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
