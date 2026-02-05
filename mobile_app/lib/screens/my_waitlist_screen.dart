import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';
import 'dart:async';

class MyWaitlistScreen extends StatefulWidget {
  const MyWaitlistScreen({super.key});

  @override
  State<MyWaitlistScreen> createState() => _MyWaitlistScreenState();
}

class _MyWaitlistScreenState extends State<MyWaitlistScreen> {
  List<WaitlistEntryModel> _entries = [];
  bool _isLoading = true;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadEntries();
    // Auto-refresh every 30 seconds to check for claim expirations
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) _loadEntries();
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadEntries() async {
    final api = Provider.of<ApiService>(context, listen: false);
    final data = await api.getMyWaitlistEntries();
    
    final entries = data.map((json) => WaitlistEntryModel.fromJson(json)).toList();
    
    if (mounted) {
      setState(() {
        _entries = entries;
        _isLoading = false;
      });
    }
  }

  Future<void> _leaveWaitlist(int entryId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Salir de lista de espera'),
        content: const Text('¿Estás seguro de que quieres salir de esta lista de espera?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('No'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sí, salir', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );

    final api = Provider.of<ApiService>(context, listen: false);
    final result = await api.leaveWaitlist(entryId);

    if (mounted) {
      Navigator.pop(context);

      if (result['success']) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: Colors.blue,
          ),
        );
        _loadEntries();
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

  Future<void> _claimSpot(int entryId) async {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );

    final api = Provider.of<ApiService>(context, listen: false);
    final result = await api.claimWaitlistSpot(entryId);

    if (mounted) {
      Navigator.pop(context);

      if (result['success']) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: Colors.green,
          ),
        );
        _loadEntries();
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
    final api = Provider.of<ApiService>(context);
    final brandColor = api.brandColor;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Mi Lista de Espera'),
        backgroundColor: brandColor,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _entries.isEmpty
              ? _buildEmptyState()
              : RefreshIndicator(
                  onRefresh: _loadEntries,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _entries.length,
                    itemBuilder: (context, index) => _buildEntryCard(_entries[index], brandColor),
                  ),
                ),
    );
  }

  Widget _buildEntryCard(WaitlistEntryModel entry, Color brandColor) {
    final canClaim = entry.status == 'NOTIFIED' && 
                     entry.claimExpiresAt != null && 
                     entry.claimExpiresAt!.isAfter(DateTime.now());
    
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      elevation: canClaim ? 4 : 1,
      child: Container(
        decoration: canClaim
            ? BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.green, width: 2),
              )
            : null,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with activity name
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: brandColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(Icons.fitness_center, color: brandColor, size: 24),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          entry.activityName,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF0F172A),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${entry.sessionDate} · ${entry.sessionTime}',
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                  ),
                  // Status badge
                  _buildStatusBadge(entry),
                ],
              ),
              
              const SizedBox(height: 12),
              
              // Position and VIP info
              Row(
                children: [
                  Icon(Icons.format_list_numbered, size: 16, color: Colors.grey[600]),
                  const SizedBox(width: 4),
                  Text(
                    'Posición: #${entry.position}',
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.grey[600],
                    ),
                  ),
                  if (entry.isVip) ...[
                    const SizedBox(width: 12),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.amber[100],
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.star, size: 12, color: Colors.amber),
                          SizedBox(width: 2),
                          Text(
                            'VIP',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: Colors.amber,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
              
              // Claim banner
              if (canClaim) ...[
                const SizedBox(height: 12),
                _buildClaimBanner(entry),
              ],
              
              const SizedBox(height: 12),
              
              // Actions
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (canClaim) ...[
                    ElevatedButton.icon(
                      onPressed: () => _claimSpot(entry.id),
                      icon: const Icon(Icons.flash_on, size: 18),
                      label: const Text('¡Reclamar plaza!'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                  ],
                  OutlinedButton(
                    onPressed: () => _leaveWaitlist(entry.id),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red,
                      side: const BorderSide(color: Colors.red),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                    ),
                    child: const Text('Salir'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatusBadge(WaitlistEntryModel entry) {
    Color bgColor;
    Color textColor;
    String text;
    IconData icon;

    switch (entry.status) {
      case 'NOTIFIED':
        bgColor = Colors.green[50]!;
        textColor = Colors.green;
        text = '¡Disponible!';
        icon = Icons.notifications_active;
        break;
      case 'WAITING':
      default:
        bgColor = Colors.orange[50]!;
        textColor = Colors.orange;
        text = 'Esperando';
        icon = Icons.hourglass_top;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: textColor),
          const SizedBox(width: 4),
          Text(
            text,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: textColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildClaimBanner(WaitlistEntryModel entry) {
    final remaining = entry.claimExpiresAt!.difference(DateTime.now());
    final minutes = remaining.inMinutes;
    final seconds = remaining.inSeconds % 60;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.green[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.green[200]!),
      ),
      child: Row(
        children: [
          const Icon(Icons.timer, color: Colors.green),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '¡Se ha liberado una plaza!',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.green,
                  ),
                ),
                Text(
                  'Tienes ${minutes}m ${seconds}s para reclamarla',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.green[700],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.hourglass_empty,
            size: 80,
            color: Colors.grey[300],
          ),
          const SizedBox(height: 16),
          Text(
            'No estás en ninguna lista de espera',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Cuando una clase esté llena, podrás unirte\na la lista de espera desde el horario',
            textAlign: TextAlign.center,
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

// Model for waitlist entries from API
class WaitlistEntryModel {
  final int id;
  final int sessionId;
  final String activityName;
  final String sessionDate;
  final String sessionTime;
  final String status;
  final int position;
  final bool isVip;
  final DateTime? claimExpiresAt;

  WaitlistEntryModel({
    required this.id,
    required this.sessionId,
    required this.activityName,
    required this.sessionDate,
    required this.sessionTime,
    required this.status,
    required this.position,
    required this.isVip,
    this.claimExpiresAt,
  });

  factory WaitlistEntryModel.fromJson(Map<String, dynamic> json) {
    // Parse datetime to extract date and time strings
    DateTime? startDatetime;
    String sessionDate = '';
    String sessionTime = '';
    
    if (json['start_datetime'] != null) {
      startDatetime = DateTime.parse(json['start_datetime']);
      final months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
      sessionDate = '${startDatetime.day} ${months[startDatetime.month - 1]}';
      sessionTime = '${startDatetime.hour.toString().padLeft(2, '0')}:${startDatetime.minute.toString().padLeft(2, '0')}';
    }
    
    return WaitlistEntryModel(
      id: json['id'],
      sessionId: json['session_id'],
      activityName: json['activity_name'] ?? '',
      sessionDate: sessionDate,
      sessionTime: sessionTime,
      status: json['status'] ?? 'WAITING',
      position: json['position'] ?? 0,
      isVip: json['is_vip'] ?? false,
      claimExpiresAt: json['claim_expires_at'] != null
          ? DateTime.parse(json['claim_expires_at'])
          : null,
    );
  }
}
