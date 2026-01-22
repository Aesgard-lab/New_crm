import 'package:flutter/material.dart';
import '../models/routine.dart';

class ExerciseDetailScreen extends StatefulWidget {
  final RoutineExercise exercise;

  const ExerciseDetailScreen({super.key, required this.exercise});

  @override
  State<ExerciseDetailScreen> createState() => _ExerciseDetailScreenState();
}

class _ExerciseDetailScreenState extends State<ExerciseDetailScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: CustomScrollView(
        slivers: [
          // Header with video preview or gradient
          SliverAppBar(
            expandedHeight: widget.exercise.videoUrl != null ? 280 : 180,
            pinned: true,
            backgroundColor: Color(widget.exercise.muscleGroupColor),
            flexibleSpace: FlexibleSpaceBar(
              background: widget.exercise.videoUrl != null
                  ? _buildVideoPlaceholder()
                  : _buildGradientHeader(),
            ),
            leading: IconButton(
              icon: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.3),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.arrow_back, color: Colors.white),
              ),
              onPressed: () => Navigator.pop(context),
            ),
          ),
          
          // Content
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Exercise Name & Muscle Group
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          widget.exercise.name,
                          style: const TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF1E293B),
                          ),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: Color(widget.exercise.muscleGroupColor)
                              .withOpacity(0.15),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              widget.exercise.muscleGroupIcon,
                              style: const TextStyle(fontSize: 16),
                            ),
                            const SizedBox(width: 4),
                            Text(
                              widget.exercise.muscleGroupDisplay,
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: Color(widget.exercise.muscleGroupColor),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  
                  const SizedBox(height: 24),
                  
                  // Sets/Reps/Rest Section
                  if (widget.exercise.sets.isNotEmpty ||
                      widget.exercise.reps.isNotEmpty ||
                      widget.exercise.rest.isNotEmpty)
                    _buildDetailsSection(),
                  
                  const SizedBox(height: 20),
                  
                  // Description
                  if (widget.exercise.description.isNotEmpty) ...[
                    const Text(
                      'Descripción',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF1E293B),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      widget.exercise.description,
                      style: const TextStyle(
                        fontSize: 15,
                        color: Color(0xFF64748B),
                        height: 1.6,
                      ),
                    ),
                    const SizedBox(height: 20),
                  ],
                  
                  // Trainer Notes
                  if (widget.exercise.notes.isNotEmpty)
                    _buildTrainerNotes(),
                  
                  const SizedBox(height: 40),
                ],
              ),
            ),
          ),
        ],
      ),
      
      // Play Video Button
      floatingActionButton: widget.exercise.videoUrl != null
          ? FloatingActionButton.extended(
              onPressed: () => _openVideoUrl(),
              backgroundColor: const Color(0xFF6366F1),
              icon: const Icon(Icons.play_arrow),
              label: const Text('Ver Video'),
            )
          : null,
    );
  }

  Widget _buildGradientHeader() {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Color(widget.exercise.muscleGroupColor),
            Color(widget.exercise.muscleGroupColor).withOpacity(0.7),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Center(
        child: Text(
          widget.exercise.muscleGroupIcon,
          style: const TextStyle(fontSize: 72),
        ),
      ),
    );
  }

  Widget _buildVideoPlaceholder() {
    return Stack(
      fit: StackFit.expand,
      children: [
        Container(
          color: const Color(0xFF0F172A),
          child: const Center(
            child: Icon(
              Icons.play_circle_outline,
              size: 72,
              color: Colors.white54,
            ),
          ),
        ),
        // Play overlay
        Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [Colors.transparent, Colors.black.withOpacity(0.5)],
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
            ),
          ),
        ),
        // Tap to play indicator
        Positioned(
          bottom: 16,
          left: 16,
          right: 16,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.play_arrow, color: Colors.white, size: 20),
                    SizedBox(width: 4),
                    Text(
                      'Video disponible',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDetailsSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          if (widget.exercise.sets.isNotEmpty)
            Expanded(
              child: _buildDetailItem(
                value: widget.exercise.sets,
                label: 'Series',
                icon: Icons.repeat,
              ),
            ),
          if (widget.exercise.reps.isNotEmpty)
            Expanded(
              child: _buildDetailItem(
                value: widget.exercise.reps,
                label: 'Reps',
                icon: Icons.fitness_center,
              ),
            ),
          if (widget.exercise.rest.isNotEmpty)
            Expanded(
              child: _buildDetailItem(
                value: widget.exercise.rest,
                label: 'Descanso',
                icon: Icons.timer,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildDetailItem({
    required String value,
    required String label,
    required IconData icon,
  }) {
    return Column(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: const Color(0xFFEEF2FF),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(
            icon,
            color: const Color(0xFF6366F1),
            size: 24,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          value,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: Color(0xFF1E293B),
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: Color(0xFF64748B),
          ),
        ),
      ],
    );
  }

  Widget _buildTrainerNotes() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFFEF3C7),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFFCD34D)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.lightbulb,
                color: Color(0xFFD97706),
                size: 20,
              ),
              SizedBox(width: 8),
              Text(
                'Nota del entrenador',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFFD97706),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            widget.exercise.notes,
            style: const TextStyle(
              fontSize: 14,
              color: Color(0xFF92400E),
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  void _openVideoUrl() {
    // For now show a snackbar, later integrate youtube_player
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Video: ${widget.exercise.videoUrl}'),
        action: SnackBarAction(
          label: 'Abrir',
          onPressed: () {
            // TODO: Use url_launcher to open in browser or embed player
          },
        ),
      ),
    );
  }
}
