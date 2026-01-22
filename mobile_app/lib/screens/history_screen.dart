import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<dynamic> _classes = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() => _isLoading = true);
    final api = Provider.of<ApiService>(context, listen: false);
    final classes = await api.getClassHistory();
    
    if (mounted) {
      setState(() {
        _classes = classes;
        _isLoading = false;
      });
    }
  }

  Future<void> _showReviewDialog(Map<String, dynamic> session) async {
    int instructorRate = 5;
    int classRate = 5;
    String comment = '';

    await showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            title: const Text('Valorar Clase'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                   Text(session['activity_name'], style: const TextStyle(fontWeight: FontWeight.bold)),
                   Text('Instructor: ${session['staff_name']}'),
                   const SizedBox(height: 16),
                   
                   const Text('Instructor'),
                   Row(
                     mainAxisAlignment: MainAxisAlignment.center,
                     children: List.generate(5, (index) {
                       return IconButton(
                         icon: Icon(
                           index < instructorRate ? Icons.star : Icons.star_border,
                           color: Colors.amber,
                         ),
                         onPressed: () => setDialogState(() => instructorRate = index + 1),
                       );
                     }),
                   ),
                   
                   const SizedBox(height: 8),
                   const Text('Clase'),
                   Row(
                     mainAxisAlignment: MainAxisAlignment.center,
                     children: List.generate(5, (index) {
                       return IconButton(
                         icon: Icon(
                           index < classRate ? Icons.star : Icons.star_border,
                           color: Colors.amber,
                         ),
                         onPressed: () => setDialogState(() => classRate = index + 1),
                       );
                     }),
                   ),
                   
                   const SizedBox(height: 8),
                   TextField(
                     decoration: const InputDecoration(
                       labelText: 'Comentario (opcional)',
                       border: OutlineInputBorder(),
                     ),
                     maxLines: 3,
                     onChanged: (val) => comment = val,
                   ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Cancelar'),
              ),
              ElevatedButton(
                onPressed: () async {
                  Navigator.pop(ctx);
                  final api = Provider.of<ApiService>(context, listen: false);
                  final result = await api.submitClassReview(
                    sessionId: session['session_id'],
                    instructorRating: instructorRate,
                    classRating: classRate,
                    comment: comment,
                  );
                  
                  if (mounted) {
                    if (result['success'] == true) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Valoración enviada. ¡Gracias!')),
                      );
                      _loadHistory(); // Refresh to hide button
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(result['message'] ?? 'Error')),
                      );
                    }
                  }
                },
                child: const Text('Enviar'),
              ),
            ],
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Historial de Clases', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF0F172A),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _classes.isEmpty
              ? _buildEmptyState()
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _classes.length,
                  itemBuilder: (context, index) {
                    return _buildClassCard(_classes[index]);
                  },
                ),
    );
  }

  Widget _buildClassCard(Map<String, dynamic> session) {
    final hasReview = session['has_review'] == true;
    final attended = session['attended'] == true;

    return Card(
      elevation: 2,
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Row(
              children: [
                Container(
                  width: 50,
                  height: 50,
                  decoration: BoxDecoration(
                    color: attended ? const Color(0xFFDCFCE7) : const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    attended ? Icons.check_circle_outline : Icons.history,
                    color: attended ? Colors.green : Colors.grey,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        session['activity_name'] ?? 'Clase',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      Text(
                        session['start_datetime']?.split('T')[0] ?? '',
                        style: TextStyle(color: Colors.grey[600]),
                      ),
                    ],
                  ),
                ),
                if (attended && !hasReview)
                  ElevatedButton(
                    onPressed: () => _showReviewDialog(session),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF0F172A),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      minimumSize: const Size(0, 32),
                    ),
                    child: const Text('Valorar'),
                  )
                else if (hasReview)
                  const Row(
                    children: [
                      Icon(Icons.star, color: Colors.amber, size: 16),
                      SizedBox(width: 4),
                      Text('Valorada', style: TextStyle(color: Colors.amber, fontWeight: FontWeight.bold)),
                    ],
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: const Text('No tienes historial de clases'),
    );
  }
}
