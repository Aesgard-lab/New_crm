import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';

class WorkoutTrackingScreen extends StatefulWidget {
  final int workoutId;
  final String routineName;
  final String dayName;
  final List<dynamic>? exercises;

  const WorkoutTrackingScreen({
    super.key,
    required this.workoutId,
    required this.routineName,
    required this.dayName,
    this.exercises,
  });

  @override
  State<WorkoutTrackingScreen> createState() => _WorkoutTrackingScreenState();
}

class _WorkoutTrackingScreenState extends State<WorkoutTrackingScreen> {
  List<dynamic> _exercises = [];
  int _currentExerciseIndex = 0;
  bool _isLogging = false;
  bool _isLoading = true;
  Timer? _timer;
  int _elapsedSeconds = 0;
  
  // Form controllers
  final _repsController = TextEditingController();
  final _weightController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadWorkoutData();
  }

  Future<void> _loadWorkoutData() async {
    if (widget.exercises != null && widget.exercises!.isNotEmpty) {
      setState(() {
        _exercises = List.from(widget.exercises!);
        _isLoading = false;
      });
      _startTimer();
    } else {
      // Cargar desde la API para entrenamiento existente
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.getWorkoutStatus(widget.workoutId);
      
      if (result['success'] == true && mounted) {
        setState(() {
          _exercises = result['exercises'] ?? [];
          _elapsedSeconds = result['elapsed_seconds'] ?? 0;
          _isLoading = false;
        });
        _startTimer();
      } else if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _repsController.dispose();
    _weightController.dispose();
    super.dispose();
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        _elapsedSeconds++;
      });
    });
  }

  String get _formattedTime {
    final hours = _elapsedSeconds ~/ 3600;
    final minutes = (_elapsedSeconds % 3600) ~/ 60;
    final seconds = _elapsedSeconds % 60;
    if (hours > 0) {
      return '${hours.toString().padLeft(2, '0')}:${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
    }
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  Future<void> _logSet() async {
    final reps = int.tryParse(_repsController.text) ?? 0;
    final weight = double.tryParse(_weightController.text) ?? 0;
    
    if (reps <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ingresa las repeticiones')),
      );
      return;
    }

    setState(() => _isLogging = true);
    
    final api = Provider.of<ApiService>(context, listen: false);
    final exercise = _exercises[_currentExerciseIndex];
    final result = await api.logSet(
      widget.workoutId,
      exercise['exercise_log_id'],
      reps,
      weight,
    );

    setState(() => _isLogging = false);

    if (result['success'] == true) {
      // Update local state
      setState(() {
        exercise['sets_completed'] = result['total_sets'];
        if (exercise['sets_data'] == null) {
          exercise['sets_data'] = [];
        }
        exercise['sets_data'].add({'reps': reps, 'weight': weight});
      });
      
      // Clear form
      _repsController.clear();
      _weightController.clear();
      
      // Vibration feedback
      // HapticFeedback.mediumImpact();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result['message'] ?? 'Error')),
      );
    }
  }

  Future<void> _completeExercise() async {
    final api = Provider.of<ApiService>(context, listen: false);
    final exercise = _exercises[_currentExerciseIndex];
    
    final result = await api.completeExercise(
      widget.workoutId,
      exercise['exercise_log_id'],
    );

    if (result['success'] == true) {
      setState(() {
        exercise['completed'] = true;
      });
      
      // Move to next exercise if available
      if (_currentExerciseIndex < _exercises.length - 1) {
        setState(() {
          _currentExerciseIndex++;
        });
      }
    }
  }

  Future<void> _finishWorkout() async {
    final difficulty = await showDialog<int>(
      context: context,
      builder: (context) => _DifficultyDialog(),
    );

    if (difficulty != null) {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.finishWorkout(widget.workoutId, difficultyRating: difficulty);

      if (result['success'] == true) {
        if (mounted) {
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(
              builder: (_) => WorkoutSummaryScreen(summary: result['summary']),
            ),
          );
        }
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(result['message'] ?? 'Error')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        backgroundColor: const Color(0xFFF8FAFC),
        body: const Center(
          child: CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF10B981)),
          ),
        ),
      );
    }

    if (_exercises.isEmpty) {
      return Scaffold(
        backgroundColor: const Color(0xFFF8FAFC),
        appBar: AppBar(
          title: const Text('Error'),
          backgroundColor: Colors.white,
        ),
        body: const Center(
          child: Text('No se encontraron ejercicios'),
        ),
      );
    }

    final exercise = _exercises[_currentExerciseIndex];
    final completedCount = _exercises.where((e) => e['completed'] == true).length;
    
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: Column(
          children: [
            // Header with timer
            Container(
              padding: const EdgeInsets.all(20),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [Color(0xFF10B981), Color(0xFF059669)],
                ),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      IconButton(
                        onPressed: () => _showExitConfirmation(),
                        icon: const Icon(Icons.close, color: Colors.white),
                      ),
                      Column(
                        children: [
                          Text(
                            widget.dayName,
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 14,
                            ),
                          ),
                          Text(
                            widget.routineName,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      IconButton(
                        onPressed: _finishWorkout,
                        icon: const Icon(Icons.check, color: Colors.white),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  // Timer
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(30),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.timer, color: Colors.white, size: 24),
                        const SizedBox(width: 8),
                        Text(
                          _formattedTime,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  // Progress
                  LinearProgressIndicator(
                    value: completedCount / _exercises.length,
                    backgroundColor: Colors.white.withOpacity(0.3),
                    valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '$completedCount / ${_exercises.length} ejercicios',
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                ],
              ),
            ),

            // Exercise selector
            SizedBox(
              height: 80,
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                itemCount: _exercises.length,
                itemBuilder: (context, index) {
                  final ex = _exercises[index];
                  final isSelected = index == _currentExerciseIndex;
                  final isCompleted = ex['completed'] == true;
                  
                  return GestureDetector(
                    onTap: () => setState(() => _currentExerciseIndex = index),
                    child: Container(
                      width: 56,
                      margin: const EdgeInsets.only(right: 8),
                      decoration: BoxDecoration(
                        color: isCompleted
                            ? const Color(0xFF10B981)
                            : isSelected
                                ? const Color(0xFF6366F1)
                                : Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: isSelected ? const Color(0xFF6366F1) : Colors.transparent,
                          width: 2,
                        ),
                        boxShadow: isSelected
                            ? [BoxShadow(color: const Color(0xFF6366F1).withOpacity(0.3), blurRadius: 8)]
                            : null,
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            '${index + 1}',
                            style: TextStyle(
                              color: (isSelected || isCompleted) ? Colors.white : Colors.grey[600],
                              fontWeight: FontWeight.bold,
                              fontSize: 18,
                            ),
                          ),
                          if (isCompleted)
                            const Icon(Icons.check, color: Colors.white, size: 16),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),

            // Current exercise
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Exercise name
                    Text(
                      exercise['exercise_name'] ?? 'Ejercicio',
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF1E293B),
                      ),
                    ),
                    const SizedBox(height: 8),
                    
                    // Target info
                    Row(
                      children: [
                        _InfoChip(
                          icon: Icons.repeat,
                          label: '${exercise['target_sets'] ?? '-'} series',
                        ),
                        const SizedBox(width: 8),
                        _InfoChip(
                          icon: Icons.fitness_center,
                          label: '${exercise['target_reps'] ?? '-'} reps',
                        ),
                        if (exercise['rest_time'] != null) ...[
                          const SizedBox(width: 8),
                          _InfoChip(
                            icon: Icons.timer,
                            label: exercise['rest_time'],
                          ),
                        ],
                      ],
                    ),
                    
                    if (exercise['notes'] != null && exercise['notes'].isNotEmpty) ...[
                      const SizedBox(height: 16),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.amber[50],
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.amber[200]!),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.note, color: Colors.amber[700], size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                exercise['notes'],
                                style: TextStyle(color: Colors.amber[900], fontSize: 14),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    
                    const SizedBox(height: 24),
                    
                    // Completed sets
                    if ((exercise['sets_data'] as List?)?.isNotEmpty ?? false) ...[
                      const Text(
                        'Series completadas',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF64748B),
                        ),
                      ),
                      const SizedBox(height: 12),
                      ...List.generate((exercise['sets_data'] as List).length, (i) {
                        final set = exercise['sets_data'][i];
                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: const Color(0xFF10B981)),
                          ),
                          child: Row(
                            children: [
                              Container(
                                width: 32,
                                height: 32,
                                decoration: BoxDecoration(
                                  color: const Color(0xFF10B981),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Center(
                                  child: Text(
                                    '${i + 1}',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 16),
                              Text(
                                '${set['reps']} reps',
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const Spacer(),
                              Text(
                                '${set['weight']} kg',
                                style: const TextStyle(
                                  fontSize: 16,
                                  color: Color(0xFF64748B),
                                ),
                              ),
                            ],
                          ),
                        );
                      }),
                      const SizedBox(height: 16),
                    ],
                    
                    // Log new set form
                    if (exercise['completed'] != true) ...[
                      Container(
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(20),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.05),
                              blurRadius: 10,
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Serie ${(exercise['sets_completed'] ?? 0) + 1}',
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF1E293B),
                              ),
                            ),
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Expanded(
                                  child: TextField(
                                    controller: _repsController,
                                    keyboardType: TextInputType.number,
                                    decoration: InputDecoration(
                                      labelText: 'Repeticiones',
                                      hintText: exercise['target_reps']?.toString() ?? '12',
                                      border: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      filled: true,
                                      fillColor: const Color(0xFFF8FAFC),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 16),
                                Expanded(
                                  child: TextField(
                                    controller: _weightController,
                                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                    decoration: InputDecoration(
                                      labelText: 'Peso (kg)',
                                      hintText: '0',
                                      border: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      filled: true,
                                      fillColor: const Color(0xFFF8FAFC),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 16),
                            SizedBox(
                              width: double.infinity,
                              child: ElevatedButton(
                                onPressed: _isLogging ? null : _logSet,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFF6366F1),
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(vertical: 16),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                ),
                                child: _isLogging
                                    ? const SizedBox(
                                        width: 20,
                                        height: 20,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                        ),
                                      )
                                    : const Text(
                                        '+ Guardar Serie',
                                        style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      
                      // Complete exercise button
                      if ((exercise['sets_completed'] ?? 0) > 0)
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton(
                            onPressed: _completeExercise,
                            style: OutlinedButton.styleFrom(
                              foregroundColor: const Color(0xFF10B981),
                              side: const BorderSide(color: Color(0xFF10B981)),
                              padding: const EdgeInsets.symmetric(vertical: 16),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            child: const Text(
                              '✓ Completar Ejercicio',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),
                    ] else ...[
                      // Exercise completed state
                      Container(
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: const Column(
                          children: [
                            Icon(
                              Icons.check_circle,
                              color: Color(0xFF10B981),
                              size: 48,
                            ),
                            SizedBox(height: 12),
                            Text(
                              '¡Ejercicio completado!',
                              style: TextStyle(
                                color: Color(0xFF10B981),
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showExitConfirmation() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Salir del entrenamiento?'),
        content: const Text('Tu progreso se guardará y podrás continuar más tarde.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              Navigator.pop(context);
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Salir'),
          ),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _InfoChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: const Color(0xFF64748B)),
          const SizedBox(width: 4),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF64748B),
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _DifficultyDialog extends StatefulWidget {
  @override
  State<_DifficultyDialog> createState() => _DifficultyDialogState();
}

class _DifficultyDialogState extends State<_DifficultyDialog> {
  int _selectedDifficulty = 5;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('¿Cómo fue el entrenamiento?'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('Dificultad percibida:'),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text('Fácil', style: TextStyle(fontSize: 12)),
              Expanded(
                child: Slider(
                  value: _selectedDifficulty.toDouble(),
                  min: 1,
                  max: 10,
                  divisions: 9,
                  onChanged: (value) {
                    setState(() => _selectedDifficulty = value.round());
                  },
                ),
              ),
              const Text('Difícil', style: TextStyle(fontSize: 12)),
            ],
          ),
          Text(
            '$_selectedDifficulty / 10',
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Color(0xFF6366F1),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancelar'),
        ),
        ElevatedButton(
          onPressed: () => Navigator.pop(context, _selectedDifficulty),
          child: const Text('Finalizar'),
        ),
      ],
    );
  }
}

class WorkoutSummaryScreen extends StatelessWidget {
  final Map<String, dynamic> summary;

  const WorkoutSummaryScreen({super.key, required this.summary});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF10B981), Color(0xFF059669)],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(
                    Icons.celebration,
                    color: Colors.white,
                    size: 80,
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    '¡Entrenamiento\nCompletado!',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 40),
                  
                  // Stats
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: Column(
                      children: [
                        _StatRow(
                          icon: Icons.timer,
                          label: 'Duración',
                          value: '${summary['duration_minutes'] ?? 0} min',
                        ),
                        const Divider(),
                        _StatRow(
                          icon: Icons.repeat,
                          label: 'Series',
                          value: '${summary['total_sets'] ?? 0}',
                        ),
                        const Divider(),
                        _StatRow(
                          icon: Icons.fitness_center,
                          label: 'Repeticiones',
                          value: '${summary['total_reps'] ?? 0}',
                        ),
                        const Divider(),
                        _StatRow(
                          icon: Icons.monitor_weight,
                          label: 'Volumen total',
                          value: '${(summary['total_volume'] ?? 0).toStringAsFixed(0)} kg',
                        ),
                      ],
                    ),
                  ),
                  
                  const SizedBox(height: 40),
                  
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.of(context).popUntil((route) => route.isFirst);
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: const Color(0xFF10B981),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      child: const Text(
                        'Volver al inicio',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _StatRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _StatRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, color: const Color(0xFF64748B), size: 24),
          const SizedBox(width: 12),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF64748B),
              fontSize: 16,
            ),
          ),
          const Spacer(),
          Text(
            value,
            style: const TextStyle(
              color: Color(0xFF1E293B),
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
