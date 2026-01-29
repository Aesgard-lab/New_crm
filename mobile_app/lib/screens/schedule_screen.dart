import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';
import '../models/schedule_models.dart';
import '../widgets/promo_section.dart';
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
    
    // Show loading
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );
    
    final result = await api.bookSession(session.id);
    
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
            if (session.isBooked)
              Container(
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
              )
            else if (!session.isFull)
              ElevatedButton(
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
              )
            else
              Container(
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
              ),
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
